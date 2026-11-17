# bs"d - lehagdil torah velahadir

from __future__ import annotations

TABLE_OF_CONTENTS_TITLE = {
    "en": "Table of contents",
    "he": "תוכן העניינים",
}

OPENING_QUOTE = """
<blockquote class="about-opening-quote">
  <p lang="he" dir="rtl">ישתבח הבורא ויתפאר היוצר, אשר הנחילנו חמדה גנוזה ויקרה, חכמה מפוארה, ליהודים היתה אורה (אסתר ח, טז), אורה זו תורה (מגילה טז:), לעבדה ולשמרה:...<br>
  אורייתא אורייתא, כמה חביבין אינון מלין דילך, מה אילנא אית ביה שרשין, ואית ביה קליפין, ואית ביה מוחא, ואית ביה ענפין, ואית ביה טרפין, ואית ביה פרחין, ואית ביה איבא, אוף הכי אינון מילין דילך, אית בהו פשטי דקראי, דרשה, רמז, דקא רמיז חכמתא, גמטריאות, רזין טמירין. רזין סתימין, אלין על אלין, כשר ופסול, טמא וטהור, אסור ומותר, חייב וזכאי, ומכאן ולהלאה מתפשטין ענפין לכל סטר, רחבה את מני ים, לית בך קץ ותכלית</p>
  <p lang="en" dir="ltr">May the Creator be praised and the Former exalted, who bestowed upon us a cherished and precious hidden treasure, glorious wisdom; “the Jews had light” (Esther 8:16)—“light refers to Torah” (Megillah 16b)—“to work it and to guard it”...<br>
  O Torah, O Torah, how beloved are your words! Just as a tree has roots, and peels, and a core, and branches, and leaves, and blossoms, and fruit, so too are your words: they contain the plain meaning of Scripture, exposition, hints in which wisdom is intimated, gematrias, hidden mysteries, concealed secrets, one above another; kosher and unfit, impure and pure, forbidden and permitted, liable and acquitted. From here onward, branches spread out in every direction. You are wider than the sea; you have no end or limit.</p>
  <cite lang="he" dir="rtl">ספר בן איש חי - הקדמה</cite>
  <cite lang="en" dir="ltr">Sefer Ben Ish Chai — Introduction</cite>
</blockquote>
"""

SECTIONS: dict[str, list[tuple[str, str, str]]] = {
    "en": [
        (
            "what-is-eitz-habina",
            "What is Eitz Habina?",
            """Since the Bar Ilan Responsa project (1967), Jews around the world have been creating different platforms and software systems to organize and analyze the most important Corpus to the Jewish People - the Torah.

Eitz Habina, born in late 2024, is another small part of the worldwide eco systems of Torah technologies. Currently a POC research project, but in the meantime fully usable for anyone who wants. It is a Knowledge Graph of Entities and Relationships throughout the Torah.

Entities (like people, places, animals) appear throughout the Torah, and are related to each other (a person is part of a nation, a person visits a place). For example - Abraham is married to Sarah and Hagar, father to Itzhak and Ishmael, born in Our Kasdim, visited Beer Sheva, etc.""",
        ),
        (
            "how-is-eitz-habina-different",
            "How is Eitz Habina different than all other Torah Search Engines?",
            """Compared to Gemini, Claude, or an LLM agent:

- The major search engines will always bring the most-searched and most commonly cited sources. But Eitz Habina allows the user to find sources in books less often cited - like Talmud yerushalmi, midrash, etc.
- Eitz Habina can return a large volume of information, for free:
  - ai was called during population, but once our data is populated, a complex query does not use any heavy resources
- Eitz Habina will never hallucinate sources: although some entities and relationships might be in accurate, the user can immediately view the original, unedited source to verify any data.

Compared to Bar Ilan Responsa search:

- Bar Ilan Responsa search is extremely accurate, but only search searching an exact word match. The search ‘דוד’ will not find ‘דויד’, and many other examples. Eitz Habina however brings sources based on natural language meaning.

Compared to Dicta’s semantic search of Tanach/Talmud:

- Dicta search presents a list of sources, and the user must understand each source to understand relevance. Eitz Habina presents the sources collapsed, with concise summary of each source is easy language, and category of passage type
- Eitz Habina runs on more sources
- Eitz Habina includes many other tools that a regular semantic search does not have.

Eitz Habina’a weaknesses:

- AI inaccuracy: because this was a personal research project, the pipeline was run on a relatively ‘weak’ LLM. Even with the strongest LLM, this project would still require heavier review and manual verification. Nonetheless, I think that (1) there is more good data than bad, and (2) the many different pages allows the user to find at least one tool he/she will like
- Missing information: because of the many validation scripts, much of the generated data was intentionally cleaned. I am sure that this included false negatives. But that is part of the price of using Ai and wanted valid results.
- Streamlit UI: I chose to invest my resources in the backend complexity, and so naturally the UI has a long way to go. But now with the MCP, I wonder if that will make up for the weak UI

**Pipeline:**
1. Query Sefaria's API, package books into carefully labeled passages with keys and metadata
2. Populate FAISS and BM25 indexes with sources and source keys (both hebrew and english), enabling instant text similarity search.
2. Prepoluate DB with 300+ hardcoded, predefined ambiguous entities (different entities sharing same name)
2. Iterate over sources (1/2): extract entities and relationships from passage with LLM (pydantic AI) with precise data scheme. Collect category of passage.
3. After heavy deterministic validation of entity and relationships - populate DB with graph of entities, relationships. Each entity and relationship is linked to at least one source passage.
4. Iterate over sources (2/2): for each passage, ensure every entity is enriched with metadata with LLM (pydantic AI), in context of that passage. This metadata is very helpful for the user to find data, and is critical for automatic merging scripts.

**Challenges:**

1. Multi language, and multiple English and Hebrew spellings: this is the challenge of any Tanach/Talmud pipeline.
   A. Use of LLM significantly improves results.
   B. Verification scripts (‘for each entity, find if other entities exists with 2 consonants instead of one [Hana vs Hanna], or ‘h’ following ‘a’ [Hanna vs Hannah], ‘ch’ instead of ‘h’ and vice versa [yochanan vs yohanan[, ‘e’ and ‘ei’, etc. ). After finding categories, identify if same entity by comparing relative closeness to other nodes in the graph (both itzchak and itzhak have parent called ‘abraham’, visited place ‘beer sheva’)
   C. The prepopulation script prevented many issues immediately
2. Llm hallucinations:
   1. Careful determinist validation cleared many fault data from LLM. however, this came at the cost of sometimes clearing valuable data

Scope:
Currently runs over Tanach and Babylonian Talmud. Hoping to run on Mishna, Jerusalem Talmud, and Midrash""",
        ),
        (
            "about-feyga-menuha",
            "About Feyga Menuha",
            """Feyga Menuha bat yehiel gershon a”h was a wonderful woman who loved to study Torah. She never had the chance to study in a yeshiva or midrasha, and so she often lacked context when attending lectures.

We had the pleasure of studying Tanach together for 10 years. In those years, I saw how helpful a simple chart was to give context to what we were learning. From that experience of our study together, I began to invest more and more time in preparing clear source sheets. The clearer I made the charts, the easier, more effective and of course more enjoyable our learning was. Since our study, almost every lecture that I give comes with a clear source sheets (often with historical context), and I try hard to make sure that no one in the audience gets left behind. It is a gift from here for which I will be eternally grateful.

Although Feyga Menuch has already moved on to the Next World, I am sure that she was excited by this project and following my progress carefully.

It is our dream that by sharing this project, we can provide a little more context to people who don't always know where to look. And at the very least - to give inspiration for how beautiful, deep, and interwoven our Torah is.""",
        ),
        (
            "about-the-author",
            "About the author",
            """My name is David Berger, and I'm a software engineer in Israel. Would love to hear feedback or ideas!

EitzHabina@gmail.com""",
        ),
    ],
    "he": [
        (
            "what-is-eitz-habina",
            "מהו עץ הבינה?",
            """מאז פרויקט השו״ת של אוניברסיטת בר־אילן (1967), יהודים ברחבי העולם יוצרים פלטפורמות ומערכות תוכנה שונות כדי לארגן ולנתח את הקורפוס החשוב ביותר לעם היהודי — התורה.

עץ הבינה, שנולד בסוף 2024, הוא חלק קטן נוסף ממערכת הטכנולוגיות התורניות המתפתחת ברחבי העולם. זהו כיום פרויקט מחקר מסוג POC, אך בינתיים הוא זמין לשימוש מלא לכל מי שמעוניין. עץ הבינה הוא גרף ידע של ישויות וקשרים ברחבי התורה.

ישויות (כגון אנשים, מקומות ובעלי חיים) מופיעות ברחבי התורה וקשורות זו לזו (אדם שייך לעם, אדם מבקר במקום). לדוגמה — אברהם נשוי לשרה ולהגר, אב ליצחק ולישמעאל, נולד באור כשדים, ביקר בבאר שבע ועוד.""",
        ),
        (
            "how-is-eitz-habina-different",
            "במה עץ הבינה שונה מכל מנועי החיפוש האחרים לתורה?",
            """בהשוואה ל־Gemini, ל־Claude או לסוכן המבוסס על מודל שפה גדול:

- מנועי החיפוש הגדולים יציגו תמיד את המקורות שמחפשים ומצטטים בתדירות הגבוהה ביותר. עץ הבינה מאפשר למצוא מקורות גם בספרים המצוטטים פחות — כגון תלמוד ירושלמי, מדרש ועוד.
- עץ הבינה יכול להחזיר כמות גדולה של מידע בחינם:
  - נעשה שימוש בבינה מלאכותית בעת אכלוס המאגר, אך לאחר שהנתונים נאספו, שאילתה מורכבת אינה צורכת משאבים כבדים.
- עץ הבינה לעולם לא ימציא מקורות: אף שחלק מהישויות והקשרים עלולים להיות לא מדויקים, המשתמש יכול לפתוח מיד את המקור המקורי והלא ערוך כדי לאמת את הנתונים.

בהשוואה לחיפוש בשו״ת בר־אילן:

- החיפוש בשו״ת בר־אילן מדויק מאוד, אך מחפש התאמה מדויקת של מילה בלבד. חיפוש המילה ׳דוד׳ לא ימצא את ׳דויד׳, ויש דוגמאות רבות נוספות. לעומת זאת, עץ הבינה מציג מקורות לפי משמעות בשפה טבעית.

בהשוואה לחיפוש הסמנטי של דיקטא בתנ״ך ובתלמוד:

- חיפוש דיקטא מציג רשימת מקורות, והמשתמש צריך להבין כל מקור כדי להבין את מידת הרלוונטיות שלו. עץ הבינה מציג את המקורות בתצוגה מצומצמת, עם תקציר תמציתי של כל מקור בשפה פשוטה ועם קטגוריה של סוג הקטע.
- עץ הבינה פועל על פני מקורות רבים יותר.
- עץ הבינה כולל כלים רבים נוספים שאינם זמינים בחיפוש סמנטי רגיל.

החסרונות של עץ הבינה:

- אי־דיוקים של בינה מלאכותית: מכיוון שזהו פרויקט מחקר אישי, צינור העיבוד הורץ באמצעות מודל שפה גדול חלש יחסית. גם עם המודל החזק ביותר, הפרויקט עדיין ידרוש בדיקה מעמיקה יותר ואימות ידני. למרות זאת, אני חושב ש־(1) יש יותר נתונים טובים מנתונים שגויים, ו־(2) הדפים הרבים מאפשרים למשתמש למצוא לפחות כלי אחד שיאהב.
- מידע חסר: בגלל סקריפטים רבים לאימות הנתונים, חלק גדול מהנתונים שנוצרו נוקה בכוונה. אני בטוח שהדבר כלל גם מקרים חיוביים שלא זוהו. זהו חלק מהמחיר של שימוש בבינה מלאכותית ושל הרצון לקבל תוצאות תקינות.
- ממשק Streamlit: בחרתי להשקיע את המשאבים שלי במורכבות של צד השרת, ולכן באופן טבעי לממשק המשתמש יש עוד דרך ארוכה. אבל עכשיו, עם MCP, אני תוהה אם הוא יפצה על הממשק החלש.

**צינור העיבוד:**
1. פנייה ל־API של ספריא ואריזת הספרים בקטעים המסומנים בקפידה, עם מפתחות ומטא־נתונים.
2. אכלוס האינדקסים FAISS ו־BM25 במקורות ובמפתחות המקורות (בעברית ובאנגלית), כדי לאפשר חיפוש דמיון טקסטואלי מיידי.
2. אכלוס מוקדם של מסד הנתונים ביותר מ־300 ישויות עמומות שהוגדרו מראש (ישויות שונות בעלות אותו שם).
2. מעבר על המקורות (1 מתוך 2): חילוץ ישויות וקשרים מהקטע באמצעות מודל שפה גדול (pydantic AI), לפי סכמת נתונים מדויקת. איסוף קטגוריית הקטע.
3. לאחר אימות דטרמיניסטי נרחב של הישויות והקשרים — אכלוס מסד הנתונים בגרף של ישויות וקשרים. כל ישות וקשר מקושרים לפחות לקטע מקור אחד.
4. מעבר על המקורות (2 מתוך 2): בכל קטע מוודאים שכל ישות מועשרת במטא־נתונים באמצעות מודל שפה גדול (pydantic AI), ובהקשר של אותו קטע. המטא־נתונים האלה עוזרים מאוד למשתמש למצוא מידע, וחיוניים לסקריפטים האוטומטיים למיזוג ישויות.

**אתגרים:**

1. ריבוי שפות וריבוי צורות כתיב בעברית ובאנגלית: זהו אתגר של כל צינור עיבוד של התנ״ך והתלמוד.
   א. השימוש במודל שפה גדול משפר מאוד את התוצאות.
   ב. סקריפטים לאימות בודקים, למשל, אם קיימות ישויות אחרות עם עיצור כפול במקום עיצור יחיד [Hana לעומת Hanna], עם ׳h׳ אחרי ׳a׳ [Hanna לעומת Hannah], עם ׳ch׳ במקום ׳h׳ ולהפך [yochanan לעומת yohanan], עם ׳e׳ ו־׳ei׳ ועוד. לאחר זיהוי קבוצות, בודקים אם מדובר באותה ישות באמצעות השוואת הקרבה היחסית לישויות אחרות בגרף (גם ל־itzchak וגם ל־itzhak יש הורה בשם ׳abraham׳, ומקום ביקור בשם ׳beer sheva׳).
   ג. סקריפט האכלוס המוקדם מנע בעיות רבות מראש.
2. הזיות של מודל השפה:
   1. אימות דטרמיניסטי קפדני הסיר נתונים שגויים רבים שהגיעו ממודל השפה. עם זאת, לפעמים הדבר בא על חשבון הסרה של נתונים מועילים.

היקף:
כיום המאגר כולל את התנ״ך ואת התלמוד הבבלי. התקווה היא להרחיבו למשנה, לתלמוד הירושלמי ולמדרש.""",
        ),
        (
            "about-feyga-menuha",
            "על פייגא מנוחה",
            """פייגא מנוחה בת יחיאל גרשון ע״ה הייתה אישה נפלאה שאהבה ללמוד תורה. היא לא זכתה ללמוד בישיבה או במדרשה, ולכן לעיתים קרובות היה חסר לה ההקשר כששמעה שיעורים.

זכינו ללמוד תנ״ך יחד במשך עשר שנים. בשנים האלה ראיתי כמה תרשים פשוט יכול לעזור להבין את ההקשר של מה שלמדנו. בעקבות הלימוד המשותף התחלתי להשקיע עוד ועוד זמן בהכנת דפי מקורות ברורים. ככל שהתרשימים היו ברורים יותר, הלימוד שלנו נעשה קל יותר, יעיל יותר וכמובן מהנה יותר. מאז הלימוד המשותף, כמעט כל שיעור שאני מעביר מלווה בדף מקורות ברור (לעיתים קרובות עם הקשר היסטורי), ואני משתדל מאוד לוודא שאיש בקהל לא יישאר מאחור. זהו מתנה שקיבלתי ממנה, ועליה אהיה אסיר תודה לעד.

אף שפייגא מנוחה כבר עברה לעולם הבא, אני בטוח שהיא התרגשה מהפרויקט הזה ועקבה מקרוב אחר התקדמותי.

החלום שלנו הוא שבאמצעות שיתוף הפרויקט נוכל לתת מעט יותר הקשר לאנשים שלא תמיד יודעים היכן לחפש. ולכל הפחות — לעורר השראה לנוכח יופייה, עומקה ושזירתה של התורה.""",
        ),
        (
            "about-the-author",
            "על המחבר",
            """שמי דוד ברגר, ואני מהנדס תוכנה בישראל. אשמח לשמוע משוב או רעיונות!

EitzHabina@gmail.com""",
        ),
    ],
}
