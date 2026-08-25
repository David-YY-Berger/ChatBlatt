# bs"d - lehagdil torah velahadir
"""
Shared constants for the text-similarity engines (FAISS + BM25 today; any
future engine tomorrow), so every engine and every layer that talks about
them (persistence, search handler, population scripts) speaks the same
language for language codes and engine "kind" identifiers - one source of
truth instead of each engine redefining its own copy.
"""

# Supported similarity-index languages. Each language gets its own fully
# separate index + metadata list *per engine*, so an English query is only
# ever ranked against English content and a Hebrew query only against
# Hebrew content.
LANG_EN = "en"
LANG_HEB = "heb"
SUPPORTED_LANGS = (LANG_EN, LANG_HEB)

# Identifies *which* similarity engine an index belongs to. Used by the
# persistence layer (see backend.db.mongo_parts.similarity_index_mixin) to
# pick the right GridFS bucket/filenames, and in log lines, so a single
# generic mixin/interface can serve every engine's (kind, lang) index pair
# completely independently of every other one.
KIND_FAISS = "faiss"
KIND_BM25 = "bm25"
SUPPORTED_KINDS = (KIND_FAISS, KIND_BM25)
