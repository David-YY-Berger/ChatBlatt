# 📚 ChatBlatt
### An Indexed Database of Torah Sources

<div align="center">
  
<a href="https://www.sefaria.org">
<img width="462" height="240" alt="Powered by Sefaria" src="https://github.com/user-attachments/assets/0495eb35-9ce9-40d7-9424-8a1f8910ca6b" />
</a>

</div>

---

## 📖 About

<details open>
<summary><b>What is ChatBlatt?</b></summary>
<br>

ChatBlatt is an indexed database of jewish texts (based on Sefaria’s resource). Each book is split into passages, each passage tagged with relevant entities that appear in that passage. Additionally, relationships are crafted through these entities (based on each passage), create a beautiful network of accessible information. 

</details>

<details>
<summary><b>How is ChatBlatt different than all other Torah Search Engines?</b></summary>
<br>

**No popularity bias**: Google and ChatGPT favor frequently cited passages. ChatBlatt treats all sources equally, revealing hidden gems. How many times do you like obscure midrashim? or Talmud Yerushalmi?

**Direct sources**: Unlike AI chatbots, ChatBlatt never invents sources. Small tagging errors possible, but sources are always authentic.

</details>

<details>
<summary><b>How It Works</b></summary>
<br>

ChatBlatt begins by iterating over parts of Sefaria’s database via Sefaria's API’s, combining sources together until they form evenly lengthed passages (see our DB’s metadata - ). This is based on Sefaria's API's ‘passages’.

Then, ChatBlatt queries Gemini (based on carefully crafted prompts) to find specified Entities and Relationships in the passage. After heavy validation of Gemini’s suggestion, ChatBlatt saves these Entities and Relationships independently of the passage, and then add labels to each passage with entities and Relationships that appear in it. 

Then, ChatBlatt queries the LLM to enrich the Entities with metadata. After validating these now rich entities, ChatBlatt can display useful filters for the User to find what he/she is looking for through tens of thousands of entities. Or build multi dimensional maps of entities and relationships linked with an associated passage.


</details>

<details>
<summary><b>Challenges We've Encountered</b></summary>
<br>

**Recognizing Different Entities with same name**: Because the LLM is context free, it is challenging to recognize that the same name can be used by 2 (or more) different people. For Example, Tamar (wife of Yehuda) is different from Tamar (daughter of David). Solution: in progress. 
    
**Hebrew handling**: LLM’s do not (yet) handle biblical Hebrew, rabbinical Hebrew or Aramaic Hebrew as well as they do English. Furthermore, many texts (particularly the Talmud) have many explanations. Therefore, we have chosen to base all metadata on English translations (made public by Sefaria). To ensure the User doesn't feel the difference, each entitiy (and therefore the relationships) are translated


</details>

---

## 🚀 How to Use

We are building a really cool UI! hope to release it in July 2026

---

## 🤝 Contribute

ChatBlatt is open source, we would love to see any code contributions you have to offer!

**Contact**: ChatBlatt@gmail.com  

**Donate in memory**: (when i set up a server in july 2026, then there will be costs to keep it running)

---

## 👥 Developers

lmk if you're interesting in joining :) 

---

<div align="center">

**Made with ❤️ for Hashem & Torah learning**

<a href="https://www.sefaria.org">
<img width="462" height="240" alt="Powered by Sefaria" src="https://github.com/user-attachments/assets/0495eb35-9ce9-40d7-9424-8a1f8910ca6b" />
</a>
</div>
