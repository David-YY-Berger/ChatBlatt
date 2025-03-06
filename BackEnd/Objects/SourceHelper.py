from BackEnd.Objects import Source


def get_BT_list_from_raw_json(raw_json) -> list[Source]:
    src_list = []
    type = Source.SourceType.BT
    book = ""
    section_pref = ""
    chapter = 0 # hard to get for BT

    for i, entry in enumerate(raw_json.text):  # Iterate with index
        section = f"{section_pref}_{i}"  # Use index as section number
        en_content = entry  # Entry is already the English text
        he_content = raw_json.he[i] if i < len(raw_json.he) else ""  # Handle Hebrew safely
        src_list.append(
            Source.Source(src_type=type, book=book, chapter=chapter, section=section, content=[en_content, he_content]))

    # todo must try it!
    return src_list

