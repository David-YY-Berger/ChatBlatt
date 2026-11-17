import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import research_mcp as research
from backend.app.logic.number_validation import number_error
from backend.models_db.EntityObjects.EPerson import EPerson
from backend.models_db.Enums import EntityType, RelType
from backend.models_db.Rel import Rel
from backend.models_db.SourceClasses.SourceContent import SourceContent
from backend.models_db.SourceClasses.SourceMetadata import SourceMetadata
from backend.models_dto.GenealogyGraphData import GenealogyEdge, GenealogyGraphData, GenealogyNode
from backend.models_dto.PersonSelectOption import PersonSelectOption
from backend.app.logic.lineage_logic import LineageGraph
from starlette.testclient import TestClient
from backend.db.DBFactory import DBFactory
from backend.db.DBapiMongoDB import DBapiMongoDB


class ResearchMcpTests(unittest.TestCase):
    def test_fuzzy_names_and_disambiguating_metadata(self):
        opts = [
            PersonSelectOption(key="1", display_en_name="yishay", display_heb_name="ישי", roles=["King"]),
            PersonSelectOption(key="2", display_en_name="ishai", roles=["Prophet"]),
            PersonSelectOption(key="3", display_en_name="moses"),
        ]
        with patch.object(research, "options", return_value=opts):
            page = research.find_entities("people", "ishai", limit=1)
            self.assertEqual(page["total"], 2)
            self.assertEqual(page["items"][0]["key"], "2")
            self.assertEqual(page["next_offset"], 1)
            king = research.find_entities("people", "ishai", roles=["King"])
            self.assertEqual(king["items"][0]["key"], "1")
            self.assertEqual(king["items"][0]["display_heb_name"], "ישי")
            all_kings = research.find_entities("people", roles=["King"])
            self.assertEqual([item["key"] for item in all_kings["items"]], ["1"])

    def test_number_validation_matches_ui_rules(self):
        for value in ("0", "1", "-3", "1.5", "1/0", "0/2", "2/2", "1//2"):
            self.assertIsNotNone(number_error(value), value)
            with self.assertRaises(research.InputError):
                research.search_number(value)
        for value in ("2", "1/3", "3/2"):
            self.assertIsNone(number_error(value))

    def test_mixed_language_rejected_before_backend(self):
        with patch.object(research, "db") as database:
            with self.assertRaisesRegex(research.InputError, "mix Hebrew and English"):
                research.search_sources(text="שלום hello")
            database.assert_not_called()

    def test_excluded_relationships_cannot_be_queried(self):
        for rel_type in (RelType.studiedFrom, RelType.disagreedWith):
            database = Mock()
            database.get_rels_by_keys.return_value = [Rel(key="r", term1="a", term2="b", rel_type=rel_type)]
            with patch.object(research, "db", return_value=database):
                with self.assertRaises(research.InputError):
                    research.search_sources(relationship_keys=["r"])

    def test_entity_relationships_exclude_warned_types(self):
        person = EPerson(key="a", display_en_name="alice")
        other = EPerson(key="b", display_en_name="bob")
        rels = [
            Rel(key="bad", term1="a", term2="b", rel_type=RelType.studiedFrom),
            Rel(key="bad2", term1="a", term2="b", rel_type=RelType.disagreedWith),
            Rel(key="good", term1="a", term2="b", rel_type=RelType.spouseOf),
        ]
        database = Mock()
        database.get_entity_by_key.return_value = person
        database.get_rels_for_entity.return_value = rels
        database.get_entities_by_keys.return_value = [person, other]
        with patch.object(research, "db", return_value=database):
            result = research.get_entity("people", "a")
        items = result["relationships"]["items"]
        self.assertEqual([entry["field"] for entry in items], ["spouseOf"])
        self.assertEqual(items[0]["relationship_keys"], ["good"])

    def test_source_search_is_bounded_and_linked(self):
        source = SourceMetadata(key="TN_Genesis_0_1:1", summary_en="Example")
        handler = Mock()
        handler.get_answer_w_source_metadata.return_value = SimpleNamespace(
            src_metadata_lst=[source], total_sources=3,
        )
        with patch.object(research, "db"), patch.object(research, "SourceSearchHandler", return_value=handler):
            result = research.search_sources(text="creation", limit=1, offset=1)
        query = handler.get_answer_w_source_metadata.call_args.args[0]
        self.assertEqual(query.offset, 1)
        self.assertEqual(query.max_sources, 1)
        self.assertEqual([v.name for v in query.src_types], ["TN", "BT"])
        self.assertEqual(result["next_offset"], 2)
        self.assertEqual(result["items"][0]["key"], source.key)
        self.assertNotIn("content", result["items"][0])
        self.assertIn("source_search?", result["url"])

    def test_number_option_expands_for_source_search_but_not_in_entity_output(self):
        option = SimpleNamespace(key="first", entity_keys=["first", "second"])
        handler = Mock()
        handler.get_answer_w_source_metadata.return_value = SimpleNamespace(src_metadata_lst=[], total_sources=0)
        with patch.object(research, "db"), \
             patch.object(research, "entity_for", return_value=SimpleNamespace(entityType=EntityType.ENumber)), \
             patch.object(research, "options", return_value=[option]), \
             patch.object(research, "SourceSearchHandler", return_value=handler):
            research.search_sources(entity_keys=["first"])
        query = handler.get_answer_w_source_metadata.call_args.args[0]
        self.assertEqual(query.entity_ids, ["first", "second"])

    def test_source_text_language_and_pagination(self):
        database = Mock()
        database.get_source_metadata_by_key.return_value = SourceMetadata(key="TN_Genesis_0_1:1")
        database.find_one_source_content.return_value = SourceContent(
            key="TN_Genesis_0_1:1", content=["<b>English</b> text", "<b>עברית</b> כאן"],
        )
        with patch.object(research, "db", return_value=database):
            result = research.get_source_text("TN_Genesis_0_1:1", "he", max_characters=4)
        self.assertEqual(result["text"], "עברי")
        self.assertEqual(result["next_offset"], 4)

    def test_family_graph_edges_carry_source_relationship_keys(self):
        graph = GenealogyGraphData(
            center_key="a",
            nodes=[GenealogyNode(key="a", display_name="alice"), GenealogyNode(key="b", display_name="bob")],
            edges=[GenealogyEdge(from_key="a", to_key="b", rel_type="childOfFather")],
        )
        database = Mock()
        database.get_rels_for_entities.return_value = [
            Rel(key="parent-rel", term1="a", term2="b", rel_type=RelType.childOfFather)
        ]
        controller = Mock()
        controller.get_genealogy_graph.return_value = graph
        with patch.object(research, "db", return_value=database), \
             patch.object(research, "entity_for"), \
             patch.object(research, "GenealogyTreeController", return_value=controller):
            result = research.family_tree("a")
        self.assertEqual(result["edges"]["items"][0]["relationship_keys"], ["parent-rel"])
        self.assertEqual(len(result["nodes"]), 2)

    def test_lineage_candidates_and_steps_carry_source_keys(self):
        options = [PersonSelectOption(key="a", display_en_name="alice"),
                   PersonSelectOption(key="b", display_en_name="bob")]
        rel = Rel(key="parent-rel", term1="a", term2="b", rel_type=RelType.childOfFather)
        graph = LineageGraph(options, [rel])
        database = Mock()
        database.get_rels_for_entities.return_value = [rel]
        with patch.object(research, "db", return_value=database), \
             patch.object(research, "entity_for"), \
             patch.object(research, "load_lineage_graph", return_value=graph):
            candidates = research.lineage_candidates("b", "descendants")
            result = research.lineage("b", "a", "descendants")
        self.assertEqual(candidates["items"][0]["key"], "a")
        self.assertEqual(result["steps"]["items"][0]["relationship_keys"], ["parent-rel"])

    def test_mcp_requires_read_only_mode(self):
        with patch.dict(os.environ, {"EITZ_DB_READ_ONLY": "false"}):
            with patch.object(research.DBFactory, "get_prod_db_mongo") as factory:
                with self.assertRaises(RuntimeError):
                    research.db()
                factory.assert_not_called()

    def test_app_factory_always_uses_read_only_account_and_does_not_create_indexes(self):
        names = []

        def secret(name):
            names.append(name)
            return {
                "DB_READ_ONLY_USERNAME": "reader",
                "DB_READ_ONLY_PASSWORD": "password",
                "DB_BT_USERNAME": "population",
                "DB_BT_PASSWORD": "population-password",
            }[name]

        with patch.dict(os.environ, {"EITZ_DB_READ_ONLY": "false"}), \
             patch("backend.db.DBFactory.get_secret", side_effect=secret), \
             patch("backend.db.DBFactory.DBapiMongoDB") as constructor:
            DBFactory.get_prod_db_mongo()
        self.assertEqual(names, ["DB_READ_ONLY_USERNAME", "DB_READ_ONLY_PASSWORD"])
        self.assertFalse(constructor.call_args.kwargs["ensure_indexes"])

        instance = DBapiMongoDB.__wrapped__(ensure_indexes=False)
        with patch("backend.db.DBapiMongoDB.MongoClient") as client, \
             patch.object(instance, "_ensure_indexes") as ensure:
            instance.connect("mongodb://example.invalid")
            client.return_value.admin.command.assert_called_once_with("ping")
            ensure.assert_not_called()

    def test_population_factory_uses_population_account_and_creates_indexes(self):
        names = []

        def secret(name):
            names.append(name)
            return {
                "DB_READ_ONLY_USERNAME": "reader",
                "DB_READ_ONLY_PASSWORD": "password",
                "DB_BT_USERNAME": "population",
                "DB_BT_PASSWORD": "population-password",
            }[name]

        with patch("backend.db.DBFactory.get_secret", side_effect=secret), \
             patch("backend.db.DBFactory.DBapiMongoDB") as constructor:
            DBFactory.get_population_db_mongo()
        self.assertEqual(names, ["DB_BT_USERNAME", "DB_BT_PASSWORD"])
        self.assertTrue(constructor.call_args.kwargs["ensure_indexes"])

    def test_protocol_errors_do_not_expose_backend_exception(self):
        app = research.mcp.streamable_http_app()
        with patch.object(research, "_enqueue_mcp_metric") as enqueue, \
             TestClient(app, base_url="http://127.0.0.1:8502") as client:
            headers = {"Accept": "application/json, text/event-stream"}
            initialized = client.post("/mcp", headers=headers, json={
                "jsonrpc": "2.0", "id": 0, "method": "initialize",
                "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                           "clientInfo": {"name": "test", "version": "1"}},
            })
            self.assertEqual(initialized.status_code, 200)
            self.assertIn("serverInfo", initialized.json()["result"])
            listing = client.post("/mcp", headers=headers, json={
                "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
            })
            self.assertEqual(listing.status_code, 200)
            tools = listing.json()["result"]["tools"]
            self.assertTrue(all(tool["annotations"]["readOnlyHint"] for tool in tools))
            self.assertNotIn("studied_from", {tool["name"] for tool in tools})
            with patch.object(research, "options", side_effect=RuntimeError("secret-value")):
                admin_response = client.post("/mcp?admin=true", headers=headers, json={
                    "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                    "params": {"name": "find_entities", "arguments": {"name": "david", "entity_type": "people"}},
                })
            self.assertEqual(admin_response.status_code, 200)
            self.assertTrue(admin_response.json()["result"]["isError"])
            self.assertNotIn("secret-value", admin_response.text)
            enqueue.assert_not_called()
            conflicting_admin_response = client.post(
                "/mcp?admin=false&admin=true", headers=headers, json={
                    "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": "find_entities",
                               "arguments": {"name": "david", "entity_type": "people"}},
                },
            )
            self.assertTrue(conflicting_admin_response.json()["result"]["isError"])
            enqueue.assert_not_called()

            with patch.object(research, "options", side_effect=RuntimeError("secret-value")):
                failure = client.post("/mcp?admin=false", headers=headers, json={
                    "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                    "params": {"name": "find_entities",
                               "arguments": {"name": "david", "entity_type": "people"}},
                })
            self.assertTrue(failure.json()["result"]["isError"])
            with patch.object(research, "options", return_value=[]):
                success = client.post("/mcp", headers=headers, json={
                    "jsonrpc": "2.0", "id": 4, "method": "tools/call",
                    "params": {"name": "find_entities",
                               "arguments": {"entity_type": "people", "name": "none"}},
                })
            self.assertFalse(success.json()["result"]["isError"])

        self.assertEqual(
            [(entry.args[0], entry.args[1]) for entry in enqueue.call_args_list],
            [("find_entities", "failure"), ("find_entities", "success")],
        )
        self.assertTrue(all(isinstance(entry.args[2], int) for entry in enqueue.call_args_list))

    def test_mcp_ga4_metric_uses_private_server_side_configuration(self):
        event = {"tool_name": "search_sources", "outcome": "failure", "duration_ms": 42}
        with patch.dict(os.environ, {
            "GA4_MEASUREMENT_ID": "G-TEST123",
            "GA4_API_SECRET": "test-secret",
        }), patch.object(research.requests, "post") as post:
            post.return_value.status_code = 204
            research._send_mcp_metric(event)

        post.assert_called_once_with(
            "https://www.google-analytics.com/mp/collect",
            params={"measurement_id": "G-TEST123", "api_secret": "test-secret"},
            json={
                "client_id": "eitz-habina-mcp-server",
                "events": [{"name": "mcp_tool_call", "params": event}],
            },
            timeout=(1, 3),
        )


if __name__ == "__main__":
    unittest.main()
