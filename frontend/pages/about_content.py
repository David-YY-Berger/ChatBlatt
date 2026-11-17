# bs"d - lehagdil torah velahadir

from __future__ import annotations

TABLE_OF_CONTENTS_TITLE = {
    "en": "Table of contents",
    "he": "תוכן העניינים",
}

LINKEDIN_PROFILE_URL = "https://www.linkedin.com/in/david-yy-berger/"

OPENING_QUOTE = """
<blockquote class="about-opening-quote">
  <p lang="he" dir="rtl">ישתבח הבורא ויתפאר היוצר, אשר הנחילנו חמדה גנוזה ויקרה, חכמה מפוארה, ליהודים היתה אורה (אסתר ח, טז), אורה זו תורה (מגילה טז:), לעבדה ולשמרה:...<br>
  אורייתא אורייתא, כמה חביבין אינון מלין דילך, מה אילנא אית ביה שרשין, ואית ביה קליפין, ואית ביה מוחא, ואית ביה ענפין, ואית ביה טרפין, ואית ביה פרחין, ואית ביה איבא, אוף הכי אינון מילין דילך, אית בהו פשטי דקראי, דרשה, רמז, דקא רמיז חכמתא, גמטריאות, רזין טמירין. רזין סתימין, אלין על אלין, כשר ופסול, טמא וטהור, אסור ומותר, חייב וזכאי, ומכאן ולהלאה מתפשטין ענפין לכל סטר, רחבה את מני ים, לית בך קץ ותכלית</p>
  <cite lang="he" dir="rtl">ספר בן איש חי - הקדמה</cite>
</blockquote>
"""

SECTIONS: dict[str, list[tuple[str, str, str]]] = {
    "en": [
        (
            "what-is-eitz-habina",
            "What is Eitz Habinah?",
            """Since the Bar-Ilan Responsa Project began in 1967, people around the world have created platforms and software to organize and study the vast body of Jewish texts, including the Torah.

Eitz Habinah began in late 2024 as a small contribution to this growing ecosystem of Torah technology. It is currently a proof-of-concept research project and is available for anyone to explore. At its core is a knowledge graph of entities and relationships found in Torah sources.

Entities such as people, places, and animals appear throughout these sources and are connected to one another. For example - a person may belong to a nation, interact with another person, visit a place, etc. Abraham is described as Sarah and Hagar's husband, Isaac and Ishmael's father, someone born in Ur Kasdim, and a visitor to Beersheba, among other relationships and places.""",
        ),
        (
            "how-is-eitz-habina-different",
            "How is Eitz Habinah different from other Torah search tools?",
            """### Compared with general-purpose AI assistants

- Eitz Habinah is built around an organized collection of Torah sources and a knowledge graph, with tools for exploring sources, people, places, and relationships.
- AI is used while preparing and enriching the data. Searches use the prepared indexes and database rather than asking an AI model to generate a new answer for each query.
- Results link to their source passages so readers can check the original text. Extracted entities and relationships can still be inaccurate, so the sources should be used to verify them.

### Compared with traditional keyword search

- A keyword search can miss spelling variants or passages that express an idea without using the exact search term. Eitz Habinah's semantic search is designed to find passages by meaning as well as wording.

### Compared with other semantic search tools

- Search results include concise summaries and passage categories to help readers assess relevance.
- The site also offers tools for exploring the knowledge graph and its relationships, beyond a list of search results.

**Current limitations**

- AI-generated data may be inaccurate. This personal research project used a relatively small language model, and the results still need further review and manual verification.
- The database is incomplete. Validation intentionally removes data that fails its checks; this can also remove correct information. The current source coverage is Tanakh and the Babylonian Talmud.
- The Streamlit interface is still evolving. I focused much of my effort on the backend, and the MCP interface provides another way to access the data.

**Pipeline**

1. Query the Sefaria API and package books into carefully labeled passages with keys and metadata.
2. Populate FAISS and BM25 indexes with source texts and source keys in Hebrew and English, enabling fast text-similarity search.
3. Pre-populate the database with separate records for ambiguous people who share a name. The current input files contain 167 Tanakh entries and 97 Bavli entries.
4. Iterate over the sources (phase 1): use PydanticAI to extract entities and relationships from each passage according to a precise data schema, and classify the passage.
5. Apply deterministic validation to the extracted entities and relationships, then populate the database with the entity-and-relationship graph. Every entity and relationship is linked to at least one source passage.
6. Iterate over the sources again (phase 2): use PydanticAI to enrich each entity with metadata in the context of its passage. This metadata helps users find information and is important for automated merge-candidate scoring.
7. Generate and review merge candidates:
   - **Person prefix matches:** find people whose names differ by a title prefix, such as “Rabbi Akiva” and “Akiva.”
   - **Same-name people:** group people with identical display names for review alongside their metadata and relationships.
   - **Closely spelled names:** find possible transliteration variants using broad spelling-normalization rules.

   Each candidate group receives an advisory confidence score. Pair scores start at 85% for title-prefix matches and 40% for same-name or close-spelling matches, then adjust for known person metadata (gender, non-Jewish/group flags, time period, Hebrew names, and book references) and graph context (shared or different parents and shared related entities). A group's score is its weakest pairwise score; missing values are not treated as contradictions, and groups with a role other than Tanna or Amora receive 0%. Source metadata is not compared. The scores help prioritize review—they do not establish identity or merge entities automatically. Decisions are recorded in the consolidated `confidence_person_*.md` files; the numbered chunk files contain entity details.
8. Run additional validation and diagnostic checks:
   - `validate_entity_relationships.py` is a read-only graph check for parent-gender mismatches, contradictory family links (including sibling/parent-child and reciprocal parent-child pairs), pairs classified as both father and mother, and reciprocal `studiedFrom` links.
   - `DBPrePopulateAmbiguosEntitys.test_validate_names` checks that pre-populated names are well-formed and appear with the exact spelling in the applicable source corpus.
   - `test_db_health.py` checks source counts, empty source fields, source-key formats, and the cleanliness of English source text.
   - `check_person_to_tribe_rels.py` is a read-only diagnostic that lists links to Israelite tribes and flags unexpected relationship types.

**Challenges**

- **Languages and spelling variants:** Tanakh and Talmud sources use Hebrew and English names with many spelling variations. Language models help identify candidates; verification scripts look for patterns such as *Hana/Hanna*, *Hanna/Hannah*, *Yochanan/Yohanan*, and *e/ei*. Candidates can then be compared by their graph connections—for example, whether both spellings are linked to Abraham and Beersheba. Predefined ambiguous entities also help prevent mistaken matches.
- **Language-model errors:** Deterministic validation catches many errors, but it can also reject useful data.

**Scope**

The database currently covers the Tanakh and the Babylonian Talmud. Expanding it to the Mishnah, Jerusalem Talmud, and Midrash is a future goal.""",
        ),
        (
            "about-feyga-menuha",
            "About Feyga Menuha",
            """Feyga Menuha bat Yehiel Gershon, of blessed memory, was a wonderful woman who loved studying Torah. She never had the opportunity to study in a yeshiva or midrasha, and sometimes lacked context when attending lectures.

We had the pleasure of studying Tanakh together for ten years. During that time, I saw how a simple chart could help make our studies clearer. That experience inspired me to spend more time preparing accessible source sheets. The clearer the charts became, the easier, more effective, and more enjoyable our learning was. Since then, nearly every lecture I give has a clear source sheet, often with historical context. I try to make sure no one in the audience is left behind. This is a gift I received from her, and I will always be grateful for it.

Although Feyga has passed away, I believe she would have been excited by this project and followed its progress with interest.

Our hope is that sharing this project will give people a little more context when they are not sure where to look—and, at the very least, inspire them to see how beautiful, deep, and interconnected the Torah is. May it be God's will, that any Torah study from this project be a merit for her soul.""",
        ),
        (
            "about-the-author",
            "About the author",
            """My name is David Berger, and I'm a software engineer in Israel. I'd love to hear your feedback and ideas.

EitzHabina@gmail.com""",
        ),
    ],
    "he": [
        (
            "what-is-eitz-habina",
            "מהו עץ הבינה?",
            """מאז שהחל פרויקט השו״ת של אוניברסיטת בר־אילן בשנת 1967, אנשים ברחבי העולם יוצרים פלטפורמות ותוכנות לארגון וללימוד של אוצר הטקסטים היהודי, ובכללו התורה.

עץ הבינה החל בסוף 2024 כתרומה קטנה למערכת המתפתחת של טכנולוגיות תורניות. כיום זהו פרויקט מחקר מסוג הוכחת היתכנות (POC), והוא זמין לכל מי שרוצה לחקור את המקורות. בליבו נמצא גרף ידע של ישויות וקשרים המופיעים במקורות התורה.

ישויות כגון אנשים, מקומות ובעלי חיים מופיעות במקורות וקשורות זו לזו. למשל, אדם עשוי להשתייך לעם, להיות בקשר עם אדם אחר או לבקר במקום. המקורות מתארים את אברהם כבעלה של שרה והגר, כאביהם של יצחק וישמעאל, כמי שנולד באור כשדים וכמי שביקר בבאר שבע, לצד קשרים ומקומות נוספים.""",
        ),
        (
            "how-is-eitz-habina-different",
            "במה עץ הבינה שונה מכלי חיפוש אחרים לתורה?",
            """### בהשוואה לכלי בינה מלאכותית כלליים

- עץ הבינה מבוסס על אוסף מקורות תורניים ועל גרף ידע, ומציע כלים לחקר המקורות, האנשים, המקומות והקשרים ביניהם.
- הבינה המלאכותית משמשת להכנת הנתונים ולהעשרתם. החיפושים מתבססים על אינדקסים ומסד נתונים מוכנים, ולא על בקשה ממודל לייצר תשובה חדשה בכל חיפוש.
- תוצאות החיפוש מקושרות לקטעי המקור, כך שאפשר לבדוק את הטקסט המקורי. ישויות וקשרים שחולצו מהמקורות עדיין עלולים להיות לא מדויקים, ולכן חשוב לאמת אותם מול המקור.

### בהשוואה לחיפוש לפי מילות מפתח

- חיפוש מילות מפתח עלול להחמיץ צורות כתיב שונות או קטעים שמבטאים רעיון בלי להשתמש במילת החיפוש המדויקת. החיפוש הסמנטי של עץ הבינה נועד לאתר קטעים לפי משמעות, ולא רק לפי הניסוח.

### בהשוואה לכלי חיפוש סמנטי אחרים

- תוצאות החיפוש כוללות תקצירים תמציתיים וקטגוריות של קטעים, המסייעים להעריך את מידת הרלוונטיות.
- האתר מציע גם כלים לחקר גרף הידע והקשרים שבו, מעבר לרשימת תוצאות חיפוש.

**מגבלות כיום**

- נתונים שנוצרו באמצעות בינה מלאכותית עלולים להיות לא מדויקים. בפרויקט המחקר האישי הזה נעשה שימוש במודל שפה קטן יחסית, ועדיין נדרשות בדיקה ואימות ידניים נוספים.
- המאגר אינו שלם. תהליכי האימות מסירים בכוונה נתונים שאינם עומדים בבדיקות, אך לפעמים עלולים להסיר גם מידע נכון. המקורות הקיימים כיום הם התנ״ך והתלמוד הבבלי.
- ממשק Streamlit עדיין נמצא בפיתוח. התמקדתי רבות בעבודה על צד השרת, וממשק MCP מציע דרך נוספת לגשת לנתונים.

**צינור העיבוד**

1. פנייה ל־API של ספריא ואריזת הספרים בקטעים המסומנים בקפידה, עם מפתחות ומטא־נתונים.
2. אכלוס אינדקסי FAISS ו־BM25 בטקסטים של המקורות ובמפתחות שלהם בעברית ובאנגלית, כדי לאפשר חיפוש דמיון טקסטואלי מהיר.
3. אכלוס מוקדם של מסד הנתונים ברשומות נפרדות של אנשים עמומים בעלי שם זהה. קובצי הקלט הנוכחיים כוללים 167 דמויות מן התנ״ך ו־97 דמויות מן התלמוד הבבלי.
4. מעבר ראשון על המקורות: שימוש ב־PydanticAI לחילוץ ישויות וקשרים מכל קטע לפי סכמת נתונים מדויקת, וכן לסיווג הקטע.
5. אימות דטרמיניסטי של הישויות והקשרים שחולצו, ולאחר מכן אכלוס מסד הנתונים בגרף של ישויות וקשרים. כל ישות וכל קשר מקושרים לפחות לקטע מקור אחד.
6. מעבר שני על המקורות: שימוש ב־PydanticAI להעשרת כל ישות במטא־נתונים בהקשר של הקטע שבו היא מופיעה. המטא־נתונים מסייעים למשתמשים למצוא מידע וחשובים לניקוד האוטומטי של מועמדים למיזוג.
7. יצירת מועמדים למיזוג ובדיקתם:
   - **התאמות לפי תחילית בשם אדם:** איתור אנשים ששמותיהם נבדלים בתחילית תואר, כגון “Rabbi Akiva” ו־“Akiva”.
   - **אנשים בעלי שם זהה:** קיבוץ אנשים בעלי שם תצוגה זהה לצורך בדיקה לצד המטא־נתונים והקשרים שלהם.
   - **שמות בעלי איות דומה:** איתור צורות תעתיק אפשריות באמצעות כללים רחבים לנרמול איות.

   לכל קבוצת מועמדים ניתן ציון ביטחון מייעץ. ציון הזוגות מתחיל ב־85% בהתאמות לפי תחילית תואר וב־40% בהתאמות של שם זהה או איות דומה, ומתעדכן לפי מטא־נתונים ידועים של האדם (מגדר, סימון כלא־יהודי או כקבוצה, תקופה, שם בעברית והפניות לספרים) וההקשר בגרף (הורים משותפים או שונים וישויות קשורות משותפות). ציון הקבוצה הוא הנמוך ביותר מבין ציוני הזוגות; מידע חסר אינו נחשב לסתירה, וקבוצה שיש בה תפקיד שאינו תנא או אמורא מקבלת ציון 0%. מטא־נתונים של המקור אינם נכללים בהשוואה. הציונים נועדו לסייע בתעדוף הבדיקה — הם אינם קובעים זהות ואינם ממזגים ישויות באופן אוטומטי. ההחלטות נשמרות בקובצי `confidence_person_*.md` המאוחדים; קובצי החלקים הממוספרים מכילים את פרטי הישויות.
8. הרצת בדיקות אימות ואבחון נוספות:
   - `validate_entity_relationships.py` בודק את גרף הקשרים לקריאות שגויות של מגדר בקשרי הורות, קשרי משפחה סותרים (לרבות קשר בין אחים להורה־ילד או קשרי הורה־ילד הדדיים), זוג שסווג גם כאב וגם כאם, וקשרי `studiedFrom` הדדיים. הבדיקה היא לקריאה בלבד.
   - `DBPrePopulateAmbiguosEntitys.test_validate_names` בודק ששמות שהוגדרו מראש תקינים ומופיעים באיות המדויק במאגר המקורות המתאים.
   - `test_db_health.py` בודק את מספר המקורות, שדות מקור ריקים, תבנית המפתחות ואת תקינות הטקסט האנגלי במקורות.
   - `check_person_to_tribe_rels.py` הוא כלי אבחון לקריאה בלבד, המציג קשרים לשבטי ישראל ומסמן סוגי קשרים לא צפויים.

**אתגרים**

- **שפות וצורות כתיב:** במקורות תנ״ך ותלמוד יש שמות בעברית ובאנגלית וצורות כתיב רבות. מודלי שפה מסייעים בזיהוי מועמדים; סקריפטים לאימות מחפשים דפוסים כגון *Hana/Hanna*, *Hanna/Hannah*, *Yochanan/Yohanan* ו־*e/ei*. לאחר מכן אפשר להשוות בין הקשרים של כל מועמד בגרף — למשל, לבדוק אם שתי צורות כתיב מקושרות לאברהם ולבאר שבע. ישויות עמומות שהוגדרו מראש מסייעות גם הן למנוע מיזוגים שגויים.
- **שגיאות של מודלי שפה:** אימות דטרמיניסטי מזהה שגיאות רבות, אך עלול גם לדחות מידע מועיל.

**היקף**

המאגר כולל כיום את התנ״ך ואת התלמוד הבבלי. הרחבתו למשנה, לתלמוד הירושלמי ולמדרש היא יעד לעתיד.""",
        ),
        (
            "about-feyga-menuha",
            "על פייגא מנוחה",
            """פייגא מנוחה בת יחיאל גרשון ע״ה הייתה אישה נפלאה שאהבה ללמוד תורה. היא לא זכתה ללמוד בישיבה או במדרשה, ולעיתים היה חסר לה ההקשר כששמעה שיעורים.

זכינו ללמוד תנ״ך יחד במשך עשר שנים. באותה תקופה ראיתי כיצד תרשים פשוט יכול להבהיר את הנושאים שלמדנו. החוויה הזאת נתנה לי השראה להשקיע יותר בהכנת דפי מקורות נגישים. ככל שהתרשימים נעשו ברורים יותר, הלימוד שלנו נעשה קל, יעיל ומהנה יותר. מאז, כמעט כל שיעור שאני מעביר מלווה בדף מקורות ברור, לעיתים קרובות עם הקשר היסטורי. אני משתדל לוודא שאיש בקהל לא יישאר מאחור. זו מתנה שקיבלתי ממנה, ועליה אהיה אסיר תודה תמיד.

אף שפייגא מנוחה נפטרה, אני מאמין שהפרויקט הזה היה משמח אותה ושהייתה עוקבת אחר התקדמותו בעניין.

תקוותנו היא ששיתוף הפרויקט יעניק לאנשים מעט יותר הקשר כשהם אינם בטוחים היכן לחפש — ולכל הפחות יעורר בהם השראה לנוכח יופייה, עומקה ושזירתה של התורה. יהי רצון שכל לימוד תורה מתוך הפרויקט יהיה לזכות נשמתה.""",
        ),
        (
            "about-the-author",
            "על המחבר",
            """שמי דוד ברגר, ואני מהנדס תוכנה בישראל. אשמח לשמוע משוב ורעיונות!

EitzHabina@gmail.com""",
        ),
    ],
}
