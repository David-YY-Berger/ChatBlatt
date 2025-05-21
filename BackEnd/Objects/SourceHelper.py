from BackEnd.Objects import SourceClasses
from BackEnd.Objects.SourceClasses import Source, SourceContentType


# def get_BT_list_from_raw_json(raw_json) -> list[Source]:
#     src_list = []
#     type = SourceClasses.SourceType.BT
#     book = ""
#     section_pref = ""
#     chapter = 0 # hard to get for BT
#
#     for i, entry in enumerate(raw_json.text):  # Iterate with index
#         section = f"{section_pref}_{i}"  # Use index as section number
#         content = []
#         content[SourceContentType.EN_CONTENT.value] = entry  # Entry is already the English text
#         content[SourceContentType.HEB_CONTENT.value] = raw_json.he[i] if i < len(raw_json.he) else ""  # Handle Hebrew safely
#
#         src_list.append(
#             SourceClasses.Source(src_type=type, book=book, chapter=chapter, section=section, content=content))
#
#     # todo must try it!
#     return src_list

