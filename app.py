import streamlit as st
import requests
from datetime import date

st.set_page_config(
    page_title="Betalingskenmerk — Bouwman Tools",
    page_icon="🏦",
    layout="centered",
)

# ── Decoding logic ──────────────────────────────────────────────────────────

MAANDEN = [
    "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
]

MIDDEL_LABEL = {
    0: {"kort": "LH",  "lang": "Loonheffing",    "sub": "Naheffingsaanslag"},
    1: {"kort": "OB",  "lang": "Omzetbelasting",  "sub": "Aangifte"},
    5: {"kort": "OB",  "lang": "Omzetbelasting",  "sub": "Naheffingsaanslag"},
    6: {"kort": "LH",  "lang": "Loonheffing",     "sub": "Aangifte"},
}

MIDDEL2_LABEL = {
    70: {"kort": "IB",  "lang": "Inkomstenbelasting"},
    71: {"kort": "IH",  "lang": "Conserverende aanslag IH"},
    73: {"kort": "IB",  "lang": "Inkomstenbelasting (gemoedsbezwaarde)"},
    74: {"kort": "VpB", "lang": "Vennootschapsbelasting"},
    75: {"kort": "ZVW", "lang": "Zorgverzekeringswet"},
    76: {"kort": "HSB", "lang": "Motorrijtuigenbelasting (naheffing)"},
    78: {"kort": "HSB", "lang": "Motorrijtuigenbelasting"},
    85: {"kort": "EVN", "lang": "Eurovignet"},
    86: {"kort": "EVN", "lang": "Eurovignet (naheffing)"},
    87: {"kort": "MOA", "lang": "Motorrijtuigenbelasting vrachtwagens (aangifte)"},
    88: {"kort": "MOA", "lang": "Motorrijtuigenbelasting vrachtwagens (naheffing)"},
    97: {"kort": "LIR", "lang": "Landinrichtingsrente / Verontreinigingsheffing"},
    23: {"kort": "KOT", "lang": "Kinderopvangtoeslag"},
    24: {"kort": "HT",  "lang": "Huurtoeslag"},
    25: {"kort": "ZT",  "lang": "Zorgtoeslag"},
    26: {"kort": "KGB", "lang": "Kindgebonden budget"},
    27: {"kort": "VB",  "lang": "Verzuimboete Toeslagen"},
    28: {"kort": "VGB", "lang": "Vergrijpboete Toeslagen"},
}


def rsin_check_digit(d8: str) -> int:
    weights = [9, 8, 7, 6, 5, 4, 3, 2]
    return sum(int(c) * w for c, w in zip(d8, weights)) % 11


def reconstruct_year(digit: int) -> int:
    current_last = date.today().year % 10
    base = 2020 if digit <= current_last else 2010
    return base + digit


def decode_tijdvak(code: str) -> str:
    n = int(code)
    if n == 0:
        return "Jaaraangifte"
    if 1 <= n <= 12:
        return MAANDEN[n - 1]
    mapping = {21: "1e kwartaal", 24: "2e kwartaal", 27: "3e kwartaal", 30: "4e kwartaal"}
    return mapping.get(n, f"tijdvak {code}")


def format_rsin(rsin9: str) -> str:
    return f"{rsin9[:4]}.{rsin9[4:6]}.{rsin9[6:]}"


def decode_kenmerk(raw: str):
    """Returns (result_dict, error_str). One of them is None."""
    raw = raw.replace(" ", "")
    if not raw.isdigit() or len(raw) != 16:
        return None, "Voer een geldig 16-cijferig betalingskenmerk in."

    p = lambda i: int(raw[i - 1])        # 1-based position
    s = lambda f, t: raw[f - 1:t]        # 1-based slice

    middel10 = p(10)

    if middel10 in (0, 1, 5, 6):
        rsin8 = s(2, 9)
        rsin9 = rsin8 + str(rsin_check_digit(rsin8))
        m = MIDDEL_LABEL[middel10]
        return {
            "soort": m["lang"], "soort_sub": m["sub"], "kort": m["kort"],
            "jaar": reconstruct_year(p(11)),
            "tijdvak": decode_tijdvak(s(14, 15)),
            "rsin": format_rsin(rsin9), "rsin9": rsin9,
            "digit_active": [False,False,False,False,False,False,False,False,False,True,True,False,False,True,True,False],
        }, None

    middel2 = int(s(10, 11))

    if middel2 == 74 or (80 <= middel2 <= 96):
        rsin6 = s(2, 7)
        if middel2 == 74:
            prefix = "00"
        elif middel2 <= 84:
            prefix = str(middel2)
        else:
            prefix = str(middel2 - 7)
        rsin8 = prefix + rsin6
        rsin9 = rsin8 + str(rsin_check_digit(rsin8))
        return {
            "soort": "Vennootschapsbelasting", "soort_sub": "", "kort": "VpB",
            "jaar": reconstruct_year(p(8)),
            "tijdvak": f"Boekjaar {s(12, 15)}",
            "rsin": format_rsin(rsin9), "rsin9": rsin9,
            "digit_active": [False,True,True,True,True,True,True,True,False,True,True,False,False,False,False,False],
        }, None

    if middel2 in MIDDEL2_LABEL:
        rsin8 = s(2, 9)
        rsin9 = rsin8 + str(rsin_check_digit(rsin8))
        m = MIDDEL2_LABEL[middel2]
        return {
            "soort": m["lang"], "soort_sub": "", "kort": m["kort"],
            "jaar": reconstruct_year(p(12)),
            "tijdvak": "—",
            "rsin": format_rsin(rsin9), "rsin9": rsin9,
            "digit_active": [False,True,True,True,True,True,True,True,True,True,True,True,False,False,False,False],
        }, None

    return None, f"Onbekend middelcode ({middel2}). Mogelijk een bijzonder kenmerk dat niet algoritmisch te decoderen is."


def build_omschrijving(r: dict) -> str:
    prefix = "Naheff." if r["soort_sub"] == "Naheffingsaanslag" else "Afdr."
    tv = r["tijdvak"].capitalize()
    return f"{prefix} {r['kort']} {tv} {r['jaar']}"


def render_digit_strip(raw: str, active: list) -> str:
    parts = []
    for i, (digit, on) in enumerate(zip(raw, active)):
        if i in (9, 11, 13):
            parts.append('<span style="color:#aab4cc;display:flex;align-items:center;font-size:18px;padding:0 2px">·</span>')
        bg = "#24304A" if on else "#e8ecf2"
        fg = "white" if on else "#6b7a99"
        parts.append(
            f'<div style="width:28px;height:34px;display:flex;align-items:center;'
            f'justify-content:center;border-radius:6px;font-family:monospace;'
            f'font-size:15px;font-weight:bold;background:{bg};color:{fg};">{digit}</div>'
        )
    return '<div style="display:flex;gap:3px;flex-wrap:wrap;margin-top:4px;">' + "".join(parts) + "</div>"


# ── KvK lookup ──────────────────────────────────────────────────────────────

KVK_API_URL = "https://api.kvk.nl/api/v2/zoeken"


def lookup_naam_kvk(rsin9: str, api_key: str) -> str | None:
    resp = requests.get(
        KVK_API_URL,
        params={"rsin": rsin9, "resultatenPerPagina": 1},
        headers={"apikey": api_key},
        timeout=8,
    )
    if resp.status_code == 401:
        raise ValueError("Ongeldige KvK API-sleutel (401).")
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    items = resp.json().get("resultaten", [])
    return items[0].get("naam") if items else None


# ── UI ──────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: linear-gradient(180deg,#f8fbfd 0%,#eef3f7 100%); }
  .bk-header { background: linear-gradient(135deg,#24304A,#2f3d5d); color: white;
    border-radius: 16px; padding: 18px 22px; margin-bottom: 16px; }
  .bk-header h1 { margin: 0 0 6px; font-size: 26px; color: white; }
  .bk-header p  { margin: 0; font-size: 14px; color: rgba(255,255,255,0.88); line-height: 1.5; }
  .bk-omschrijving { background: white; border-radius: 14px; padding: 16px 20px;
    box-shadow: 0 4px 16px rgba(36,48,74,.08); margin-bottom: 12px; }
  .bk-omschrijving .label { font-size: 12px; color: #6b7a99; font-weight: 600;
    letter-spacing:.03em; margin-bottom: 6px; }
  .bk-omschrijving .value { font-size: 20px; font-weight: bold; color: #24304A;
    font-family: monospace; }
  .bk-tile { background: white; border-radius: 12px; padding: 14px 16px;
    box-shadow: 0 2px 10px rgba(36,48,74,.07); margin-bottom: 8px; }
  .bk-tile .label { font-size: 12px; color: #6b7a99; margin-bottom: 2px; }
  .bk-tile .value { font-size: 18px; font-weight: bold; color: #24304A; }
  .bk-tile .sub   { font-size: 13px; color: #6b7a99; margin-top: 2px; }
  div[data-testid="stCodeBlock"] button { display: inline-flex !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="bk-header">
  <h1>Betalingskenmerk</h1>
  <p>Plak een 16-cijferig betalingskenmerk van de Belastingdienst en zie direct om welk
     belastingmiddel, jaar en tijdvak het gaat.</p>
</div>
""", unsafe_allow_html=True)

# KvK API-sleutel: secrets.toml (lokaal/Streamlit Cloud) heeft prioriteit
try:
    _secret_key = st.secrets.get("kvk_api_key", "")
except Exception:
    _secret_key = ""

if _secret_key:
    # Sleutel komt uit secrets — sidebar niet nodig voor collega's
    st.session_state["kvk_api_key"] = _secret_key
else:
    # Geen secret geconfigureerd: toon invoer in sidebar (ontwikkeling / lokaal)
    with st.sidebar:
        st.markdown("### KvK API-sleutel")
        st.markdown("Voer uw sleutel in om de bedrijfsnaam bij een RSIN op te zoeken.")
        api_key_input = st.text_input(
            "API-sleutel", value=st.session_state.get("kvk_api_key", ""),
            type="password", label_visibility="collapsed"
        )
        if api_key_input:
            st.session_state["kvk_api_key"] = api_key_input
        elif "kvk_api_key" in st.session_state:
            del st.session_state["kvk_api_key"]

# Input
raw_input = st.text_input(
    "Betalingskenmerk",
    placeholder="bijv. 4863521721601050",
    max_chars=19,
    help="Plak of typ het 16-cijferig kenmerk. Spaties worden genegeerd.",
)

if not raw_input:
    st.stop()

raw = raw_input.replace(" ", "")
result, error = decode_kenmerk(raw)

if error:
    st.error(error)
    st.stop()

omschrijving = build_omschrijving(result)

# Omschrijving (st.code geeft ingebouwde kopieerknop)
st.markdown('<div class="bk-omschrijving"><div class="label">Omschrijving voor in uw boekhouding</div></div>', unsafe_allow_html=True)
st.code(omschrijving, language=None)

# Resultaat-tegels
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Soort</div>
      <div class="value">{result['soort']}</div>
      <div class="sub">{result['soort_sub']}</div>
    </div>""", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Tijdvak</div>
      <div class="value">{result['tijdvak'].capitalize()}</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Jaartal</div>
      <div class="value">{result['jaar']}</div>
    </div>""", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">BSN / RSIN</div>
      <div class="value" style="font-family:monospace;font-size:17px;">{result['rsin']}</div>
    </div>""", unsafe_allow_html=True)

# KvK naam
kvk_key = st.session_state.get("kvk_api_key", "")
if kvk_key:
    with st.spinner("Naam opzoeken in KvK…"):
        try:
            naam = lookup_naam_kvk(result["rsin9"], kvk_key)
        except ValueError as e:
            naam = None
            st.warning(str(e))
        except Exception as e:
            naam = None
            st.warning(f"KvK-fout: {e}")

    naam_value = naam if naam else "Niet gevonden in KvK-register (mogelijk BSN van particulier)"
    st.markdown(f"""
    <div class="bk-tile" style="margin-top:0">
      <div class="label">Naam bij RSIN</div>
      <div class="value">{naam_value}</div>
    </div>""", unsafe_allow_html=True)
else:
    st.info("Stel uw KvK API-sleutel in de zijbalk in om de bedrijfsnaam automatisch op te zoeken.")

# Positieweergave
with st.expander("Positieweergave", expanded=False):
    st.markdown(render_digit_strip(raw, result["digit_active"]), unsafe_allow_html=True)
    st.caption("Donkere posities zijn de gedecodeerde velden.")
