import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

from backend.app.logic.genealogy_tree_logic import GenealogyTreeLogic
from backend.models_db.Enums import RelType
from backend.models_db.Rel import Rel
from pages.genealogy_tree import _collapsible_siblings, _compute_layout


class FamilyDB:
    def __init__(self, names, relationships):
        self.entities = {
            name: SimpleNamespace(
                key=name, display_en_name=name, display_heb_name="", isWoman=None
            )
            for name in names
        }
        self.relationships = [
            Rel.create(rel_type, child, parent)
            for rel_type, child, parent in relationships
        ]

    def get_entity_by_key(self, key):
        return self.entities.get(key)

    def get_entities_by_keys_map(self, keys):
        return {key: self.entities[key] for key in keys if key in self.entities}

    def get_family_rels_for_entities(self, keys):
        return [
            rel for rel in self.relationships
            if rel.term1 in keys or rel.term2 in keys
        ]


FATHER = RelType.childOfFather
MOTHER = RelType.childOfMother
SPOUSE = RelType.spouseOf


class GenealogyTreeTests(unittest.TestCase):
    def make_graph(self, depth=1):
        siblings = [f"sibling{i:02}" for i in range(12)]
        relationships = [
            (FATHER, "center", "father"),
            (MOTHER, "center", "mother"),
            (FATHER, "half", "father"),
            (MOTHER, "half", "other_mother"),
            (SPOUSE, "center", "spouse"),
            (FATHER, "child", "center"),
            (MOTHER, "child", "spouse"),
            (FATHER, "missing", "father"),
        ]
        relationships.extend((FATHER, sibling, "father") for sibling in siblings)
        relationships.extend((MOTHER, sibling, "mother") for sibling in siblings)
        names = ["center", "father", "mother", "half", "other_mother", "spouse", "child", *siblings]
        return GenealogyTreeLogic(FamilyDB(names, relationships)).build_graph("center", depth)

    def test_depth_one_shows_siblings_through_recorded_shared_parents(self):
        graph = self.make_graph()
        edges = {(edge.from_key, edge.to_key, edge.rel_type) for edge in graph.edges}
        self.assertEqual(len([node for node in graph.nodes if node.key.startswith("sibling")]), 12)
        self.assertEqual(len(edges), 29)
        self.assertFalse(any(edge.rel_type == "sibling" for edge in graph.edges))
        self.assertIn(("half", "father", "childOfFather"), edges)
        self.assertNotIn(("half", "mother", "childOfMother"), edges)
        self.assertFalse(any("missing" in edge[:2] for edge in edges))

    def test_depth_two_preserves_half_siblings_other_parent(self):
        graph = self.make_graph(depth=2)
        edges = {(edge.from_key, edge.to_key, edge.rel_type) for edge in graph.edges}
        self.assertIn(("half", "other_mother", "childOfMother"), edges)
        self.assertNotIn(("half", "mother", "childOfMother"), edges)
        self.assertNotIn("half", _collapsible_siblings(graph))
        self.assertEqual(len(_collapsible_siblings(graph)), 12)

    def test_center_siblings_grouped_and_other_relatives_not_mislabeled(self):
        graph = self.make_graph(depth=2)
        positions, roles = _compute_layout(graph)
        full = ["center"] + [f"sibling{i:02}" for i in range(12)]
        ordered_row = sorted(
            (node.key for node in graph.nodes if positions[node.key][1] == 0),
            key=lambda key: positions[key][0],
        )
        self.assertEqual(set(ordered_row[:len(full)]), set(full))
        self.assertEqual(ordered_row[len(full)], "spouse")
        self.assertEqual(ordered_row[len(full) + 1], "half")
        self.assertEqual(positions["center"][0], 0)
        self.assertEqual(roles["half"], "sibling")
        self.assertEqual(roles["other_mother"], "relative")
        self.assertEqual(roles["child"], "child")

    def test_sibling_with_other_displayed_relationship_stays_visible(self):
        db = FamilyDB(
            ["center", "father", "sibling", "niece"],
            [(FATHER, "center", "father"), (FATHER, "sibling", "father"),
             (FATHER, "niece", "sibling")],
        )
        graph = GenealogyTreeLogic(db).build_graph("center", depth=2)
        self.assertNotIn("sibling", _collapsible_siblings(graph))

    def test_unresolved_parent_does_not_add_disconnected_siblings(self):
        db = FamilyDB(
            ["center", "sibling"],
            [(FATHER, "center", "missing_parent"), (FATHER, "sibling", "missing_parent")],
        )
        graph = GenealogyTreeLogic(db).build_graph("center")
        self.assertEqual([node.key for node in graph.nodes], ["center"])
        self.assertEqual(graph.edges, [])

    def test_children_with_same_parents_stay_grouped(self):
        db = FamilyDB(
            ["center", "spouse", "other", "a", "b", "c"],
            [(SPOUSE, "center", "spouse"), (SPOUSE, "center", "other"),
             (FATHER, "a", "center"), (MOTHER, "a", "spouse"),
             (FATHER, "b", "center"), (MOTHER, "b", "spouse"),
             (FATHER, "c", "center"), (MOTHER, "c", "other")],
        )
        graph = GenealogyTreeLogic(db).build_graph("center", depth=2)
        positions, _ = _compute_layout(graph)
        children = sorted(("a", "b", "c"), key=lambda key: positions[key][0])
        self.assertEqual(abs(children.index("a") - children.index("b")), 1)

    def test_checkbox_filters_and_restores_visible_graph(self):
        graph = self.make_graph(depth=2)
        app = AppTest.from_string("""
from pages.genealogy_tree import render
render("en")
""")
        with patch("components.person_selector.render_person_selector", return_value="center"), \
             patch("pages.genealogy_tree._load_graph_data", return_value=graph), \
             patch("pages.genealogy_tree._render_pyvis_graph") as render_graph:
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(len(render_graph.call_args.args[0].nodes), len(graph.nodes))
            app.checkbox[0].check().run()
            hidden = render_graph.call_args.args[0]
            self.assertEqual(len(hidden.nodes), len(graph.nodes) - 12)
            self.assertIn("half", {node.key for node in hidden.nodes})
            self.assertTrue(all(edge.from_key in {node.key for node in hidden.nodes}
                                and edge.to_key in {node.key for node in hidden.nodes}
                                for edge in hidden.edges))
            app.checkbox[0].uncheck().run()
            self.assertEqual(len(render_graph.call_args.args[0].nodes), len(graph.nodes))
            self.assertEqual(len(graph.nodes), len(self.make_graph(depth=2).nodes))
            self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
