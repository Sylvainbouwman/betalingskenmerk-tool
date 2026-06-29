# betalingskenmerk-tool

Decodeert 16-cijferige Belastingdienst betalingskenmerken volledig client-side, op basis van de officiële specificatie v1.5.

**Live:** [bouwman.tools/betalingskenmerk.html](https://bouwman.tools/betalingskenmerk.html)

## Wat doet het

- Herkent belastingsoort: LB, OB, VpB, IB en toeslagen
- Reconstrueert het RSIN via 11-proof (inclusief BTW-nummer)
- Toont jaar en tijdvak (maand of kwartaal)
- Genereert een boekhoudingomschrijving (bijv. "Afdr. OB mei 2026")
- Visuele digit-strip met actieve posities

Gevalideerd kenmerk: `4863521721601050` = Aangifte OB, mei 2026, RSIN 863521721

## Architectuur

Één enkel HTML-bestand (`betalingskenmerk.html`), geen externe dependencies. Bij elke push naar `master` kopieert de sync-workflow het bestand automatisch naar [bouwman-tools](https://github.com/Sylvainbouwman/bouwman-tools).

## Bronspec

[Specificatie Betalingskenmerk_bepaling v1.5 — Belastingdienst](https://odb.belastingdienst.nl/wp-content/uploads/2025/07/Specificatie-Betalingskenmerk_bepaling_1.5.pdf)
