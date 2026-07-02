# Betalingskenmerk Tool

## Omgeving

- Python: `C:\Python314\python.exe`
- `streamlit` staat **niet** in PATH. Altijd starten via:
  ```
  python -m streamlit run app.py
  ```
  Nooit `streamlit run app.py` — dat geeft "not recognized".

## Structuur

- `betalingskenmerk.html` — originele statische versie (HTML/JS, KvK via Cloudflare Worker proxy)
- `app.py` — Streamlit versie (Python, KvK via directe `requests` call)
- `requirements.txt` — `streamlit`, `requests`

## KvK API

- KvK blokkeert Cloudflare IP-adressen, daarom werkt de proxy in de HTML-versie niet.
- In de Streamlit-versie gaat de call server-side via Python → geen blokkade.
- Endpoint: `https://api.kvk.nl/api/v2/zoeken?rsin={rsin9}`
- API-sleutel: in sidebar invoeren (sessie) of via `st.secrets["kvk_api_key"]` (Streamlit Cloud).

## Samenvoegen met WWFT-app

Later toevoegen als pagina in de WWFT multi-page app: kopieer `app.py` naar
`pages/2_Betalingskenmerk.py` in die repo. Streamlit pikt het automatisch op.
