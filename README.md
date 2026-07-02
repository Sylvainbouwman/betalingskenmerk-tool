# Bouwman Tools — Belastingtools

Een Streamlit-app met drie belastingtools voor dagelijks gebruik.

**Live:** beschikbaar via Streamlit Cloud  
**Statische versie betalingskenmerk:** [bouwman.tools/betalingskenmerk.html](https://bouwman.tools/betalingskenmerk.html)

---

## Tools

### 🏦 Betalingskenmerk
Decodeert 16-cijferige Belastingdienst betalingskenmerken.

- Herkent belastingsoort: LB, OB, VpB, IB en toeslagen
- Reconstrueert het RSIN via 11-proof (inclusief BTW-nummer)
- Toont jaar en tijdvak (maand of kwartaal)
- Genereert een boekhoudingomschrijving (bijv. "Afdr. OB mei 2026") met kopieerknop
- Zoekt automatisch de bedrijfsnaam op via de KvK API (RSIN-lookup)
- **Auto-decode bij plakken** — geen klik nodig

Gevalideerd kenmerk: `4863521721601050` = Aangifte OB, mei 2026, RSIN 863521721

### 📊 Belastingrente IB
Berekent de belastingrente voor een aanslag inkomstenbelasting.

- Renteperiode: 1 juli volgend op het belastingjaar t/m 6 weken na dagtekening
- Tarieven rechtstreeks van belastingdienst.nl (bijgewerkt 2 juli 2026)
- Altijd zichtbare uitsplitsing per tariefperiode
- Werkt ook als voorcalculatie met verwachte dagtekening
- **Automatische check:** eens per maand wordt gecontroleerd of belastingdienst.nl nieuwere tarieven vermeldt

### 📊 Belastingrente VpB
Berekent de belastingrente voor een aanslag vennootschapsbelasting.

- Renteperiode: 6 maanden na boekjaar-einde t/m 6 weken na dagtekening
- Ondersteunt **gebroken boekjaren** (elke einddatum)
- Tarieven rechtstreeks van belastingdienst.nl (bijgewerkt 2 juli 2026)
- Altijd zichtbare uitsplitsing per tariefperiode
- Werkt ook als voorcalculatie met verwachte dagtekening
- **Automatische check:** eens per maand wordt gecontroleerd of belastingdienst.nl nieuwere tarieven vermeldt

---

## Structuur

| Bestand | Beschrijving |
|---------|-------------|
| `app.py` | Entrypoint — `st.navigation()` router |
| `pages/Betalingskenmerk.py` | Betalingskenmerk decoder |
| `pages/Belastingrente_IB.py` | Belastingrente IB calculator |
| `pages/Belastingrente_VpB.py` | Belastingrente VpB calculator |
| `_auto_paste.py` | Streamlit custom component declaratie (paste-detectie) |
| `_components/auto_paste/` | HTML/JS voor de paste-component |
| `_tarieven_check.py` | Maandelijkse check op nieuwe tarieven (belastingdienst.nl) |
| `betalingskenmerk.html` | Statische HTML-versie (geen KvK-koppeling) |
| `requirements.txt` | Python dependencies |

---

## Lokaal draaien

```bash
python -m streamlit run app.py
```

> Let op: `streamlit` staat niet in PATH op dit systeem — gebruik altijd `python -m streamlit`.

Maak een `.streamlit/secrets.toml` aan met:

```toml
kvk_api_key = "jouw-kvk-api-sleutel"
```

---

## Deployment (Streamlit Cloud)

1. Push naar `master`
2. Streamlit Cloud deployt automatisch
3. Stel de KvK API-sleutel in via **Settings → Secrets** in het Streamlit Cloud dashboard
4. De URL is aan te passen via **Settings → Custom subdomain**

---

## Bronnen

- [Specificatie Betalingskenmerk_bepaling v1.5 — Belastingdienst](https://odb.belastingdienst.nl/wp-content/uploads/2025/07/Specificatie-Betalingskenmerk_bepaling_1.5.pdf)
- [Overzicht percentages belastingrente — Belastingdienst](https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/standaard_functies/prive/contact/rechten_en_plichten_bij_de_belastingdienst/belastingrente/overzicht_percentages_belastingrente)
