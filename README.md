# betalingskenmerk-tool

Decodeert 16-cijferige Belastingdienst betalingskenmerken en zoekt automatisch de bijbehorende bedrijfsnaam op via de KvK API.

**Live (Streamlit):** komt beschikbaar via Streamlit Cloud  
**Statische versie:** [bouwman.tools/betalingskenmerk.html](https://bouwman.tools/betalingskenmerk.html)

## Wat doet het

- Herkent belastingsoort: LB, OB, VpB, IB en toeslagen
- Reconstrueert het RSIN via 11-proof (inclusief BTW-nummer)
- Toont jaar en tijdvak (maand of kwartaal)
- Genereert een boekhoudingomschrijving (bijv. "Afdr. OB mei 2026")
- Zoekt automatisch de bedrijfsnaam op via de KvK API (RSIN-lookup)
- Visuele digit-strip met actieve posities

Gevalideerd kenmerk: `4863521721601050` = Aangifte OB, mei 2026, RSIN 863521721

## Architectuur

| Bestand | Beschrijving |
|---------|-------------|
| `app.py` | Streamlit-app — server-side KvK-lookup, voor gebruik door collega's |
| `betalingskenmerk.html` | Statische HTML-versie — volledig client-side, geen KvK-lookup |
| `requirements.txt` | Python dependencies (`streamlit`, `requests`) |

De HTML-versie heeft geen werkende KvK-koppeling omdat de KvK de IP-adressen van Cloudflare blokkeert. De Streamlit-versie doet de API-call server-side en heeft dit probleem niet.

## Lokaal draaien

```bash
python -m streamlit run app.py
```

> Let op: `streamlit` staat niet in PATH op dit systeem — gebruik altijd `python -m streamlit`.

Maak een `.streamlit/secrets.toml` aan met:

```toml
kvk_api_key = "jouw-kvk-api-sleutel"
```

## Deployment (Streamlit Cloud)

1. Push naar `master`
2. Streamlit Cloud deployt automatisch
3. Stel de API-sleutel in via **Settings → Secrets** in het Streamlit Cloud dashboard

## Bronspec

[Specificatie Betalingskenmerk_bepaling v1.5 — Belastingdienst](https://odb.belastingdienst.nl/wp-content/uploads/2025/07/Specificatie-Betalingskenmerk_bepaling_1.5.pdf)
