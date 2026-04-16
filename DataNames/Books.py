# bs"d - lehagdil torah velahadir
from dataclasses import dataclass

from BackEnd.DataObjects.Enums import SourceType


@dataclass(frozen=True)
class Book:
    source_type: SourceType
    en_display_name: str
    heb_display_name: str
    database_name: str

class BookRegistry:
    @classmethod
    def all(cls) -> list[Book]:
        return [v for v in cls.__dict__.values() if isinstance(v, Book)]

    @classmethod
    def by_source(cls, source: SourceType) -> list[Book]:
        return [b for b in cls.all() if b.source_type == source]

    @classmethod
    def get_by_db_name(cls, db_name: str) -> Book | None:
        return next((b for b in cls.all() if b.database_name == db_name), None)

class Books(BookRegistry):
    # Torah
    GENESIS = Book(SourceType.TN, "Bereishit", "בראשית", "Genesis")
    EXODUS = Book(SourceType.TN, "Shemot", "שמות", "Exodus")
    LEVITICUS = Book(SourceType.TN, "Vayikra", "ויקרא", "Leviticus")
    NUMBERS = Book(SourceType.TN, "Bamidbar", "במדבר", "Numbers")
    DEUTERONOMY = Book(SourceType.TN, "Devarim", "דברים", "Deuteronomy")

    # Nevi'im
    JOSHUA = Book(SourceType.TN, "Yehoshua", "יהושע", "Joshua")
    JUDGES = Book(SourceType.TN, "Shoftim", "שופטים", "Judges")
    SAMUEL_I = Book(SourceType.TN, "Shmuel I", "שמואל א", "I Samuel")
    SAMUEL_II = Book(SourceType.TN, "Shmuel II", "שמואל ב", "II Samuel")
    KINGS_I = Book(SourceType.TN, "Melakhim I", "מלכים א", "I Kings")
    KINGS_II = Book(SourceType.TN, "Melakhim II", "מלכים ב", "II Kings")
    ISAIAH = Book(SourceType.TN, "Yeshayahu", "ישעיהו", "Isaiah")
    JEREMIAH = Book(SourceType.TN, "Yirmiyahu", "ירמיהו", "Jeremiah")
    EZEKIEL = Book(SourceType.TN, "Yehezkel", "יחזקאל", "Ezekiel")
    HOSEA = Book(SourceType.TN, "Hoshea", "הושע", "Hosea")
    JOEL = Book(SourceType.TN, "Yoel", "יואל", "Joel")
    AMOS = Book(SourceType.TN, "Amos", "עמוס", "Amos")
    OBADIAH = Book(SourceType.TN, "Ovadyah", "עובדיה", "Obadiah")
    JONAH = Book(SourceType.TN, "Yonah", "יונה", "Jonah")
    MICAH = Book(SourceType.TN, "Mikah", "מיכה", "Micah")
    NAHUM = Book(SourceType.TN, "Nachum", "נחום", "Nahum")
    HABAKKUK = Book(SourceType.TN, "Chavakuk", "חבקוק", "Habakkuk")
    ZEPHANIAH = Book(SourceType.TN, "Tzefanyah", "צפניה", "Zephaniah")
    HAGGAI = Book(SourceType.TN, "Chaggai", "חגי", "Haggai")
    ZECHARIAH = Book(SourceType.TN, "Zekharyah", "זכריה", "Zechariah")
    MALACHI = Book(SourceType.TN, "Malakhi", "מלאכי", "Malachi")

    # Ketuvim
    PSALMS = Book(SourceType.TN, "Tehillim", "תהילים", "Psalms")
    PROVERBS = Book(SourceType.TN, "Mishlei", "משלי", "Proverbs")
    JOB = Book(SourceType.TN, "Iyov", "איוב", "Job")
    SONG_OF_SONGS = Book(SourceType.TN, "Shir HaShirim", "שיר השירים", "Song of Songs")
    RUTH = Book(SourceType.TN, "Rut", "רות", "Ruth")
    LAMENTATIONS = Book(SourceType.TN, "Eikhah", "איכה", "Lamentations")
    ECCLESIASTES = Book(SourceType.TN, "Kohelet", "קהלת", "Ecclesiastes")
    ESTHER = Book(SourceType.TN, "Esther", "אסתר", "Esther")
    DANIEL = Book(SourceType.TN, "Daniel", "דניאל", "Daniel")
    EZRA = Book(SourceType.TN, "Ezra", "עזרא", "Ezra")
    NEHEMIAH = Book(SourceType.TN, "Nehemiah", "נחמיה", "Nehemiah")
    CHRONICLES_I = Book(SourceType.TN, "Divrei HaYamim I", "דברי הימים א", "I Chronicles")
    CHRONICLES_II = Book(SourceType.TN, "Divrei HaYamim II", "דברי הימים ב", "II Chronicles")

    # Zeraim
    BERAKHOT = Book(SourceType.BT, "Berakhot", "ברכות", "Berakhot")

    # Moed
    SHABBAT = Book(SourceType.BT, "Shabbat", "שבת", "Shabbat")
    ERUVIN = Book(SourceType.BT, "Eruvin", "עירובין", "Eruvin")
    PESACHIM = Book(SourceType.BT, "Pesachim", "פסחים", "Pesachim")
    # SHEKALIM = Book(SourceType.BT, "Shekalim", "שקלים", "Shekalim")  # missing?
    YOMA = Book(SourceType.BT, "Yoma", "יומא", "Yoma")
    SUKKAH = Book(SourceType.BT, "Sukkah", "סוכה", "Sukkah")
    BEITZAH = Book(SourceType.BT, "Beitzah", "ביצה", "Beitzah")
    ROSH_HASHANAH = Book(SourceType.BT, "Rosh Hashanah", "ראש השנה", "Rosh Hashanah")
    TAANIT = Book(SourceType.BT, "Taanit", "תענית", "Taanit")
    MEGILLAH = Book(SourceType.BT, "Megillah", "מגילה", "Megillah")
    MOED_KATAN = Book(SourceType.BT, "Moed Katan", "מועד קטן", "Moed Katan")
    CHAGIGAH = Book(SourceType.BT, "Chagigah", "חגיגה", "Chagigah")

    # Nashim
    YEVAMOT = Book(SourceType.BT, "Yevamot", "יבמות", "Yevamot")
    KETUBOT = Book(SourceType.BT, "Ketubot", "כתובות", "Ketubot")
    NEDARIM = Book(SourceType.BT, "Nedarim", "נדרים", "Nedarim")
    NAZIR = Book(SourceType.BT, "Nazir", "נזיר", "Nazir")
    SOTAH = Book(SourceType.BT, "Sotah", "סוטה", "Sotah")
    GITTIN = Book(SourceType.BT, "Gittin", "גיטין", "Gittin")
    KIDDUSHIN = Book(SourceType.BT, "Kiddushin", "קידושין", "Kiddushin")

    # Nezikin
    BAVA_KAMMA = Book(SourceType.BT, "Bava Kamma", "בבא קמא", "Bava Kamma")
    BAVA_METZIA = Book(SourceType.BT, "Bava Metzia", "בבא מציעא", "Bava Metzia")
    BAVA_BATRA = Book(SourceType.BT, "Bava Batra", "בבא בתרא", "Bava Batra")
    SANHEDRIN = Book(SourceType.BT, "Sanhedrin", "סנהדרין", "Sanhedrin")
    MAKKOT = Book(SourceType.BT, "Makkot", "מכות", "Makkot")
    SHEVUOT = Book(SourceType.BT, "Shevuot", "שבועות", "Shevuot")
    AVODAH_ZARAH = Book(SourceType.BT, "Avodah Zarah", "עבודה זרה", "Avodah Zarah")
    HORAYOT = Book(SourceType.BT, "Horayot", "הוריות", "Horayot")

    # Kodashim
    ZEVACHIM = Book(SourceType.BT, "Zevachim", "זבחים", "Zevachim")
    MENACHOT = Book(SourceType.BT, "Menachot", "מנחות", "Menachot")
    CHULLIN = Book(SourceType.BT, "Chullin", "חולין", "Chullin")
    BEKHOROT = Book(SourceType.BT, "Bekhorot", "בכורות", "Bekhorot")
    ARAKHIN = Book(SourceType.BT, "Arakhin", "ערכין", "Arakhin")
    TEMURAH = Book(SourceType.BT, "Temurah", "תמורה", "Temurah")
    KERITOT = Book(SourceType.BT, "Keritot", "כריתות", "Keritot")
    MEILAH = Book(SourceType.BT, "Meilah", "מעילה", "Meilah")
    TAMID = Book(SourceType.BT, "Tamid", "תמיד", "Tamid")
    # KINNIM = Book(SourceType.BT, "Kinnim", "קנים", "Kinnim")  # missing?
    # MIDDOT = Book(SourceType.BT, "Middot", "מידות", "Middot")  # missing?

    # Tahorot
    NIDDAH = Book(SourceType.BT, "Niddah", "נדה", "Niddah")

