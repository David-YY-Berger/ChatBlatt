# bs'd
from backend.db.Collections import CollectionObjs
from backend_pipeline.data_pipeline.DBScriptParentClass import DBParentClass
from backend.faiss_api import FaissEngine


class DBPopulateFaiss(DBParentClass):

    def setUp(self):
        """Runs before every test to set up directories and lazy init Faiss."""
        super().setUp()  # call parent setup first
        self.faiss = FaissEngine.FaissEngine(dbapi=self.db_api)

    def tearDown(self):
        super().tearDown()

        ############################################## Populating FAISS ###############################################

    def test_populate_faiss_index(self):
        self.faiss.clear_index()  # start from a totally clean FAISS index (both languages)

        # all_srcs = self.db_api.get_all_src_contents_of_collection(CollectionObjs.TN)
        # all_srcs = self.db_api.get_all_src_contents_of_collection(CollectionObjs.BT)
        all_srcs = (self.db_api.get_all_src_contents_of_collection(CollectionObjs.BT)
                    + self.db_api.get_all_src_contents_of_collection(CollectionObjs.TN))
        print(f"{len(all_srcs)} sources found")

        en_docs = [
            {
                "key": src.key,
                "content": src.get_clean_en_text(),
            }
            for src in all_srcs
        ]
        heb_docs = [
            {
                "key": src.key,
                "content": src.get_clean_heb_text(),
            }
            for src in all_srcs
        ]

        self.faiss.populate_bulk(
            en_docs,
            lang=FaissEngine.LANG_EN,
            batch_size=256,  # safe for CPU RAM; raise to 512 if you have more
            checkpoint_every=500,  # save to Mongo every 500 docs as crash insurance
        )
        self.faiss.populate_bulk(
            heb_docs,
            lang=FaissEngine.LANG_HEB,
            batch_size=256,
            checkpoint_every=500,
        )

        results = self.faiss.search("leading the battle", 20, lang=FaissEngine.LANG_EN)
        for r in results:
            print(r)

        heb_results = self.faiss.search("קרב", 20, lang=FaissEngine.LANG_HEB)
        for r in heb_results:
            print(r)