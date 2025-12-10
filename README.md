# 📚 ChatBlatt
### An Indexed Database of Torah Sources

<div align="center">
  
[![Powered by Sefaria](YOUR_IMAGE_URL_HERE)](https://www.sefaria.org)

*Making the vast world of Jewish texts accessible and discoverable*

</div>

---

## 📖 About | אודות

<details open>
<summary><b>What is ChatBlatt? | מהו צ'אטבלאט?</b></summary>
<br>

**ChatBlatt is an indexed database of Jewish texts** based on Sefaria's comprehensive resource library. Each book is intelligently split into passages, with every passage tagged with relevant entities that appear within it. Through these entities, relationships are crafted between passages, creating a beautiful network of accessible information that connects the vast tapestry of Torah sources.

**צ'אטבלאט הוא מסד נתונים מאונדקס של טקסטים יהודיים** המבוסס על ספריית המקורות המקיפה של ספריא. כל ספר מחולק בצורה חכמה לקטעים, כאשר כל קטע מתויג בישויות הרלוונטיות המופיעות בו. באמצעות ישויות אלו נוצרים קשרים בין קטעים, ויוצרים רשת יפה של מידע נגיש המקשרת את שטיח המקורות העשיר של התורה.

</details>

<details>
<summary><b>Why Different Than Other Search Engines? | למה שונה ממנועי חיפוש אחרים?</b></summary>
<br>

### 🎯 Unbiased Discovery

**Google and ChatGPT give very strong bias toward oft-quoted passages** because they are based on articles and content that are commonly viewed on the internet. This essentially hides so many gems of our Torah underneath the more commonly seen sources.

**גוגל ו-ChatGPT נותנים הטיה חזקה מאוד לקטעים המצוטטים לעתים קרובות** מכיוון שהם מבוססים על מאמרים ותוכן הנצפים באינטרנט. זה למעשה מסתיר כל כך הרבה פנינים של התורה שלנו מתחת למקורות הנפוצים יותר.

### 🔍 Direct Source Access

Unlike other AI products, **ChatBlatt gives the user direct access to untainted sources**. Although there is a small percentage of error in the AI-based associations, the user will never see a "made up" or tainted source. Every passage comes directly from authenticated texts.

בניגוד למוצרי AI אחרים, **צ'אטבלאט נותן למשתמש גישה ישירה למקורות לא מזויפים**. למרות שיש אחוז קטן של שגיאות בקישורים המבוססים על AI, המשתמש לעולם לא יראה מקור "מומצא" או מזויף.

</details>

<details>
<summary><b>How It Works | איך זה עובד</b></summary>
<br>

### 🔄 The Pipeline

1. **📥 Data Ingestion**
   - ChatBlatt iterates over parts of Sefaria's database via Sefaria's APIs
   - Sources are combined to form evenly-lengthed passages
   - See our DB's metadata for passage structure details

2. **🤖 Entity Extraction**
   - ChatBlatt queries Gemini using carefully crafted prompts
   - Specified Entities and Relationships are identified in each passage
   - Heavy validation ensures accuracy of Gemini's suggestions

3. **💾 Data Structuring**
   - Entities and Relationships are saved independently of passages
   - Each passage is labeled with its entities and relationships
   - Creates a web of interconnected knowledge

4. **✨ Enrichment**
   - LLM queries enrich entities with additional metadata
   - Validation ensures quality of enriched data
   - Useful filters help users navigate tens of thousands of entities

### צינור העיבוד

**צ'אטבלאט עובד בתהליך רב-שלבי:** קליטת נתונים מספריא, חילוץ ישויות באמצעות בינה מלאכותית, מיבנה הנתונים ברשת מקושרת, והעשרת המידע עם מטא-דאטה מאומתת.

</details>

<details>
<summary><b>Challenges We Encountered | אתגרים שנתקלנו בהם</b></summary>
<br>

### 🎭 Recognizing Different Entities with Same Name

**The Challenge:** Because the LLM is context-free, it's challenging to distinguish between entities with identical names.

**Example:** Tamar (wife of Yehuda) vs. Tamar (daughter of David)

**האתגר:** מכיוון שה-LLM חסר הקשר, קשה להבחין בין ישויות עם שמות זהים, כמו תמר אשת יהודה מול תמר בת דוד.

---

### 🌐 Handling Hebrew and English

**The Challenge:** LLMs do not (yet) handle Biblical Hebrew, Rabbinical Hebrew, or Aramaic as well as they do English. Furthermore, many texts (particularly the Talmud) have numerous explanations and interpretations.

**Our Solution:** 
- All metadata is based on English translations made public by Sefaria
- Each entity is translated to ensure seamless user experience
- Relationships maintain bilingual accessibility

**הפתרון שלנו:** כל המטא-דאטה מבוסס על תרגומים לאנגלית שפורסמו על ידי ספריא, וכל ישות מתורגמת להבטחת חוויית משתמש חלקה.

</details>

---

## 🚀 How to Use | איך להשתמש

<details>
<summary><b>Getting Started | התחלה</b></summary>
<br>

```bash
# Clone the repository
git clone https://github.com/yourusername/chatblatt.git

# Install dependencies
npm install

# Configure your environment
cp .env.example .env

# Run the application
npm start
```

**הוראות בעברית:** שכפל את המאגר, התקן תלויות, הגדר את הסביבה, והפעל את האפליקציה.

</details>

---

## 🤝 Contribute | תרומה לפרויקט

<details>
<summary><b>How to Contribute | איך לתרום</b></summary>
<br>

**ChatBlatt is open source!** We welcome any code contributions you have to offer.

### Ways to Contribute:
- 🐛 Report bugs and issues
- 💡 Suggest new features
- 🔧 Submit pull requests
- 📖 Improve documentation
- 🌍 Add translations

### Get in Touch:
📧 **Email:** ChatBlatt@gmail.com  
🔗 **Repository:** [github.com/yourusername/chatblatt](https://github.com/yourusername/chatblatt)

**צ'אטבלאט הוא קוד פתוח!** אנו מזמינים כל תרומת קוד שיש לכם להציע. דרכי תרומה: דיווח על באגים, הצעת תכונות חדשות, שליחת pull requests, שיפור התיעוד והוספת תרגומים.

</details>

<details>
<summary><b>Donate in Memory | תרומה לזכר</b></summary>
<br>

Support the continued development of ChatBlatt and dedicate your contribution in memory of a loved one.

**[Donation Link Here]**

תמכו בהמשך הפיתוח של צ'אטבלאט והקדישו את תרומתכם לזכר אהוב.

</details>

---

## 👥 About the Developers | אודות המפתחים

<details>
<summary><b>Meet the Team | הכירו את הצוות</b></summary>
<br>

[Your team information here]

**Our Mission:** To make the vast ocean of Torah literature accessible, searchable, and discoverable for learners at all levels.

**המשימה שלנו:** להפוך את האוקיינוס העצום של ספרות התורה לנגיש, ניתן לחיפוש וגילוי עבור לומדים בכל הרמות.

</details>

---

<div align="center">

### 🌟 Star us on GitHub | תנו לנו כוכב ב-GitHub

**Made with ❤️ for the Jewish people**

[![Powered by Sefaria](YOUR_IMAGE_URL_HERE)](https://www.sefaria.org)

</div>
