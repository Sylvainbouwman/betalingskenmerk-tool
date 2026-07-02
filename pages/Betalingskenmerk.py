import streamlit as st
import requests
from datetime import date
from _auto_paste import auto_paste_input as _auto_paste_input

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

    p = lambda i: int(raw[i - 1])
    s = lambda f, t: raw[f - 1:t]

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


@st.cache_data(ttl=3600)
def lookup_naam_kvk(rsin9: str, api_key: str) -> str | None:
    resp = requests.get(
        KVK_API_URL,
        params={"rsin": rsin9, "resultatenPerPagina": 1},
        headers={"apikey": api_key},
        timeout=4,
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

# KvK API-sleutel
try:
    _secret_key = st.secrets.get("kvk_api_key", "")
except Exception:
    _secret_key = ""

if _secret_key:
    st.session_state["kvk_api_key"] = _secret_key
else:
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

# Input — eigen component: paste triggert direct rerun zonder klik
st.markdown('<p style="font-size:14px;font-weight:600;color:#31333F;margin-bottom:4px;">Betalingskenmerk</p>', unsafe_allow_html=True)
_comp_value = _auto_paste_input(
    value=st.session_state.get("kenmerk_digits", ""),
    key="kenmerk_comp",
    default=None,
)

if _comp_value is not None:
    st.session_state["kenmerk_digits"] = _comp_value.replace(" ", "")

vertalen = st.button("Vertalen →", use_container_width=True)
digits = st.session_state.get("kenmerk_digits", "")

if vertalen and not digits:
    st.info("Plak eerst een 16-cijferig betalingskenmerk.")
    st.stop()

if not digits:
    st.stop()

raw = digits
result, error = decode_kenmerk(raw)

if error:
    st.error(error)
    st.stop()

omschrijving = build_omschrijving(result)

st.html(f"""
<div style="background:white;border-radius:14px;padding:16px 20px;
  box-shadow:0 4px 16px rgba(36,48,74,.08);font-family:Arial,sans-serif;">
  <div style="font-size:12px;color:#6b7a99;font-weight:600;
    letter-spacing:.03em;margin-bottom:10px;">
    Omschrijving voor in uw boekhouding
  </div>
  <button id="copybtn" onclick="
    var ta = document.createElement('textarea');
    ta.value = '{omschrijving}';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    this.innerHTML = '&#10003;&nbsp;&nbsp;Gekopieerd!';
    this.style.background = '#1a6b3a';
    var btn = this;
    setTimeout(function() {{
      btn.innerHTML = '{omschrijving} <span style=&quot;opacity:.8;font-size:15px&quot;>&#x2398;</span>';
      btn.style.background = '#24304A';
    }}, 1800);
  " style="background:#24304A;color:white;border:none;border-radius:10px;
    padding:11px 18px;font-size:18px;font-weight:bold;cursor:pointer;
    display:inline-flex;align-items:center;gap:10px;
    font-family:Arial,sans-serif;transition:background 0.2s;">
    {omschrijving}
    <span style="opacity:.8;font-size:15px">&#x2398;</span>
  </button>
</div>
""")

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

kvk_key = st.session_state.get("kvk_api_key", "")
rsin9 = result["rsin9"]
pending_key = f"kvk_pending_{rsin9}"

def _naam_tile(waarde: str, loading: bool = False) -> str:
    kleur = "color:#aab4cc;font-style:italic;font-size:15px" if loading else ""
    return f"""
    <div class="bk-tile" style="margin-top:0">
      <div class="label">Naam bij RSIN</div>
      <div class="value" style="{kleur}">{waarde}</div>
    </div>"""

if kvk_key:
    if pending_key in st.session_state:
        del st.session_state[pending_key]
        try:
            naam = lookup_naam_kvk(rsin9, kvk_key)
            naam_value = naam or "Niet gevonden in KvK-register (mogelijk BSN van particulier)"
        except ValueError as e:
            naam_value = f"⚠ {e}"
        except Exception:
            naam_value = "KvK niet bereikbaar"
        st.markdown(_naam_tile(naam_value), unsafe_allow_html=True)
    else:
        st.markdown(_naam_tile("Ophalen…", loading=True), unsafe_allow_html=True)
        st.session_state[pending_key] = True
        st.rerun()
else:
    st.info("Stel uw KvK API-sleutel in de zijbalk in om de bedrijfsnaam automatisch op te zoeken.")

with st.expander("Positieweergave", expanded=False):
    st.markdown(render_digit_strip(raw, result["digit_active"]), unsafe_allow_html=True)
    st.caption("Donkere posities zijn de gedecodeerde velden.")
