import streamlit as st
import requests
from datetime import date
from _auto_paste import auto_paste_input as _auto_paste_input

# ── Bijtelling tarieven ──────────────────────────────────────────────────────
# Standaard (benzine/diesel/hybride, CO2 > 0)
_STD_BIJ = {j: 22.0 for j in range(2017, 2031)}
for j in range(2012, 2017):
    _STD_BIJ[j] = 25.0

# Elektrisch/waterstof (CO2 = 0): laag tarief met cap; daarboven 22%
_EV_BIJ = {
    # jaar: (laag_pct, cap in €)
    2025: (16.0, 30_000),
    2024: (16.0, 30_000),
    2023: (16.0, 30_000),
    2022: (16.0, 35_000),
    2021: (12.0, 40_000),
    2020: (12.0, 45_000),
    2019: (16.0, 50_000),
    2018: (16.0, 50_000),
    2017: ( 7.0, 50_000),
}


def _normaliseer(k: str) -> str:
    return k.replace("-", "").replace(" ", "").upper()


@st.cache_data(show_spinner=False)
def _rdw_ophalen(kn: str) -> dict | None:
    try:
        r = requests.get(
            f"https://opendata.rdw.nl/resource/m9d7-ebf2.json?kenteken={kn}",
            timeout=8,
        )
        if not r.ok or not r.json():
            return None
        v = r.json()[0]

        rb = requests.get(
            f"https://opendata.rdw.nl/resource/8ys7-d773.json?kenteken={kn}",
            timeout=8,
        )
        brandstof, co2 = "Onbekend", None
        if rb.ok and rb.json():
            b = rb.json()[0]
            brandstof = b.get("brandstof_omschrijving", "Onbekend")
            try:
                co2 = int(float(b["co2_uitstoot_gecombineerd"]))
            except (KeyError, ValueError, TypeError):
                pass

        cat_str = v.get("catalogusprijs")
        return {
            "voertuig": (v.get("merk", "") + " " + v.get("handelsbenaming", "")).strip(),
            "bouwjaar": str(v.get("datum_eerste_toelating", ""))[:4],
            "brandstof": brandstof,
            "co2": co2,
            "catalogusprijs": int(cat_str) if cat_str else None,
        }
    except Exception:
        return None


def _btw_correctie(catalogusprijs: float, marge: bool, dagen: int) -> float:
    return catalogusprijs * (0.015 if marge else 0.027) * (dagen / 365)


def _bijtelling(catalogusprijs: float, co2: int | None, brandstof: str, jaar: int, dagen: int):
    is_ev = (co2 == 0) or brandstof.lower() in ("elektriciteit", "waterstof")
    if is_ev and jaar in _EV_BIJ:
        pct, cap = _EV_BIJ[jaar]
        if catalogusprijs <= cap:
            bedrag = catalogusprijs * (pct / 100) * (dagen / 365)
            label = f"{pct:.0f}% (0-emissie, ≤ € {cap:,})"
        else:
            bedrag = (cap * (pct / 100) + (catalogusprijs - cap) * 0.22) * (dagen / 365)
            label = f"{pct:.0f}% t/m € {cap:,} + 22% daarboven"
    else:
        pct = _STD_BIJ.get(jaar, 22.0)
        bedrag = catalogusprijs * (pct / 100) * (dagen / 365)
        label = f"{pct:.0f}%"
    return bedrag, label


def nl_euro(x: float) -> str:
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"€ {s}"


def nl_date(d: date) -> str:
    return d.strftime("%d-%m-%Y")


# ── Opmaak ───────────────────────────────────────────────────────────────────
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
  <h1>Auto BTW privé</h1>
  <p>Berekent de BTW-correctie en bijtelling voor privégebruik van een zakelijke auto (forfaitmethode).
     Vul het kenteken in voor automatische opzoekservice via het RDW kentekenregister.</p>
</div>
""", unsafe_allow_html=True)

# ── Kenteken ──────────────────────────────────────────────────────────────────
if "kenteken_norm" not in st.session_state:
    st.session_state["kenteken_norm"] = ""

st.markdown('<p style="font-size:14px;font-weight:600;color:#31333F;margin-bottom:4px;">Kenteken</p>', unsafe_allow_html=True)
_kent_val = _auto_paste_input(
    value=st.session_state["kenteken_norm"],
    pattern=r"^[A-Z0-9]{6}$",
    placeholder="Plak of typ het kenteken hier…",
    key="kenteken_comp",
    default=None,
)
if _kent_val is not None:
    st.session_state["kenteken_norm"] = _kent_val

kenteken_norm = st.session_state["kenteken_norm"]
auto_data = None

if len(kenteken_norm) == 6:
    with st.spinner("RDW gegevens ophalen…"):
        auto_data = _rdw_ophalen(kenteken_norm)
    if auto_data is None:
        st.error(f"Kenteken **{kenteken_norm}** niet gevonden in het RDW.")
elif len(kenteken_norm) > 0:
    st.caption(f"{len(kenteken_norm)}/6 tekens — voer een geldig kenteken in.")

if auto_data is None:
    st.stop()

# ── Auto-informatie ───────────────────────────────────────────────────────────
co2_txt = f"{auto_data['co2']} g/km" if auto_data['co2'] is not None else "Onbekend"
cat_txt = nl_euro(auto_data['catalogusprijs']) if auto_data['catalogusprijs'] else "—"

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Voertuig</div>
      <div class="value" style="font-size:15px;">{auto_data['voertuig']}</div>
      <div class="sub">Bouwjaar {auto_data['bouwjaar']}</div>
    </div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Brandstof</div>
      <div class="value" style="font-size:15px;">{auto_data['brandstof']}</div>
      <div class="sub">CO₂ {co2_txt}</div>
    </div>""", unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Catalogusprijs (RDW)</div>
      <div class="value" style="font-size:15px;">{cat_txt}</div>
      <div class="sub">incl. BTW en BPM</div>
    </div>""", unsafe_allow_html=True)
with col4:
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Kenteken</div>
      <div class="value" style="font-size:15px;">{kenteken_norm}</div>
      <div class="sub">&nbsp;</div>
    </div>""", unsafe_allow_html=True)

# Handmatig invullen als RDW geen catalogusprijs heeft
catalogusprijs = float(auto_data["catalogusprijs"]) if auto_data["catalogusprijs"] else None
if catalogusprijs is None:
    st.warning("Catalogusprijs niet gevonden in het RDW. Vul deze handmatig in.")
    cat_handmatig = st.number_input(
        "Catalogusprijs (€, incl. BTW en BPM)",
        min_value=0,
        value=0,
        step=500,
    )
    if cat_handmatig == 0:
        st.stop()
    catalogusprijs = float(cat_handmatig)

# ── Berekening invoer ────────────────────────────────────────────────────────
st.divider()

huidig_jaar = date.today().year
col_a, col_b = st.columns(2)
with col_a:
    berekeningsjaar = st.selectbox(
        "Berekeningsjaar",
        options=list(range(huidig_jaar, huidig_jaar - 8, -1)),
        index=0,
    )
with col_b:
    marge = st.toggle(
        "Marge-auto",
        value=False,
        help="Vink aan als de auto als marge-auto is gekocht (zonder BTW-factuur). Tarief wordt 1,5% in plaats van 2,7%.",
    )

periode_keuze = st.radio(
    "Periode",
    options=["Volledig jaar (365 dagen)", "Eigen periode"],
    horizontal=True,
)

if periode_keuze == "Volledig jaar (365 dagen)":
    dagen = 365
    periode_label = f"1-1-{berekeningsjaar} t/m 31-12-{berekeningsjaar}"
else:
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        datum_van = st.date_input(
            "Van",
            value=date(berekeningsjaar, 1, 1),
            min_value=date(berekeningsjaar, 1, 1),
            max_value=date(berekeningsjaar, 12, 31),
            format="DD-MM-YYYY",
        )
    with col_d2:
        datum_tot = st.date_input(
            "Tot en met",
            value=date(berekeningsjaar, 12, 31),
            min_value=date(berekeningsjaar, 1, 1),
            max_value=date(berekeningsjaar, 12, 31),
            format="DD-MM-YYYY",
        )
    if datum_tot < datum_van:
        st.error("Einddatum moet na de begindatum liggen.")
        st.stop()
    dagen = (datum_tot - datum_van).days + 1
    periode_label = f"{nl_date(datum_van)} t/m {nl_date(datum_tot)}"

# ── Berekening ───────────────────────────────────────────────────────────────
btw = _btw_correctie(catalogusprijs, marge, dagen)
bij, bij_label = _bijtelling(catalogusprijs, auto_data["co2"], auto_data["brandstof"], berekeningsjaar, dagen)
tarief_str = "1,5%" if marge else "2,7%"

# ── Uitvoer ───────────────────────────────────────────────────────────────────
col_r1, col_r2 = st.columns(2)
with col_r1:
    st.html(f"""
    <div style="background:linear-gradient(135deg,#1a3a6e,#1e4680);color:white;
      border-radius:14px;padding:20px 22px;text-align:center;
      box-shadow:0 4px 16px rgba(26,58,110,.25);">
      <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-bottom:6px;letter-spacing:.05em;">
        BTW-CORRECTIE PRIVÉGEBRUIK
      </div>
      <div style="font-size:36px;font-weight:bold;font-family:monospace;">
        {nl_euro(btw)}
      </div>
      <div style="font-size:12px;color:rgba(255,255,255,0.7);margin-top:6px;">
        {tarief_str} forfait &nbsp;·&nbsp; {dagen} dagen
      </div>
    </div>
    """)
with col_r2:
    st.html(f"""
    <div style="background:linear-gradient(135deg,#1a4d2e,#1e5c36);color:white;
      border-radius:14px;padding:20px 22px;text-align:center;
      box-shadow:0 4px 16px rgba(26,77,46,.25);">
      <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-bottom:6px;letter-spacing:.05em;">
        BIJTELLING (FISCALE WAARDE)
      </div>
      <div style="font-size:36px;font-weight:bold;font-family:monospace;">
        {nl_euro(bij)}
      </div>
      <div style="font-size:12px;color:rgba(255,255,255,0.7);margin-top:6px;">
        {bij_label} &nbsp;·&nbsp; {dagen} dagen
      </div>
    </div>
    """)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Catalogusprijs (grondslag)</div>
      <div class="value">{nl_euro(catalogusprijs)}</div>
      <div class="sub">incl. BTW en BPM</div>
    </div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">BTW-tarief forfait</div>
      <div class="value">{tarief_str}</div>
      <div class="sub">{'Marge-auto (zonder BTW)' if marge else 'BTW afgetrokken bij aankoop'}</div>
    </div>""", unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Periode</div>
      <div class="value" style="font-size:14px;">{periode_label}</div>
      <div class="sub">{dagen} dag{'en' if dagen != 1 else ''}</div>
    </div>""", unsafe_allow_html=True)

st.caption(
    "BTW-correctie: forfaitmethode art. 4 lid 2 Wet OB (2,7% of 1,5% van catalogusprijs). "
    "Bijtelling: fiscale toevoeging aan box 1 / loon voor privégebruik auto van de zaak. "
    "Voertuiggegevens via RDW Open Data (opendata.rdw.nl) — geen API-sleutel vereist."
)
