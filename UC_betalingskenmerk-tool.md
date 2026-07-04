# UC_betalingskenmerk-tool — Belastingtools Streamlit

| | |
|---|---|
| **Eigenaar** | Sylvain Bouwman |
| **Domein** | Fiscaal / Rekenmodellen (onderdeel van UC00) |
| **Status** | Live |
| **Versie** | v1 — juni 2026 |

> Dit is een individuele tool binnen de rekenmodellenreeks. Zie [`UC_bouwman-tools (UC00)`](https://github.com/Sylvainbouwman/bouwman-tools/blob/master/UC_bouwman-tools%20(UC00).md) voor het overkoepelende kader.

## Doel

Een set praktische belastingtools voor dagelijks gebruik, beschikbaar als Streamlit-app en als statische webpagina.

## Betrokkenen

Medewerkers bij Join Administraties en DK Accountants die dagelijks belastingbetalingen verwerken of berekeningen uitvoeren.

## Trigger

Medewerker moet een betalingskenmerk opzoeken, een IB-berekening maken of een andere dagelijkse belastingtaak uitvoeren.

## As-is situatie

Betalingskenmerken worden handmatig opgezocht via de Belastingdienst-website. IB-berekeningen worden ad-hoc gedaan. Geen centrale tool voor dit soort kleine dagelijkse taken.

## To-be situatie

1. Medewerker opent de Streamlit-app of de statische webpagina
2. Direct toegang tot drie tools: betalingskenmerk genereren, IB-berekening en aanvullende belastingtool
3. Resultaat direct kopieerbaar voor gebruik in AFAS of correspondentie

## Live

- Streamlit: [belastingtooljoindk.streamlit.app](https://belastingtooljoindk.streamlit.app)
- Statisch: [bouwman.tools/betalingskenmerk.html](https://bouwman.tools/betalingskenmerk.html)

## Waarde

| | |
|---|---|
| **Tijdwinst** | Directe toegang zonder zoeken op externe websites |
| **Kwaliteit** | Consistente berekeningen; minder kans op invoerfouten |
