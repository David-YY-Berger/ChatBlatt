# bs'd
from enum import Enum
from typing import List, Union

from backend.data_pipeline.DBScriptParentClass import DBParentClass
from backend.models_db.Enums import EntityType, RelType


class TestsPopulateEntityRelGraphFromJson(DBParentClass):

    ABRAHAM = {
        # --- scalar entity fields ---
        "display_en_name": "abraham",
        "alias_keys":    [],
        "timePeriod":    None,
        "isWoman":       False,
        "isNonJew":      False,
        "isGroup":       False,
        "roles":         [],
        # --- related entities (rel_type → (expected_names, direction)) ---
        # direction: "outgoing" = entity is term1, "incoming" = entity is term2, "both" = either
        "childOfFather":       (["Father"],                                                                  "outgoing"),
        "children":            (["Ishmael", "Isaac", "Zimran", "Jokshan", "Medan", "Midian", "Ishbak", "Shuah"], "incoming"),
        "siblings":            (["Wife", "Joseph"],                                                          "siblings"),
        "spouseOf":            (["Sarai", "Sarah", "Wife", "Keturah"],                                       "both"),
        "spokeWith":           (["God", "They", "Sarah", "Hashem", "Abimelech", "Wife", "Phicol",
                                 "Servants", "Isaac", "Messenger Of Hashem", "Hittites", "Ephron"],          "both"),
        "allyOf":              (["Abimelech", "Hashem", "The Man"],                                          "both"),
        "enemyOf":             (["Abimelech", "Canaan", "Philistines"],                                      "both"),
        "bornIn":              (["Aram-Naharaim", "Nahor"],                                                  "outgoing"),
        "diedIn":              (["Machpelah"],                                                               "outgoing"),
        "visited":             (["Tent", "Sodom", "Gomorrah", "Plain", "Negeb", "Kadesh", "Shur",
                                 "Gerar", "Beer-Sheba", "Moriah", "Adonai-Yireh", "Mount Of Hashem",
                                 "Kiriath-Arba", "Hebron", "Canaan", "Machpelah", "Mamre", "Towns Gate"],   "outgoing"),
        "prayedAt":            (["Beer-Sheba"],                                                              "outgoing"),
        "associatedWithPlace": (["Canaan", "Under The Tree", "Beer-Sheba", "Land Of The Philistines",
                                 "House", "Gerar", "Land", "Mamre", "Kiriath-Arba", "Hebron",
                                 "Machpelah", "The Land"],                                                   "outgoing"),
    }
    HEBRON = {
        "display_en_name": "hebron",
        "display_heb_name": "",
        "all_en_names":  ["Hebron"],
        "all_heb_names": [],
        "entityType":    "EPlace",
        "alias_keys":    [],
        "placeType":     None,
        # direction is from Hebron's perspective
        "diedIn":              (["Sarah", "Isaac"],                        "incoming"),
        "visited":             (["Abram", "Abraham", "Jacob"],             "incoming"),
        "prayedAt":            (["Abram"],                                 "incoming"),
        "associatedWithPlace": (["Abraham", "Israel"],                     "incoming"),
        "placeToNation":       (["Hittites", "Canaan"],                    "outgoing"),
    }
    EGYPT_NATION = {
        "display_en_name": "egypt",
        "display_heb_name": "",
        "all_en_names":  ["Egypt"],
        "all_heb_names": [],
        "entityType":    "ENation",
        "alias_keys":    [],
        # relationships
        "personBelongsToNation": (["Hagar", "Egyptians", "Brothers", "Father's Household", "Fathers"], "incoming"),
        "placeToNation":         (["River Of Egypt", "Shur", "Goshen"],                                 "incoming"),
        "enemyOf":               (["Offspring"],                                                         "both"),
        "contrastedWith":        (["Hebrew"],                                                            "both"),
    }
    EGYPT_PLACE = {
        "display_en_name": "egypt",
        "display_heb_name": "",
        "all_en_names":  ["Egypt"],
        "all_heb_names": [],
        "entityType":    "EPlace",
        "alias_keys":    [],
        "placeType":     None,
        # relationships
        "bornIn":              (["Manasseh", "Ephraim"],                                                          "incoming"),
        "diedIn":              (["Israel", "Joseph"],                                                             "incoming"),
        "visited":             (["Abram", "Sarai", "Lot", "Ishmaelites", "Midianites", "Joseph",
                                 "All The World", "Joseph's Brothers", "Sons Of Israel", "Brothers",
                                 "Benjamin", "Jacob", "Children Of Israel", "Israel", "God",
                                 "Israelites"],                                                                    "incoming"),
        "associatedWithPlace": (["Potiphar's Wife", "Magician-Priests Of Egypt", "Sages", "Joseph",
                                 "Pharaoh", "Egyptians", "Priests"],                                             "incoming"),
        "comparedTo":          (["Jordan"],                                                                       "both"),
    }
    JACOB = {
        "display_en_name": "jacob",
        "display_heb_name": "",
        "all_en_names":  ["Jacob"],
        "all_heb_names": [],
        "entityType":    "EPerson",
        "alias_keys":    [],
        "timePeriod":    None,
        "isWoman":       False,
        "isNonJew":      False,
        "isGroup":       False,
        "roles":         [],
        # relationships
        "childOfFather":        (["Isaac"],                                                                      "outgoing"),
        "childOfMother":        (["Rebekah"],                                                                    "outgoing"),
        "children":             (["Dan", "Naphtali", "Gad", "Asher", "Reuben", "Issachar", "Zebulun",
                                  "Dinah", "Joseph", "Sons", "Simeon", "Levi", "Sons Of Jacob",
                                  "Benjamin", "Judah", "Brothers", "Joseph's Brothers",
                                  "Children Of Israel", "Sons Of Israel"],                                       "incoming"),
        "siblings":             (["Esau"],                                                                       "siblings"),
        "spouseOf":             (["Rachel", "Leah", "Bilhah", "Wives", "Maids", "Zilpah"],                     "both"),
        "descendantOf":         (["Abraham", "Isaac"],                                                          "outgoing"),
        "spokeWith":            (["Esau", "Rebekah", "Isaac", "Hashem", "Shepherds", "Rachel", "Laban",
                                  "Leah", "Messenger Of God", "Messengers Of God", "Messengers",
                                  "Servants", "Agent", "Hamor", "Shechem", "Simeon", "Levi", "God",
                                  "Household", "All Who Were With Him", "Joseph", "Joseph's Brothers",
                                  "Reuben", "The Brothers", "Children Of Israel", "Pharaoh",
                                  "El Shaddai", "Jacob's Sons"],                                                 "both"),
        "disagreedWith":        (["Laban's Sons", "Laban", "Simeon", "Levi"],                                   "both"),
        "allyOf":               (["Laban", "Esau"],                                                             "both"),
        "enemyOf":              (["Esau", "Laban", "Agent", "Canaan", "Perizzites", "Amorites"],                "both"),
        "diedIn":               (["Canaan"],                                                                     "outgoing"),
        "visited":              (["Haran", "Paddan-Aram", "Beer-Sheba", "Bethel", "Father's House",
                                  "Land Of The Easterners", "Well", "Field", "Troughs",
                                  "Water Receptacles", "Euphrates", "Gilead", "Gal-Ed", "Mizpah",
                                  "Height", "Mahanaim", "Jordan", "Jabbok", "Peniel", "Penuel",
                                  "Succoth", "Shechem", "Canaan", "Luz", "Ephrath", "Mamre",
                                  "Kiriath-Arba", "Hebron", "Goshen", "Egypt", "Rameses",
                                  "Machpelah"],                                                                   "outgoing"),
        "prayedAt":             (["Bethel", "Height", "Beer-Sheba"],                                            "outgoing"),
        "associatedWithPlace":  (["House", "Field", "Canaan", "The Height", "Seir", "Paddan-Aram",
                                  "Sheol", "The Land"],                                                          "outgoing"),
        "personBelongsToNation":(["Israel", "Egypt"],                                                           "outgoing"),
        "prophesiedAbout":      (["Simeon", "Levi", "Israel", "Joseph"],                                        "outgoing"),
        "comparedTo":           (["Esau", "Ancestors"],                                                         "both"),
        "contrastedWith":       (["Esau", "Canaan", "Simeon", "Levi"],                                          "both"),
    }

    # ------------------------------------------------------------------ #

    def setUp(self):
        super().setUp()

    def tearDown(self):
        pass

    # ------------------------------------------------------------------ #
    #  Main test                                                           #
    # ------------------------------------------------------------------ #

    def test_populate_graph(self):
        self.remove_repopulate_graph()

        self._assert_entity_snapshot(self.ABRAHAM)
        self._assert_entity_snapshot(self.HEBRON)
        self._assert_entity_snapshot(self.EGYPT_NATION)
        self._assert_entity_snapshot(self.EGYPT_PLACE)
        self._assert_entity_snapshot(self.JACOB)

    def remove_repopulate_graph(self):
        # 1. Remove all entities and relationships
        deleted_entities = self.db_api.drop_all_entities()
        deleted_rels = self.db_api.drop_all_rels()
        print(f"Dropped {deleted_entities} entities and {deleted_rels} rels before populate.")

        # 2. Run the populator
        from backend.data_pipeline.populator_scripts.DBPopulateEntityRelGraph import DBPopulateLmmData
        populator = DBPopulateLmmData('test_populate_entities_and_rels_from_jsons')
        populator.db_api = self.db_api  # share the live connection
        populator.setUp()
        populator.test_populate_entities_and_rels_from_jsons()

    # ------------------------------------------------------------------ #
    #  Helpers – unified snapshot assertion                               #
    # ------------------------------------------------------------------ #

    # Relationship keys that are NOT RelType names but need special handling
    _CHILDREN_KEY = "children"
    _SIBLINGS_KEY = "siblings"

    def _assert_entity_snapshot(self, snapshot: dict) -> None:
        """
        Drive the full entity assertion from a single snapshot dict.

        Keys whose values are plain Python scalars / lists (non-tuple) are
        compared against the DB document fields.
        Keys whose values are a (list, direction_str) tuple are treated as
        relationship assertions (direction "siblings" triggers _assert_siblings).
        """
        # Separate scalar fields from rel entries
        scalar_keys = {k for k, v in snapshot.items() if not isinstance(v, tuple)}
        rel_keys    = {k for k, v in snapshot.items() if isinstance(v, tuple)}

        # ── 1. scalar / db-field assertions ──────────────────────────────
        en_name         = snapshot["display_en_name"]
        entity_type_str = snapshot["entityType"]
        entity_type     = self._parse_entity_type(entity_type_str)

        print(f"Asserting {en_name} entity type {entity_type_str}")

        matches = self.db_api.search_entities_by_name(en_name, entity_type)
        matches = [e for e in matches if e.display_en_name.lower() == en_name.lower()]
        self.assertTrue(len(matches) > 0,
                        f"Entity '{en_name}' ({entity_type_str}) not found in DB.")

        actual_dict = matches[0].to_db_dict()
        actual_dict.pop("key", None)
        entity_key = matches[0].key

        for field in scalar_keys:
            if field == "key":
                continue
            exp_value = snapshot[field]

            if exp_value is None:
                actual_value = actual_dict.get(field)
                self.assertIsNone(actual_value,
                    f"Field '{field}' expected null/absent for '{en_name}', got: {actual_value!r}")
                continue

            self.assertIn(field, actual_dict,
                          f"Field '{field}' missing on entity '{en_name}' in DB.")
            actual_value = actual_dict[field]

            if isinstance(actual_value, Enum):
                actual_value = actual_value.name

            if isinstance(exp_value, list) and isinstance(actual_value, list):
                norm_actual = [v.name if isinstance(v, Enum) else str(v) for v in actual_value]
                self.assertEqual(sorted(str(v) for v in exp_value), sorted(norm_actual),
                    f"Field '{field}' mismatch for '{en_name}': expected {exp_value}, got {actual_value}")
            else:
                self.assertEqual(exp_value, actual_value,
                    f"Field '{field}' mismatch for '{en_name}': expected {exp_value!r}, got {actual_value!r}")

        # ── 2. relationship assertions ────────────────────────────────────
        for rel_key in rel_keys:
            expected_names, direction = snapshot[rel_key]

            if direction == "siblings":
                self._assert_siblings(entity_key, expected_names)
                continue

            # "children" uses childOfFather + childOfMother (incoming)
            if rel_key == self._CHILDREN_KEY:
                rel_types = [RelType.childOfFather, RelType.childOfMother]
            else:
                rel_types = [RelType[rel_key]]

            self._assert_rel_names(entity_key, rel_types, expected_names,
                                   direction=direction, label=rel_key)
    # ------------------------------------------------------------------ #

    def _get_entity(self, name: str, entity_type: EntityType):
        """Return the first DB entity exactly matching *name* and *entity_type*."""
        matches = self.db_api.search_entities_by_name(name, entity_type)
        matches = [e for e in matches if e.display_en_name.lower() == name.lower()]
        return matches[0] if matches else None

    def _get_connected_names(
        self,
        entity_key: str,
        rel_types: Union[RelType, List[RelType]],
        direction: str = "both",
    ) -> List[str]:
        """
        Return display names of all entities connected to *entity_key* via
        *rel_types*.

        direction:
          "outgoing" → entity_key == term1
          "incoming" → entity_key == term2
          "both"     → entity_key on either side
        """
        if isinstance(rel_types, RelType):
            rel_types = [rel_types]

        all_rels = self.db_api.get_rels_for_entity(entity_key)
        other_keys = []
        for r in all_rels:
            if r.rel_type not in rel_types:
                continue
            is_term1 = (r.term1 == entity_key)
            is_term2 = (r.term2 == entity_key)
            if direction == "outgoing" and is_term1:
                other_keys.append(r.term2)
            elif direction == "incoming" and is_term2:
                other_keys.append(r.term1)
            elif direction == "both":
                other_keys.append(r.term2 if is_term1 else r.term1)

        entities = self.db_api.get_entities_by_keys(other_keys) if other_keys else []
        return [e.display_en_name for e in entities]

    def _assert_rel_names(
        self,
        entity_key: str,
        rel_types: Union[RelType, List[RelType]],
        expected_names: List[str],
        direction: str = "both",
        label: str = "",
    ) -> None:
        """Assert that every name in *expected_names* appears among connected entities."""
        actual_names = self._get_connected_names(entity_key, rel_types, direction)
        actual_lower = [n.lower() for n in actual_names]
        for name in expected_names:
            self.assertIn(
                name.lower(), actual_lower,
                f"[{label}] Expected related entity '{name}' not found. "
                f"Got: {actual_names}"
            )

    def _assert_siblings(self, entity_key: str, expected_names: List[str]) -> None:
        """
        Assert that each name in *expected_names* is a sibling of the entity –
        i.e. shares at least one parent (childOfFather or childOfMother) with it.
        """
        parent_rel_types = [RelType.childOfFather, RelType.childOfMother]

        # Step 1: find this entity's own parents
        parent_keys: set = set()
        rels = self.db_api.get_rels_for_entity(entity_key)
        for r in rels:
            if r.rel_type in parent_rel_types and r.term1 == entity_key:
                parent_keys.add(r.term2)

        if not parent_keys:
            if expected_names:
                self.fail(
                    f"Entity {entity_key} has no parents in DB; "
                    f"cannot verify siblings {expected_names}."
                )
            return

        # Step 2: collect all children of those parents (excluding entity itself)
        sibling_keys: set = set()
        for parent_key in parent_keys:
            for r in self.db_api.get_rels_for_entity(parent_key):
                if (r.rel_type in parent_rel_types
                        and r.term2 == parent_key
                        and r.term1 != entity_key):
                    sibling_keys.add(r.term1)

        siblings = self.db_api.get_entities_by_keys(list(sibling_keys)) if sibling_keys else []
        sibling_names_lower = [s.display_en_name.lower() for s in siblings]

        for name in expected_names:
            self.assertIn(
                name.lower(), sibling_names_lower,
                f"[siblings] Expected sibling '{name}' not found. "
                f"Got: {[s.display_en_name for s in siblings]}"
            )

    # ------------------------------------------------------------------ #
    #  Static utilities                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_entity_type(entity_type_str: str) -> EntityType:
        """
        Accept multiple formats:
          "EPerson"              → EntityType["EPerson"]
          "EntityType.EPerson"   → EntityType["EPerson"]
        """
        name = entity_type_str.split(".")[-1]
        return EntityType[name]

