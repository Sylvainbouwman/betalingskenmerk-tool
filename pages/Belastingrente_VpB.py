import streamlit as st
from datetime import date, timedelta
import calendar
from _tarieven_check import controleer_nieuwe_tarieven

# ── Tarieven ────────────────────────────────────────────────────────────────
# Enkelvoudige belastingrente VpB per jaar. Gesorteerd nieuw → oud.
# Bron: Belastingdienst / Staatscourant — laatste controle: 1 juli 2025
TARIEVEN = [
    # Bron: belastingdienst.nl — "Percentages vennootschapsbelasting"
    # Let op: 2025/2026 zijn herziene percentages (oorspronkelijk hoger vastgesteld)
    (date(2026, 1, 1),  5.00),
    (date(2025, 1, 1),  6.50),
    (date(2024, 1, 1),  7.50),
    (date(2023, 7, 1),  6.00),
    (date(2020, 10, 1), 4.00),
    (date(2020, 6, 1),  0.01),
    (date(2016, 9, 1),  8.00),
    (date(2016, 3, 1),  8.05),
    (date(2014, 9, 1),  8.15),
    (date(2014, 4, 1),  8.25),
]


_tarief_waarschuwing = controleer_nieuwe_tarieven(TARIEVEN)


def add_months(d: date, months: int) -> date:
    m = d.month + months
    y = d.year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def tarief_op(d: date) -> float:
    for start, pct in TARIEVEN:
        if d >= start:
            return pct
    return TARIEVEN[-1][1]


def bereken(bedrag: float, start: date, eind: date):
    knippunten = sorted({start, eind} | {d for d, _ in TARIEVEN if start < d < eind})
    perioden, totaal = [], 0.0
    for i in range(len(knippunten) - 1):
        a, b = knippunten[i], knippunten[i + 1]
        dagen = (b - a).days
        pct = tarief_op(a)
        rente = bedrag * (pct / 100) * (dagen / 365)
        totaal += rente
        perioden.append({"start": a, "eind": b, "dagen": dagen, "pct": pct, "rente": rente})
    return totaal, perioden


def nl_euro(x: float) -> str:
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"€ {s}"


def nl_date(d: date) -> str:
    return d.strftime("%d-%m-%Y")


# ── Opmaak ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: linear-gradient(180deg,#f8fbfd 0%,#eef3f7 100%); }
  .bk-header { background: linear-gradient(135deg,#24304A,#2f3d5d); color: white;
    border-radius: 16px; padding: 18px 22px; margin-bottom: 16px; }
  .bk-header h1 { margin: 0 0 6px; font-size: 26px; color: white; }
  .bk-header p  { margin: 0; font-size: 14px; color: rgba(255,255,255,0.88); line-height: 1.5; }
  .bk-tile { background: white; border-radius: 12px; padding: 14px 16px;
    box-shadow: 0 2px 10px rgba(36,48,74,.07); margin-bottom: 8px; }
  .bk-tile .label { font-size: 12px; color: #6b7a99; margin-bottom: 2px; }
  .bk-tile .value { font-size: 18px; font-weight: bold; color: #24304A; }
  .bk-tile .sub   { font-size: 13px; color: #6b7a99; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="bk-header">
  <h1>Belastingrente VpB</h1>
  <p>Bereken de belastingrente voor een aanslag vennootschapsbelasting.
     De rente loopt van 6 maanden na boekjaar-einde tot 6 weken na de dagtekening van de aanslag.</p>
</div>
""", unsafe_allow_html=True)

# ── Invoer ───────────────────────────────────────────────────────────────────
if _tarief_waarschuwing:
    st.warning(_tarief_waarschuwing)

huidig_jaar = date.today().year

col_a, col_b = st.columns(2)
with col_a:
    boekjaar_eind = st.date_input(
        "Einddatum boekjaar",
        value=date(huidig_jaar - 2, 12, 31),
        min_value=date(2000, 1, 1),
        max_value=date(huidig_jaar + 1, 12, 31),
        format="DD-MM-YYYY",
        help="Regulier boekjaar: 31 december. Bij een gebroken boekjaar vult u de werkelijke einddatum in.",
    )
    boekjaar = boekjaar_eind.year

with col_b:
    dagtekening = st.date_input(
        "Dagtekening aanslag (of verwachte datum)",
        value=date.today(),
        min_value=date(2015, 1, 1),
        max_value=date(huidig_jaar + 3, 12, 31),
        format="DD-MM-YYYY",
        help="Vul de werkelijke dagtekening in, of een verwachte datum om vooraf een inschatting te maken.",
    )

bedrag = st.number_input(
    "Aangeslagen bedrag VpB (€)",
    min_value=0.0,
    value=10000.0,
    step=500.0,
    format="%.2f",
)

# ── Berekening ───────────────────────────────────────────────────────────────
r_start = add_months(boekjaar_eind, 6) + timedelta(days=1)
r_eind  = dagtekening + timedelta(weeks=6)

if r_start >= r_eind:
    st.warning(
        f"Geen belastingrente: renteperiode start op {nl_date(r_start)} maar eindigt op {nl_date(r_eind)}. "
        "De aanslag is (te vroeg) gedagtekend binnen 6 maanden na het boekjaar-einde."
    )
    st.stop()

totaal_rente, deelperioden = bereken(bedrag, r_start, r_eind)
totaal_dagen = (r_eind - r_start).days

# ── Uitvoer ──────────────────────────────────────────────────────────────────
st.html(f"""
<div style="background:linear-gradient(135deg,#1a4d2e,#1e5c36);color:white;
  border-radius:14px;padding:20px 22px;margin-bottom:12px;text-align:center;
  box-shadow:0 4px 16px rgba(26,77,46,.25);">
  <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-bottom:6px;letter-spacing:.05em;">
    BELASTINGRENTE VPB
  </div>
  <div style="font-size:36px;font-weight:bold;font-family:monospace;">
    {nl_euro(totaal_rente)}
  </div>
</div>
""")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Renteperiode</div>
      <div class="value" style="font-size:14px;">{nl_date(r_start)} t/m {nl_date(r_eind)}</div>
      <div class="sub">{totaal_dagen} dagen</div>
    </div>""", unsafe_allow_html=True)

with col2:
    uniq_tarieven = sorted({d["pct"] for d in deelperioden})
    tarief_txt = " / ".join(f"{p:.0f}%" for p in uniq_tarieven)
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Rentetarief (per jaar)</div>
      <div class="value">{tarief_txt}</div>
      <div class="sub">Enkelvoudig, 365 dagen</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Aangeslagen bedrag</div>
      <div class="value" style="font-size:16px;">{nl_euro(bedrag)}</div>
      <div class="sub">Boekjaar t/m {nl_date(boekjaar_eind)}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("**Berekening per periode**")
for d in deelperioden:
    st.markdown(f"""
    <div class="bk-tile" style="margin-bottom:6px">
      <div class="label">{nl_date(d['start'])} t/m {nl_date(d['eind'])} &nbsp;·&nbsp; {d['pct']:.2g}% &nbsp;·&nbsp; {d['dagen']} dagen</div>
      <div class="value">{nl_euro(d['rente'])}</div>
    </div>""", unsafe_allow_html=True)

st.caption(
    "Tarieven op basis van belastingdienst.nl (bijgewerkt 2 juli 2026). "
    "Controleer periodiek of er nieuwe percentages zijn gepubliceerd."
)
