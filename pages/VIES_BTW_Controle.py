import streamlit as st
import requests
import re

EU_LANDEN = [
    "AT","BE","BG","CY","CZ","DE","DK","EE","EL","ES","FI","FR",
    "HR","HU","IE","IT","LT","LU","LV","MT","NL","PL","PT","RO",
    "SE","SI","SK","XI",
]

LAND_NAAM = {
    "AT":"Oostenrijk","BE":"België","BG":"Bulgarije","CY":"Cyprus",
    "CZ":"Tsjechië","DE":"Duitsland","DK":"Denemarken","EE":"Estland",
    "EL":"Griekenland","ES":"Spanje","FI":"Finland","FR":"Frankrijk",
    "HR":"Kroatië","HU":"Hongarije","IE":"Ierland","IT":"Italië",
    "LT":"Litouwen","LU":"Luxemburg","LV":"Letland","MT":"Malta",
    "NL":"Nederland","PL":"Polen","PT":"Portugal","RO":"Roemenië",
    "SE":"Zweden","SI":"Slovenië","SK":"Slowakije","XI":"Noord-Ierland",
}

VIES_URL = "https://ec.europa.eu/taxation_customs/vies/rest-api/ms/{land}/vat/{nummer}"


def parse_btw(raw: str):
    """Geeft (landcode, nummer) terug, of (None, None) bij ongeldige invoer."""
    s = re.sub(r"[\s\.\-]", "", raw).upper()
    if len(s) >= 2 and s[:2].isalpha() and s[:2] in EU_LANDEN:
        return s[:2], s[2:]
    return None, None


@st.cache_data(ttl=3600)
def vies_check(land: str, nummer: str) -> dict:
    try:
        r = requests.get(VIES_URL.format(land=land, nummer=nummer), timeout=8)
        if not r.ok:
            return {"fout": f"VIES niet bereikbaar ({r.status_code})"}
        return r.json()
    except Exception as e:
        return {"fout": f"Verbindingsfout: {e}"}


def adres_regels(adres_str: str) -> list[str]:
    return [r.strip() for r in adres_str.strip().splitlines() if r.strip()]


# ── Stijl ────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: linear-gradient(180deg,#f8fbfd 0%,#eef3f7 100%); }
  .vies-header { background: linear-gradient(135deg,#24304A,#2f3d5d); color: white;
    border-radius: 16px; padding: 18px 22px; margin-bottom: 16px; }
  .vies-header h1 { margin: 0 0 6px; font-size: 26px; color: white; }
  .vies-header p  { margin: 0; font-size: 14px; color: rgba(255,255,255,0.88); line-height: 1.5; }
  .vies-tile { background: white; border-radius: 12px; padding: 14px 16px;
    box-shadow: 0 2px 10px rgba(36,48,74,.07); margin-bottom: 8px; }
  .vies-tile .label { font-size: 12px; color: #6b7a99; margin-bottom: 2px; }
  .vies-tile .value { font-size: 18px; font-weight: bold; color: #24304A; }
  .vies-tile .sub   { font-size: 13px; color: #6b7a99; margin-top: 2px; }
  .badge-geldig   { display:inline-block; background:#1a6b3a; color:white;
    border-radius:8px; padding:4px 14px; font-size:15px; font-weight:bold; }
  .badge-ongeldig { display:inline-block; background:#c0392b; color:white;
    border-radius:8px; padding:4px 14px; font-size:15px; font-weight:bold; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="vies-header">
  <h1>VIES BTW-controle</h1>
  <p>Controleer of een Europees BTW-nummer geldig is en haal de bijbehorende
     bedrijfsnaam en het adres op via de officiële EU VIES-database.</p>
</div>
""", unsafe_allow_html=True)

# ── Invoer ───────────────────────────────────────────────────────────────────

col_in, col_knop = st.columns([3, 1])
with col_in:
    raw = st.text_input(
        "BTW-nummer",
        placeholder="bijv. NL820646660B01 of BE0123456789",
        label_visibility="collapsed",
    )
with col_knop:
    controleer = st.button("Controleer →", use_container_width=True)

if not raw:
    st.caption("Voer een BTW-nummer in met landcode (bijv. NL, DE, BE). "
               "Spaties en punten worden automatisch verwijderd.")
    st.stop()

land, nummer = parse_btw(raw)

if land is None:
    st.error("Ongeldige invoer — begin met een geldige EU-landcode (bijv. NL, DE, BE, FR).")
    st.stop()

# ── API-aanroep ──────────────────────────────────────────────────────────────

with st.spinner("VIES raadplegen…"):
    data = vies_check(land, nummer)

if "fout" in data:
    st.error(f"VIES niet bereikbaar: {data['fout']}")
    st.stop()

geldig = data.get("isValid", False)
naam   = data.get("name", "---").strip()
adres  = data.get("address", "").strip()

# ── Resultaat ────────────────────────────────────────────────────────────────

badge = '<span class="badge-geldig">✓ Geldig</span>' if geldig else '<span class="badge-ongeldig">✗ Niet geldig</span>'
st.markdown(f"""
<div class="vies-tile" style="margin-bottom:12px;">
  <div class="label">Status</div>
  <div style="margin-top:6px;">{badge}</div>
  <div class="sub" style="margin-top:6px;">{land} {nummer} &nbsp;·&nbsp; {LAND_NAAM.get(land, land)}</div>
</div>
""", unsafe_allow_html=True)

if geldig:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div class="vies-tile">
          <div class="label">Bedrijfsnaam</div>
          <div class="value" style="font-size:16px;">{naam if naam and naam != "---" else "—"}</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        adres_html = "<br>".join(adres_regels(adres)) if adres and adres != "---" else "—"
        st.markdown(f"""
        <div class="vies-tile">
          <div class="label">Adres</div>
          <div class="value" style="font-size:15px;font-weight:normal;line-height:1.5;">{adres_html}</div>
        </div>""", unsafe_allow_html=True)

    # Voor NL: toon het RSIN
    if land == "NL":
        rsin_match = re.match(r"^(\d{9})B\d{2}$", nummer)
        if rsin_match:
            rsin9 = rsin_match.group(1)
            rsin_fmt = f"{rsin9[:4]}.{rsin9[4:6]}.{rsin9[6:]}"
            st.markdown(f"""
            <div class="vies-tile">
              <div class="label">RSIN (afgeleid)</div>
              <div class="value" style="font-family:monospace;font-size:17px;">{rsin_fmt}</div>
              <div class="sub">Correspondeert met het RSIN in een betalingskenmerk</div>
            </div>""", unsafe_allow_html=True)

else:
    st.info("Dit BTW-nummer is niet geregistreerd of niet actief in de VIES-database. "
            "Controleer of het nummer correct is ingevoerd.")

st.caption("Bron: Europese Commissie VIES · Gratis · Geen API-sleutel vereist")
