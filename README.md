# Bouwman Tools — Belastingtools

Een Streamlit-app met belastingtools voor dagelijks gebruik.

**Live:** [belastingtooljoindk.streamlit.app](https://belastingtooljoindk.streamlit.app)

---

## Tools

### 🏦 Betalingskenmerk
Decodeert 16-cijferige Belastingdienst betalingskenmerken.

- Herkent belastingsoort: LH, OB, VpB, IB en toeslagen
- Reconstrueert het RSIN via 11-proof (inclusief BTW-nummer)
- Toont jaar en tijdvak (maand of kwartaal)
- Genereert een boekhoudingomschrijving (bijv. "Afdr. OB mei 2026") met kopieerknop
- Zoekt automatisch de bedrijfsnaam **en SBI-code** op via de KvK API (RSIN-lookup)
- **Auto-decode bij plakken** — geen klik nodig

Gevalideerd kenmerk: `4863521721601050` = Aangifte OB, mei 2026, RSIN 863521721

### 🇪🇺 VIES BTW-controle
Valideert Europese BTW-nummers via de officiële EU VIES-database.

- Ondersteunt alle EU-landen (NL, DE, BE, FR, ...)
- Toont geldigheid, bedrijfsnaam en adres
- Leidt voor NL-nummers automatisch het RSIN af
- Gratis, geen API-sleutel vereist

### 🔍 KvK / SBI opzoeken
Zoek bedrijfsgegevens op via de KvK Handelsregister API.

- Zoeken op bedrijfsnaam, KvK-nummer (8 cijfers) of RSIN (9 cijfers)
- Toont naam, KvK-nummer, RSIN en SBI-activiteitscode(s)
- Onderscheid hoofd- en nevenactiviteiten
- Tot 10 resultaten per zoekopdracht

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

### 🚗 Auto BTW privé
Berekent de BTW-correctie en bijtelling voor privégebruik van een zakelijke auto (forfaitmethode).

- Kenteken invoeren → automatische opzoekservice via het **RDW kentekenregister** (gratis, geen API-sleutel)
- Haalt op: merk, model, bouwjaar, brandstof, CO₂-uitstoot en catalogusprijs
- **BTW-correctie** (art. 4 lid 2 Wet OB): 2,7% of 1,5% (marge-auto) van catalogusprijs
- **Bijtelling**: bijtellingpercentage op basis van berekeningsjaar en brandstof/CO₂
  - Benzine/diesel: 22% (2017+), 25% (2012–2016)
  - Elektrisch/waterstof: laag tarief met cap (bijv. 16% t/m €30.000 in 2025)
- Keuze volledig jaar of eigen periode
- Catalogusprijs handmatig invullen als RDW geen waarde heeft

---

## Structuur

| Bestand | Beschrijving |
|---------|-------------|
| `app.py` | Entrypoint — `st.navigation()` router |
| `pages/Betalingskenmerk.py` | Betalingskenmerk decoder + KvK naam/SBI |
| `pages/VIES_BTW_Controle.py` | EU BTW-nummer validatie via VIES |
| `pages/KvK_SBI_Opzoeken.py` | KvK / SBI opzoeken op naam, KvK-nr of RSIN |
| `pages/Belastingrente_IB.py` | Belastingrente IB calculator |
| `pages/Belastingrente_VpB.py` | Belastingrente VpB calculator |
| `pages/Auto_BTW_Prive.py` | Auto BTW privé calculator (RDW-koppeling) |
| `_auto_paste.py` | Streamlit custom component declaratie (paste-detectie) |
| `_components/auto_paste/` | HTML/JS voor de paste-component |
| `_tarieven_check.py` | Maandelijkse check op nieuwe tarieven (belastingdienst.nl) |
| `requirements.txt` | Python dependencies |

---

## API-sleutels

| API | Gebruikt door | Kosten | Sleutel vereist |
|-----|--------------|--------|-----------------|
| KvK Handelsregister | Betalingskenmerk, KvK/SBI | ~€0,02–0,04 per aanroep | Ja — via `.streamlit/secrets.toml` |
| RDW Open Data | Auto BTW privé | Gratis | Nee |
| EU VIES | VIES BTW-controle | Gratis | Nee |

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

---

## Bronnen

- [Specificatie Betalingskenmerk_bepaling v1.5 — Belastingdienst](https://odb.belastingdienst.nl/wp-content/uploads/2025/07/Specificatie-Betalingskenmerk_bepaling_1.5.pdf)
- [Overzicht percentages belastingrente — Belastingdienst](https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/standaard_functies/prive/contact/rechten_en_plichten_bij_de_belastingdienst/belastingrente/overzicht_percentages_belastingrente)
- [KvK Handelsregister API](https://developers.kvk.nl)
- [EU VIES API](https://ec.europa.eu/taxation_customs/vies/)
