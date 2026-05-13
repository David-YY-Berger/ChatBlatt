# bs"d - lehagdil torah velahadir
from dataclasses import dataclass

from backend.models_db.Enums import SourceType


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
    GENESIS = Book(1, SourceType.TN, "Bereishit", "בראשית", "Genesis")
    EXODUS = Book(2, SourceType.TN, "Shemot", "שמות", "Exodus")
    LEVITICUS = Book(3, SourceType.TN, "Vayikra", "ויקרא", "Leviticus")
    NUMBERS = Book(4, SourceType.TN, "Bamidbar", "במדבר", "Numbers")
    DEUTERONOMY = Book(5, SourceType.TN, "Devarim", "דברים", "Deuteronomy")

    # ── Nevi'im ──
    JOSHUA = Book(6, SourceType.TN, "Yehoshua", "יהושע", "Joshua")
    JUDGES = Book(7, SourceType.TN, "Shoftim", "שופטים", "Judges")
    SAMUEL_I = Book(8, SourceType.TN, "Shmuel I", "שמואל א", "I Samuel")
    SAMUEL_II = Book(9, SourceType.TN, "Shmuel II", "שמואל ב", "II Samuel")
    KINGS_I = Book(10, SourceType.TN, "Melakhim I", "מלכים א", "I Kings")
    KINGS_II = Book(11, SourceType.TN, "Melakhim II", "מלכים ב", "II Kings")
    ISAIAH = Book(12, SourceType.TN, "Yeshayahu", "ישעיהו", "Isaiah")
    JEREMIAH = Book(13, SourceType.TN, "Yirmiyahu", "ירמיהו", "Jeremiah")
    EZEKIEL = Book(14, SourceType.TN, "Yehezkel", "יחזקאל", "Ezekiel")
    HOSEA = Book(15, SourceType.TN, "Hoshea", "הושע", "Hosea")
    JOEL = Book(16, SourceType.TN, "Yoel", "יואל", "Joel")
    AMOS = Book(17, SourceType.TN, "Amos", "עמוס", "Amos")
    OBADIAH = Book(18, SourceType.TN, "Ovadyah", "עובדיה", "Obadiah")
    JONAH = Book(19, SourceType.TN, "Yonah", "יונה", "Jonah")
    MICAH = Book(20, SourceType.TN, "Mikah", "מיכה", "Micah")
    NAHUM = Book(21, SourceType.TN, "Nachum", "נחום", "Nahum")
    HABAKKUK = Book(22, SourceType.TN, "Chavakuk", "חבקוק", "Habakkuk")
    ZEPHANIAH = Book(23, SourceType.TN, "Tzefanyah", "צפניה", "Zephaniah")
    HAGGAI = Book(24, SourceType.TN, "Chaggai", "חגי", "Haggai")
    ZECHARIAH = Book(25, SourceType.TN, "Zekharyah", "זכריה", "Zechariah")
    MALACHI = Book(26, SourceType.TN, "Malakhi", "מלאכי", "Malachi")

    # ── Ketuvim ──
    PSALMS = Book(27, SourceType.TN, "Tehillim", "תהילים", "Psalms")
    PROVERBS = Book(28, SourceType.TN, "Mishlei", "משלי", "Proverbs")
    JOB = Book(29, SourceType.TN, "Iyov", "איוב", "Job")
    SONG_OF_SONGS = Book(30, SourceType.TN, "Shir HaShirim", "שיר השירים", "Song of Songs")
    RUTH = Book(31, SourceType.TN, "Rut", "רות", "Ruth")
    LAMENTATIONS = Book(32, SourceType.TN, "Eikhah", "איכה", "Lamentations")
    ECCLESIASTES = Book(33, SourceType.TN, "Kohelet", "קהלת", "Ecclesiastes")
    ESTHER = Book(34, SourceType.TN, "Esther", "אסתר", "Esther")
    DANIEL = Book(35, SourceType.TN, "Daniel", "דניאל", "Daniel")
    EZRA = Book(36, SourceType.TN, "Ezra", "עזרא", "Ezra")
    NEHEMIAH = Book(37, SourceType.TN, "Nehemiah", "נחמיה", "Nehemiah")
    CHRONICLES_I = Book(38, SourceType.TN, "Divrei HaYamim I", "דברי הימים א", "I Chronicles")
    CHRONICLES_II = Book(39, SourceType.TN, "Divrei HaYamim II", "דברי הימים ב", "II Chronicles")

    # ── Zeraim ──
    BERAKHOT = Book(1, SourceType.BT, "Berakhot", "ברכות", "Berakhot")

    # ── Moed ──
    SHABBAT = Book(2, SourceType.BT, "Shabbat", "שבת", "Shabbat")
    ERUVIN = Book(3, SourceType.BT, "Eruvin", "עירובין", "Eruvin")
    PESACHIM = Book(4, SourceType.BT, "Pesachim", "פסחים", "Pesachim")
    SHEKALIM = Book(5, SourceType.BT, "Shekalim", "שקלים", "Shekalim")
    YOMA = Book(6, SourceType.BT, "Yoma", "יומא", "Yoma")
    SUKKAH = Book(7, SourceType.BT, "Sukkah", "סוכה", "Sukkah")
    BEITZAH = Book(8, SourceType.BT, "Beitzah", "ביצה", "Beitzah")
    ROSH_HASHANAH = Book(9, SourceType.BT, "Rosh Hashanah", "ראש השנה", "Rosh Hashanah")
    TAANIT = Book(10, SourceType.BT, "Taanit", "תענית", "Taanit")
    MEGILLAH = Book(11, SourceType.BT, "Megillah", "מגילה", "Megillah")
    MOED_KATAN = Book(12, SourceType.BT, "Moed Katan", "מועד קטן", "Moed Katan")
    CHAGIGAH = Book(13, SourceType.BT, "Chagigah", "חגיגה", "Chagigah")

    # ── Nashim ──
    YEVAMOT = Book(14, SourceType.BT, "Yevamot", "יבמות", "Yevamot")
    KETUBOT = Book(15, SourceType.BT, "Ketubot", "כתובות", "Ketubot")
    NEDARIM = Book(16, SourceType.BT, "Nedarim", "נדרים", "Nedarim")
    NAZIR = Book(17, SourceType.BT, "Nazir", "נזיר", "Nazir")
    SOTAH = Book(18, SourceType.BT, "Sotah", "סוטה", "Sotah")
    GITTIN = Book(19, SourceType.BT, "Gittin", "גיטין", "Gittin")
    KIDDUSHIN = Book(20, SourceType.BT, "Kiddushin", "קידושין", "Kiddushin")

    # ── Nezikin ──
    BAVA_KAMMA = Book(21, SourceType.BT, "Bava Kamma", "בבא קמא", "Bava Kamma")
    BAVA_METZIA = Book(22, SourceType.BT, "Bava Metzia", "בבא מציעא", "Bava Metzia")
    BAVA_BATRA = Book(23, SourceType.BT, "Bava Batra", "בבא בתרא", "Bava Batra")
    SANHEDRIN = Book(24, SourceType.BT, "Sanhedrin", "סנהדרין", "Sanhedrin")
    MAKKOT = Book(25, SourceType.BT, "Makkot", "מכות", "Makkot")
    SHEVUOT = Book(26, SourceType.BT, "Shevuot", "שבועות", "Shevuot")
    AVODAH_ZARAH = Book(27, SourceType.BT, "Avodah Zarah", "עבודה זרה", "Avodah Zarah")
    HORAYOT = Book(28, SourceType.BT, "Horayot", "הוריות", "Horayot")

    # ── Kodashim ──
    ZEVACHIM = Book(29, SourceType.BT, "Zevachim", "זבחים", "Zevachim")
    MENACHOT = Book(30, SourceType.BT, "Menachot", "מנחות", "Menachot")
    CHULLIN = Book(31, SourceType.BT, "Chullin", "חולין", "Chullin")
    BEKHOROT = Book(32, SourceType.BT, "Bekhorot", "בכורות", "Bekhorot")
    ARAKHIN = Book(33, SourceType.BT, "Arakhin", "ערכין", "Arakhin")
    TEMURAH = Book(34, SourceType.BT, "Temurah", "תמורה", "Temurah")
    KERITOT = Book(35, SourceType.BT, "Keritot", "כריתות", "Keritot")
    MEILAH = Book(36, SourceType.BT, "Meilah", "מעילה", "Meilah")
    KINNIM = Book(37, SourceType.BT, "Kinnim", "קנים", "Kinnim")
    TAMID = Book(38, SourceType.BT, "Tamid", "תמיד", "Tamid")
    MIDDOT = Book(39, SourceType.BT, "Middot", "מידות", "Middot")

    # ── Tahorot ──
    NIDDAH = Book(40, SourceType.BT, "Niddah", "נדה", "Niddah")
