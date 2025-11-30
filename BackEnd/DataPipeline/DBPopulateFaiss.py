# bs'd
from BackEnd.DataObjects.Enums import SourceContentType
from BackEnd.DataPipeline.DB.Collections import CollectionName
from BackEnd.DataPipeline.DBParentClass import DBParentClass
from BackEnd.DataPipeline.FAISS_api import FaissEngine
from BackEnd.General import miscFuncs


class DBPopulateSourceContentAndFaiss(DBParentClass):

    def setUp(self):
        """Runs before every test to set up directories and lazy init Faiss."""
        super().setUp()  # call parent setup first
        self.faiss = FaissEngine.FaissEngine(dbapi=self.db_api)

    def tearDown(self):
        super().tearDown()

        ############################################## Populating FAISS ###############################################

    def test_populate_faiss_index(self):
        """
        very slow function (on BT, ran for 3.5 hrs till failed), but works well. could be improved, but not worth it, it only needs to run once.
        must NOT interrupt in the middle... then you must delete faiss_data and rerun all collections all over again..
        very possible for mongo connection to be broken.. best to somehow mark exactly which passages where added to FAISS and which were not.

        TN - runs for 55 m
        """
        # doc1 = {
        #     "key": "BT_Bava Batra_0_4a:10-11",
        #     "content": "The mishna teaches: In a place where it is customary to build a wall of non-chiseled stone, or chiseled stone, or small bricks, or large bricks, they must build the partition with that material. Everything is in accordance with the regional custom. The Gemara asks: What does the word everything serve to add? The Gemara answers: It serves to add a place where it is customary to build a partition out of palm and laurel branches. In such a place, the partition is built from those materials.The mishna teaches: Therefore, if the wall later falls, the assumption is that the space where the wall stood and the stones belong to both of them, to be divided equally. The Gemara questions the need for this ruling: Isn’t it obvious that this is the case, since both neighbors participated in the construction of the wall? The Gemara answers: No, it is necessary to teach this halakha for a case where the entire wall fell into the domain of one of them. Alternatively, it is necessary in a case where one of them already cleared all the stones into his own domain. Lest you say that the other party should be governed by the principle that the burden of proof rests upon the claimant, that is, if the other party should have to prove that he had been a partner in the construction of the wall, the mishna teaches us that they are presumed to have been partners in the building of the wall, and neither requires further proof."
        # }
        # doc2 = {
        #     "key" :" BT_Bava Batra_0_2a:1-5",
        #     "content": "MISHNA: Partners who wished to make a partition [meḥitza] in a jointly owned courtyard build the wall for the partition in the middle of the courtyard. What is this wall fashioned from? In a place where it is customary to build such a wall with non-chiseled stone [gevil], or chiseled stone [gazit], or small bricks [kefisin], or large bricks [leveinim], they must build the wall with that material. Everything is in accordance with the regional custom.If they build the wall with non-chiseled stone, this partner provides three handbreadths of his portion of the courtyard and that partner provides three handbreadths, since the thickness of such a wall is six handbreadths. If they build the wall with chiseled stone, this partner provides two and a half handbreadths and that partner provides two and a half handbreadths, since such a wall is five handbreadths thick. If they build the wall with small bricks, this one provides two handbreadths and that one provides two handbreadths, since the thickness of such a wall is four handbreadths. If they build with large bricks, this one provides one and a half handbreadths and that one provides one and a half handbreadths, since the thickness of such a wall is three handbreadths. Therefore, if the wall later falls, the assumption is that the space where the wall stood and the stones belong to both of them, to be divided equally.And similarly with regard to a garden, in a place where it is customary to build a partition in the middle of a garden jointly owned by two people, and one of them wishes to build such a partition, the court obligates his neighbor to join in building the partition. But with regard to an expanse of fields [babbika], in a place where it is customary not to build a partition between two people’s fields, and one person wishes to build a partition between his field and that of his neighbor, the court does not obligate his neighbor to build such a partition.Rather, if one person wishes to erect a partition, he must withdraw into his own field and build the partition there. And he makes a border mark on the outer side of the barrier facing his neighbor’s property, indicating that he built the entire structure of his own materials and on his own land. Therefore, if the wall later falls, the assumption is that the space where the wall stood and the stones belong only to him, as is indicated by the mark on the wall.Nevertheless, in a place where it is not customary to build a partition between two people’s fields, if they made such a partition with the agreement of the two of them, they build it in the middle, i.e., on the property line, and make a border mark on the one side and on the other side. Therefore, if the wall later falls, the assumption is that the space where the wall stood and the stones belong to both of them, to be divided equally."
        # }
        # self.faiss.add_documents([doc1, doc2])
        # all_srcs = self.db_api.get_all_source_contents(CollectionName.BT)

        all_srcs = self.db_api.get_all_src_contents_of_collection(CollectionName.TN)
        # must put here ^^ every collection separately...
        print(f"{len(all_srcs)} sources found")
        for src in all_srcs:
            cleaned_content = src.get_clean_en_text()
            self.faiss.add_documents([
                {
                    "key": src.key,
                    "content": cleaned_content,
                }
            ])

        results = self.faiss.search("leading the battle", 20)  # just to show that it works...
        for r in results:
            print(r)