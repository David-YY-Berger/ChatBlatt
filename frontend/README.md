[//]: # (# Streamlit Frontend Starter)

[//]: # ()
[//]: # (## Structure)

[//]: # (- `Frontend/app.py`: entry point with language toggle and custom nav buttons. Entity Search and Maps use a popover dropdown for subtabs.)

[//]: # (- `Frontend/translations1/`: YAML translations &#40;`en.yml`, `he.yml`&#41; and helper functions.)

[//]: # (- `Frontend/components/`: shared UI pieces &#40;`header.py`, `layout.py`&#41;.)

[//]: # (- `Frontend/pages/`: tab renderers &#40;all pages have titles and lorem ipsum content in English/Hebrew&#41;.)

[//]: # (- `Frontend/assets/styles.css`: base styling; extra RTL/dark/light tweaks live in `layout.apply_layout`.)

[//]: # ()
[//]: # (## Run locally)

[//]: # (```bash)

[//]: # (cd frontend)

[//]: # (pip install -r requirements.txt)

[//]: # (streamlit run app.py)

[//]: # (```)

[//]: # ()
[//]: # (## PyCharm Setup)

[//]: # (To resolve import warnings in PyCharm:)

[//]: # (1. Right-click on the `Frontend` folder)

[//]: # (2. Select "Mark Directory as" → "Sources Root")

[//]: # ()
[//]: # (## Editing translations)

[//]: # (- Add or edit keys in `Frontend/translations1/en.yml` and mirror them in `Frontend/translations1/he.yml`.)

[//]: # (- Use `get_text&#40;"path.to.key", lang&#41;` in code; it falls back to English if a key is missing in the chosen language.)

[//]: # (- Page titles are under `page_titles.*`.)

[//]: # (- Nav labels are under `nav.*`, `entity_tabs.*`, and `map_tabs.*`.)

[//]: # ()
[//]: # (## RTL Support)

[//]: # (- When Hebrew is selected, the page reorients right-to-left automatically.)

[//]: # (- Tab order is mirrored &#40;reversed&#41; for Hebrew.)

[//]: # (- Switching back to English reorients left-to-right.)

[//]: # ()
[//]: # (## Light/Dark Mode)

[//]: # (- Respects system `prefers-color-scheme`. Dark mode uses deep blues; light mode uses clean whites and soft grays.)
