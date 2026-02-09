from dataclasses import dataclass

@dataclass(frozen=True)
class BookName:
    en_display_name: str
    heb_display_name: str
    database_name: str

class BookRegistry:
    """Base class to provide shared lookup logic."""
    @classmethod
    def all(cls) -> list[BookName]:
        return [v for v in cls.__dict__.values() if isinstance(v, BookName)]

    @classmethod
    def get_by_db_name(cls, db_name: str) -> BookName | None:
        return next((b for b in cls.all() if b.database_name == db_name), None)

class TanachBooks(BookRegistry):
    # Torah
    GENESIS = BookName("Bereishit", "בראשית", "Genesis")
    EXODUS = BookName("Shemot", "שמות", "Exodus")
    LEVITICUS = BookName("Vayikra", "ויקרא", "Leviticus")
    NUMBERS = BookName("Bamidbar", "במדבר", "Numbers")
    DEUTERONOMY = BookName("Devarim", "דברים", "Deuteronomy")

    # Nevi'im
    JOSHUA = BookName("Yehoshua", "יהושע", "Joshua")
    JUDGES = BookName("Shoftim", "שופטים", "Judges")
    SAMUEL_I = BookName("Shmuel I", "שמואל א", "I Samuel")
    SAMUEL_II = BookName("Shmuel II", "שמואל ב", "II Samuel")
    KINGS_I = BookName("Melakhim I", "מלכים א", "I Kings")
    KINGS_II = BookName("Melakhim II", "מלכים ב", "II Kings")
    ISAIAH = BookName("Yeshayahu", "ישעיהו", "Isaiah")
    JEREMIAH = BookName("Yirmiyahu", "ירמיהו", "Jeremiah")
    EZEKIEL = BookName("Yehezkel", "יחזקאל", "Ezekiel")
    HOSEA = BookName("Hoshea", "הושע", "Hosea")
    JOEL = BookName("Yoel", "יואל", "Joel")
    AMOS = BookName("Amos", "עמוס", "Amos")
    OBADIAH = BookName("Ovadyah", "עובדיה", "Obadiah")
    JONAH = BookName("Yonah", "יונה", "Jonah")
    MICAH = BookName("Mikah", "מיכה", "Micah")
    NAHUM = BookName("Nachum", "נחום", "Nahum")
    HABAKKUK = BookName("Chavakuk", "חבקוק", "Habakkuk")
    ZEPHANIAH = BookName("Tzefanyah", "צפניה", "Zephaniah")
    HAGGAI = BookName("Chaggai", "חגי", "Haggai")
    ZECHARIAH = BookName("Zekharyah", "זכריה", "Zechariah")
    MALACHI = BookName("Malakhi", "מלאכי", "Malachi")

    # Ketuvim
    PSALMS = BookName("Tehillim", "תהילים", "Psalms")
    PROVERBS = BookName("Mishlei", "משלי", "Proverbs")
    JOB = BookName("Iyov", "איוב", "Job")
    SONG_OF_SONGS = BookName("Shir HaShirim", "שיר השירים", "Song of Songs")
    RUTH = BookName("Rut", "רות", "Ruth")
    LAMENTATIONS = BookName("Eikhah", "איכה", "Lamentations")
    ECCLESIASTES = BookName("Kohelet", "קהלת", "Ecclesiastes")
    ESTHER = BookName("Esther", "אסתר", "Esther")
    DANIEL = BookName("Daniel", "דניאל", "Daniel")
    EZRA = BookName("Ezra", "עזרא", "Ezra")
    NEHEMIAH = BookName("Nehemiah", "נחמיה", "Nehemiah")
    CHRONICLES_I = BookName("Divrei HaYamim I", "דברי הימים א", "I Chronicles")
    CHRONICLES_II = BookName("Divrei HaYamim II", "דברי הימים ב", "II Chronicles")

class TalmudObjs(BookRegistry):
    # Zeraim
    BERAKHOT = BookName("Berakhot", "ברכות", "Berakhot")

    # Moed
    SHABBAT = BookName("Shabbat", "שבת", "Shabbat")
    ERUVIN = BookName("Eruvin", "עירובין", "Eruvin")
    PESACHIM = BookName("Pesachim", "פסחים", "Pesachim")
    # SHEKALIM = BookName("Shekalim", "שקלים", "Shekalim") missing?
    YOMA = BookName("Yoma", "יומא", "Yoma")
    SUKKAH = BookName("Sukkah", "סוכה", "Sukkah")
    BEITZAH = BookName("Beitzah", "ביצה", "Beitzah")
    ROSH_HASHANAH = BookName("Rosh Hashanah", "ראש השנה", "Rosh Hashanah")
    TAANIT = BookName("Taanit", "תענית", "Taanit")
    MEGILLAH = BookName("Megillah", "מגילה", "Megillah")
    MOED_KATAN = BookName("Moed Katan", "מועד קטן", "Moed Katan")
    CHAGIGAH = BookName("Chagigah", "חגיגה", "Chagigah")

    # Nashim
    YEVAMOT = BookName("Yevamot", "יבמות", "Yevamot")
    KETUBOT = BookName("Ketubot", "כתובות", "Ketubot")
    NEDARIM = BookName("Nedarim", "נדרים", "Nedarim")
    NAZIR = BookName("Nazir", "נזיר", "Nazir")
    SOTAH = BookName("Sotah", "סוטה", "Sotah")
    GITTIN = BookName("Gittin", "גיטין", "Gittin")
    KIDDUSHIN = BookName("Kiddushin", "קידושין", "Kiddushin")

    # Nezikin
    BAVA_KAMMA = BookName("Bava Kamma", "בבא קמא", "Bava Kamma")
    BAVA_METZIA = BookName("Bava Metzia", "בבא מציעא", "Bava Metzia")
    BAVA_BATRA = BookName("Bava Batra", "בבא בתרא", "Bava Batra")
    SANHEDRIN = BookName("Sanhedrin", "סנהדרין", "Sanhedrin")
    MAKKOT = BookName("Makkot", "מכות", "Makkot")
    SHEVUOT = BookName("Shevuot", "שבועות", "Shevuot")
    AVODAH_ZARAH = BookName("Avodah Zarah", "עבודה זרה", "Avodah Zarah")
    HORAYOT = BookName("Horayot", "הוריות", "Horayot")

    # Kodashim
    ZEVACHIM = BookName("Zevachim", "זבחים", "Zevachim")
    MENACHOT = BookName("Menachot", "מנחות", "Menachot")
    CHULLIN = BookName("Chullin", "חולין", "Chullin")
    BEKHOROT = BookName("Bekhorot", "בכורות", "Bekhorot")
    ARAKHIN = BookName("Arakhin", "ערכין", "Arakhin")
    TEMURAH = BookName("Temurah", "תמורה", "Temurah")
    KERITOT = BookName("Keritot", "כריתות", "Keritot")
    MEILAH = BookName("Meilah", "מעילה", "Meilah")
    TAMID = BookName("Tamid", "תמיד", "Tamid")
    # KINNIM = BookName("Kinnim", "קנים", "Kinnim") missing?
    # MIDDOT = BookName("Middot", "מידות", "Middot") missing?

    # Tahorot
    NIDDAH = BookName("Niddah", "נדה", "Niddah")