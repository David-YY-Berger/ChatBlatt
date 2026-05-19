# bs"d - lehagdil torah velahadir
from dataclasses import dataclass

from backend.models_db.Enums import SourceType, BookCategoryName


@dataclass(frozen=True, order=True)
class Book:
    """
    Represents a book/tractate in the database.
    The `order` field determines canonical ordering within each source type.
    Comparison operators use `order` first (due to field ordering in the dataclass).
    """
    order: int
    source_type: SourceType
    en_display_name: str
    heb_display_name: str
    database_name: str
    category: BookCategoryName = BookCategoryName.Torah  # default overridden per instance

class BookRegistry:
    @classmethod
    def all(cls) -> list['Book']:
        return [v for v in cls.__dict__.values() if isinstance(v, Book)]

    @classmethod
    def by_source(cls, source: SourceType) -> list['Book']:
        return sorted([b for b in cls.all() if b.source_type == source])

    @classmethod
    def get_by_db_name(cls, db_name: str) -> 'Book | None':
        return next((b for b in cls.all() if b.database_name == db_name), None)

    @classmethod
    def sorted_all(cls) -> list['Book']:
        """Returns all books sorted by source type, then by canonical order."""
        return sorted(cls.all(), key=lambda b: (b.source_type.value, b.order))

class Books(BookRegistry):
    # ── Torah ──
    GENESIS = Book(1, SourceType.TN, "Bereishit", "בראשית", "Genesis", BookCategoryName.Torah)
    EXODUS = Book(2, SourceType.TN, "Shemot", "שמות", "Exodus", BookCategoryName.Torah)
    LEVITICUS = Book(3, SourceType.TN, "Vayikra", "ויקרא", "Leviticus", BookCategoryName.Torah)
    NUMBERS = Book(4, SourceType.TN, "Bamidbar", "במדבר", "Numbers", BookCategoryName.Torah)
    DEUTERONOMY = Book(5, SourceType.TN, "Devarim", "דברים", "Deuteronomy", BookCategoryName.Torah)

    # ── Nevi'im ──
    JOSHUA = Book(6, SourceType.TN, "Yehoshua", "יהושע", "Joshua", BookCategoryName.Neviim)
    JUDGES = Book(7, SourceType.TN, "Shoftim", "שופטים", "Judges", BookCategoryName.Neviim)
    SAMUEL_I = Book(8, SourceType.TN, "Shmuel I", "שמואל א", "I Samuel", BookCategoryName.Neviim)
    SAMUEL_II = Book(9, SourceType.TN, "Shmuel II", "שמואל ב", "II Samuel", BookCategoryName.Neviim)
    KINGS_I = Book(10, SourceType.TN, "Melakhim I", "מלכים א", "I Kings", BookCategoryName.Neviim)
    KINGS_II = Book(11, SourceType.TN, "Melakhim II", "מלכים ב", "II Kings", BookCategoryName.Neviim)
    ISAIAH = Book(12, SourceType.TN, "Yeshayahu", "ישעיהו", "Isaiah", BookCategoryName.Neviim)
    JEREMIAH = Book(13, SourceType.TN, "Yirmiyahu", "ירמיהו", "Jeremiah", BookCategoryName.Neviim)
    EZEKIEL = Book(14, SourceType.TN, "Yehezkel", "יחזקאל", "Ezekiel", BookCategoryName.Neviim)
    HOSEA = Book(15, SourceType.TN, "Hoshea", "הושע", "Hosea", BookCategoryName.Neviim)
    JOEL = Book(16, SourceType.TN, "Yoel", "יואל", "Joel", BookCategoryName.Neviim)
    AMOS = Book(17, SourceType.TN, "Amos", "עמוס", "Amos", BookCategoryName.Neviim)
    OBADIAH = Book(18, SourceType.TN, "Ovadyah", "עובדיה", "Obadiah", BookCategoryName.Neviim)
    JONAH = Book(19, SourceType.TN, "Yonah", "יונה", "Jonah", BookCategoryName.Neviim)
    MICAH = Book(20, SourceType.TN, "Mikah", "מיכה", "Micah", BookCategoryName.Neviim)
    NAHUM = Book(21, SourceType.TN, "Nachum", "נחום", "Nahum", BookCategoryName.Neviim)
    HABAKKUK = Book(22, SourceType.TN, "Chavakuk", "חבקוק", "Habakkuk", BookCategoryName.Neviim)
    ZEPHANIAH = Book(23, SourceType.TN, "Tzefanyah", "צפניה", "Zephaniah", BookCategoryName.Neviim)
    HAGGAI = Book(24, SourceType.TN, "Chaggai", "חגי", "Haggai", BookCategoryName.Neviim)
    ZECHARIAH = Book(25, SourceType.TN, "Zekharyah", "זכריה", "Zechariah", BookCategoryName.Neviim)
    MALACHI = Book(26, SourceType.TN, "Malakhi", "מלאכי", "Malachi", BookCategoryName.Neviim)

    # ── Ketuvim ──
    PSALMS = Book(27, SourceType.TN, "Tehillim", "תהילים", "Psalms", BookCategoryName.Ketuvim)
    PROVERBS = Book(28, SourceType.TN, "Mishlei", "משלי", "Proverbs", BookCategoryName.Ketuvim)
    JOB = Book(29, SourceType.TN, "Iyov", "איוב", "Job", BookCategoryName.Ketuvim)
    SONG_OF_SONGS = Book(30, SourceType.TN, "Shir HaShirim", "שיר השירים", "Song of Songs", BookCategoryName.Ketuvim)
    RUTH = Book(31, SourceType.TN, "Rut", "רות", "Ruth", BookCategoryName.Ketuvim)
    LAMENTATIONS = Book(32, SourceType.TN, "Eikhah", "איכה", "Lamentations", BookCategoryName.Ketuvim)
    ECCLESIASTES = Book(33, SourceType.TN, "Kohelet", "קהלת", "Ecclesiastes", BookCategoryName.Ketuvim)
    ESTHER = Book(34, SourceType.TN, "Esther", "אסתר", "Esther", BookCategoryName.Ketuvim)
    DANIEL = Book(35, SourceType.TN, "Daniel", "דניאל", "Daniel", BookCategoryName.Ketuvim)
    EZRA = Book(36, SourceType.TN, "Ezra", "עזרא", "Ezra", BookCategoryName.Ketuvim)
    NEHEMIAH = Book(37, SourceType.TN, "Nehemiah", "נחמיה", "Nehemiah", BookCategoryName.Ketuvim)
    CHRONICLES_I = Book(38, SourceType.TN, "Divrei HaYamim I", "דברי הימים א", "I Chronicles", BookCategoryName.Ketuvim)
    CHRONICLES_II = Book(39, SourceType.TN, "Divrei HaYamim II", "דברי הימים ב", "II Chronicles", BookCategoryName.Ketuvim)

    # ── Zeraim ──
    BERAKHOT = Book(1, SourceType.BT, "Berakhot", "ברכות", "Berakhot", BookCategoryName.Zeraim)

    # ── Moed ──
    SHABBAT = Book(2, SourceType.BT, "Shabbat", "שבת", "Shabbat", BookCategoryName.Moed)
    ERUVIN = Book(3, SourceType.BT, "Eruvin", "עירובין", "Eruvin", BookCategoryName.Moed)
    PESACHIM = Book(4, SourceType.BT, "Pesachim", "פסחים", "Pesachim", BookCategoryName.Moed)
    SHEKALIM = Book(5, SourceType.BT, "Shekalim", "שקלים", "Shekalim", BookCategoryName.Moed)
    YOMA = Book(6, SourceType.BT, "Yoma", "יומא", "Yoma", BookCategoryName.Moed)
    SUKKAH = Book(7, SourceType.BT, "Sukkah", "סוכה", "Sukkah", BookCategoryName.Moed)
    BEITZAH = Book(8, SourceType.BT, "Beitzah", "ביצה", "Beitzah", BookCategoryName.Moed)
    ROSH_HASHANAH = Book(9, SourceType.BT, "Rosh Hashanah", "ראש השנה", "Rosh Hashanah", BookCategoryName.Moed)
    TAANIT = Book(10, SourceType.BT, "Taanit", "תענית", "Taanit", BookCategoryName.Moed)
    MEGILLAH = Book(11, SourceType.BT, "Megillah", "מגילה", "Megillah", BookCategoryName.Moed)
    MOED_KATAN = Book(12, SourceType.BT, "Moed Katan", "מועד קטן", "Moed Katan", BookCategoryName.Moed)
    CHAGIGAH = Book(13, SourceType.BT, "Chagigah", "חגיגה", "Chagigah", BookCategoryName.Moed)

    # ── Nashim ──
    YEVAMOT = Book(14, SourceType.BT, "Yevamot", "יבמות", "Yevamot", BookCategoryName.Nashim)
    KETUBOT = Book(15, SourceType.BT, "Ketubot", "כתובות", "Ketubot", BookCategoryName.Nashim)
    NEDARIM = Book(16, SourceType.BT, "Nedarim", "נדרים", "Nedarim", BookCategoryName.Nashim)
    NAZIR = Book(17, SourceType.BT, "Nazir", "נזיר", "Nazir", BookCategoryName.Nashim)
    SOTAH = Book(18, SourceType.BT, "Sotah", "סוטה", "Sotah", BookCategoryName.Nashim)
    GITTIN = Book(19, SourceType.BT, "Gittin", "גיטין", "Gittin", BookCategoryName.Nashim)
    KIDDUSHIN = Book(20, SourceType.BT, "Kiddushin", "קידושין", "Kiddushin", BookCategoryName.Nashim)

    # ── Nezikin ──
    BAVA_KAMMA = Book(21, SourceType.BT, "Bava Kamma", "בבא קמא", "Bava Kamma", BookCategoryName.Nezikin)
    BAVA_METZIA = Book(22, SourceType.BT, "Bava Metzia", "בבא מציעא", "Bava Metzia", BookCategoryName.Nezikin)
    BAVA_BATRA = Book(23, SourceType.BT, "Bava Batra", "בבא בתרא", "Bava Batra", BookCategoryName.Nezikin)
    SANHEDRIN = Book(24, SourceType.BT, "Sanhedrin", "סנהדרין", "Sanhedrin", BookCategoryName.Nezikin)
    MAKKOT = Book(25, SourceType.BT, "Makkot", "מכות", "Makkot", BookCategoryName.Nezikin)
    SHEVUOT = Book(26, SourceType.BT, "Shevuot", "שבועות", "Shevuot", BookCategoryName.Nezikin)
    AVODAH_ZARAH = Book(27, SourceType.BT, "Avodah Zarah", "עבודה זרה", "Avodah Zarah", BookCategoryName.Nezikin)
    HORAYOT = Book(28, SourceType.BT, "Horayot", "הוריות", "Horayot", BookCategoryName.Nezikin)

    # ── Kodashim ──
    ZEVACHIM = Book(29, SourceType.BT, "Zevachim", "זבחים", "Zevachim", BookCategoryName.Kodashim)
    MENACHOT = Book(30, SourceType.BT, "Menachot", "מנחות", "Menachot", BookCategoryName.Kodashim)
    CHULLIN = Book(31, SourceType.BT, "Chullin", "חולין", "Chullin", BookCategoryName.Kodashim)
    BEKHOROT = Book(32, SourceType.BT, "Bekhorot", "בכורות", "Bekhorot", BookCategoryName.Kodashim)
    ARAKHIN = Book(33, SourceType.BT, "Arakhin", "ערכין", "Arakhin", BookCategoryName.Kodashim)
    TEMURAH = Book(34, SourceType.BT, "Temurah", "תמורה", "Temurah", BookCategoryName.Kodashim)
    KERITOT = Book(35, SourceType.BT, "Keritot", "כריתות", "Keritot", BookCategoryName.Kodashim)
    MEILAH = Book(36, SourceType.BT, "Meilah", "מעילה", "Meilah", BookCategoryName.Kodashim)
    KINNIM = Book(37, SourceType.BT, "Kinnim", "קנים", "Kinnim", BookCategoryName.Kodashim)
    TAMID = Book(38, SourceType.BT, "Tamid", "תמיד", "Tamid", BookCategoryName.Kodashim)
    MIDDOT = Book(39, SourceType.BT, "Middot", "מידות", "Middot", BookCategoryName.Kodashim)

    # ── Tahorot ──
    NIDDAH = Book(40, SourceType.BT, "Niddah", "נדה", "Niddah", BookCategoryName.Tahorot)
