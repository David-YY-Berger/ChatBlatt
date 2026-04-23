import unittest

from backend.db.Collections import CollectionObjs
from backend.db.interface_parts.base_interface import BaseInterfaceMixin
from backend.db.interface_parts.entity_interface import EntityInterfaceMixin
from backend.db.interface_parts.relationship_interface import RelationshipInterfaceMixin
from backend.db.interface_parts.source_content_interface import SourceContentInterfaceMixin
from backend.db.interface_parts.source_metadata_interface import SourceMetadataInterfaceMixin
from backend.models.EntityObjects.EFood import EFood
from backend.models.Enums import EntityType, RelType, SourceType
from backend.models.Rel import Rel
from backend.models.SourceClasses.SourceContent import SourceContent
from backend.models.SourceClasses.SourceMetadata import SourceMetadata


class DummyEntityInterface(EntityInterfaceMixin):
    def __init__(self, exists: bool):
        self.exists = exists
        self.insert_called = 0
        self.update_called = 0

    def is_entity_exists(self, key: str) -> bool:
        return self.exists

    def insert_entity(self, entity):
        self.insert_called += 1
        return "inserted"

    def update_entity(self, entity):
        self.update_called += 1
        return 1

    def get_entity_by_key(self, key: str):
        return None

    def get_entities_by_keys(self, keys):
        return []

    def get_entities_by_type(self, entity_type: EntityType):
        return []

    def get_all_entities(self):
        return []

    def search_entities_by_name(self, name: str, entity_type=None):
        return []

    def insert_entities_bulk(self, entities):
        return len(entities)

    def upsert_entities_bulk(self, entities):
        return (0, 0)


class DummyRelationshipInterface(RelationshipInterfaceMixin):
    def __init__(self, exists: bool):
        self.exists = exists
        self.insert_called = 0
        self.update_called = 0

    def is_rel_exists(self, key: str) -> bool:
        return self.exists

    def insert_rel(self, rel: Rel) -> str:
        self.insert_called += 1
        return "inserted"

    def update_rel(self, rel: Rel) -> int:
        self.update_called += 1
        return 1

    def get_rel_by_key(self, key: str):
        return None

    def get_rels_by_keys(self, keys):
        return []

    def get_rels_for_entity(self, entity_key: str):
        return []

    def get_all_rels(self):
        return []

    def insert_rels_bulk(self, rels):
        return len(rels)

    def upsert_rels_bulk(self, rels):
        return (0, 0)


class DummySourceMetadataInterface(SourceMetadataInterfaceMixin):
    def __init__(self, exists: bool):
        self.exists = exists
        self.insert_called = 0
        self.update_called = 0

    def is_src_metadata_exists(self, key: str) -> bool:
        return self.exists

    def insert_source_metadata(self, src_metadata: SourceMetadata) -> str:
        self.insert_called += 1
        return "inserted"

    def update_source_metadata(self, src_metadata: SourceMetadata) -> int:
        self.update_called += 1
        return 1

    def get_source_metadata_by_key(self, key: str):
        return None

    def get_all_source_metadata(self):
        return []


class DummySourceContentInterface(SourceContentInterfaceMixin):
    def __init__(self):
        self.stored = {}
        self.last_insert = None

    def insert(self, collection, data):
        self.last_insert = (collection, data)
        self.stored[(collection.name, data["key"])] = data
        return "ok"

    def update(self, collection, query, update):
        return 1

    def find_one(self, collection, key: str):
        return self.stored.get((collection.name, key))

    def _find_one_source_content_by_col(self, collection, key: str):
        doc = self.find_one(collection, key)
        if doc is None:
            raise KeyError(key)
        return SourceContent(key=doc["key"], content=doc["content"])

    def get_all_src_contents_of_collection(self, collection):
        return []


class InterfacePartsBasicTests(unittest.TestCase):
    def test_base_interface_is_marker_abc(self):
        self.assertEqual(BaseInterfaceMixin.__abstractmethods__, frozenset())

    def test_entity_upsert_updates_when_exists(self):
        repo = DummyEntityInterface(exists=True)
        entity = EFood(
            key="F_food",
            display_en_name="Bread",
            display_heb_name="lechem",
            all_en_names=["Bread"],
            all_heb_names=["lechem"],
        )

        key = repo.upsert_entity(entity)

        self.assertEqual(key, entity.key)
        self.assertEqual(repo.update_called, 1)
        self.assertEqual(repo.insert_called, 0)

    def test_entity_upsert_inserts_when_missing(self):
        repo = DummyEntityInterface(exists=False)
        entity = EFood(
            key="F_food",
            display_en_name="Bread",
            display_heb_name="lechem",
            all_en_names=["Bread"],
            all_heb_names=["lechem"],
        )

        key = repo.upsert_entity(entity)

        self.assertEqual(key, "inserted")
        self.assertEqual(repo.insert_called, 1)
        self.assertEqual(repo.update_called, 0)

    def test_rel_upsert_updates_when_exists(self):
        repo = DummyRelationshipInterface(exists=True)
        rel = Rel(key="R_1", term1="A", term2="B", rel_type=RelType.studiedFrom)

        key = repo.upsert_rel(rel)

        self.assertEqual(key, rel.key)
        self.assertEqual(repo.update_called, 1)
        self.assertEqual(repo.insert_called, 0)

    def test_source_metadata_upsert_inserts_when_missing(self):
        repo = DummySourceMetadataInterface(exists=False)
        metadata = SourceMetadata(source_type=SourceType.TN)
        metadata.key = "TN_Genesis_1_1"

        key = repo.upsert_source_metadata(metadata)

        self.assertEqual(key, "inserted")
        self.assertEqual(repo.insert_called, 1)
        self.assertEqual(repo.update_called, 0)

    def test_source_content_exists_and_find_one_source_content(self):
        repo = DummySourceContentInterface()
        content = SourceContent(key="BT_Bava_1_1", content=["<p>en</p>", "heb", ""])

        repo.insert_source_content(content, ref=None, start_index=0)

        self.assertTrue(repo.exists(CollectionObjs.BT, content.key))
        found = repo.find_one_source_content(content.key)
        self.assertEqual(found.key, content.key)
        self.assertEqual(found.content[0], "<p>en</p>")

    def test_source_content_find_one_source_content_invalid_key(self):
        repo = DummySourceContentInterface()

        with self.assertRaises(KeyError):
            repo.find_one_source_content("XX_Invalid_0_1")


if __name__ == "__main__":
    unittest.main()




