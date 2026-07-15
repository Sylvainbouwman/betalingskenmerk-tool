import streamlit as st
import requests

KVK_ZOEKEN_URL = "https://api.kvk.nl/api/v2/zoeken"

# ── KvK API-sleutel ──────────────────────────────────────────────────────────

try:
    _secret_key = st.secrets.get("kvk_api_key", "")
except Exception:
    _secret_key = ""

if _secret_key:
    st.session_state["kvk_api_key"] = _secret_key
else:
    with st.sidebar:
        st.markdown("### KvK API-sleutel")
        api_key_input = st.text_input(
            "API-sleutel", value=st.session_state.get("kvk_api_key", ""),
            type="password", label_visibility="collapsed"
        )
        if api_key_input:
            st.session_state["kvk_api_key"] = api_key_input
        elif "kvk_api_key" in st.session_state:
            del st.session_state["kvk_api_key"]

# ── Lookup functies ───────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def zoek_bedrijf(zoekterm: str, api_key: str) -> list:
    """Zoek op naam, KvK-nummer of RSIN. Geeft lijst van resultaten."""
    zoekterm = zoekterm.strip()
    if zoekterm.isdigit() and len(zoekterm) == 9:
        param = {"rsin": zoekterm}
    elif zoekterm.isdigit():
        param = {"kvkNummer": zoekterm}
    else:
        param = {"naam": zoekterm}
    param["resultatenPerPagina"] = 10
    resp = requests.get(KVK_ZOEKEN_URL, params=param, headers={"apikey": api_key}, timeout=8)
    if resp.status_code == 401:
        raise ValueError("Ongeldige of verlopen KvK API-sleutel (401).")
    if not resp.ok:
        raise ValueError(f"KvK fout {resp.status_code}: {resp.text[:200]}")
    return resp.json().get("resultaten", [])


@st.cache_data(ttl=3600)
def haal_sbi(href: str, api_key: str) -> list:
    try:
        r = requests.get(href, headers={"apikey": api_key}, timeout=8)
        return r.json().get("sbiActiviteiten", []) if r.ok else []
    except Exception:
        return []

# ── Stijl ─────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: linear-gradient(180deg,#f8fbfd 0%,#eef3f7 100%); }
  .sbi-header { background: linear-gradient(135deg,#24304A,#2f3d5d); color: white;
    border-radius: 16px; padding: 18px 22px; margin-bottom: 16px; }
  .sbi-header h1 { margin: 0 0 6px; font-size: 26px; color: white; }
  .sbi-header p  { margin: 0; font-size: 14px; color: rgba(255,255,255,0.88); line-height: 1.5; }
  .sbi-tile { background: white; border-radius: 12px; padding: 14px 16px;
    box-shadow: 0 2px 10px rgba(36,48,74,.07); margin-bottom: 8px; }
  .sbi-tile .label { font-size: 12px; color: #6b7a99; margin-bottom: 2px; }
  .sbi-tile .value { font-size: 18px; font-weight: bold; color: #24304A; }
  .sbi-tile .sub   { font-size: 13px; color: #6b7a99; margin-top: 2px; }
  .sbi-badge { display:inline-block; background:#24304A; color:white;
    border-radius:6px; padding:3px 10px; font-size:13px; font-weight:bold;
    font-family:monospace; margin-right:6px; }
  .sbi-badge-neven { background:#6b7a99; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="sbi-header">
  <h1>KvK / SBI opzoeken</h1>
  <p>Zoek op bedrijfsnaam, KvK-nummer of RSIN en zie direct de SBI-activiteitencode(s).</p>
</div>
""", unsafe_allow_html=True)

# ── Invoer ────────────────────────────────────────────────────────────────────

kvk_key = st.session_state.get("kvk_api_key", "")

if not kvk_key:
    st.info("Stel uw KvK API-sleutel in via de zijbalk om bedrijven op te zoeken.")
    st.stop()

col_in, col_knop = st.columns([3, 1])
with col_in:
    zoekterm = st.text_input(
        "Zoeken",
        placeholder="Bedrijfsnaam, KvK-nummer (8 cijfers) of RSIN (9 cijfers)",
        label_visibility="collapsed",
    )
with col_knop:
    zoeken = st.button("Zoeken →", use_container_width=True)

if not zoekterm:
    st.caption("Typ een naam om op te zoeken, of plak een KvK-nummer of RSIN.")
    st.stop()

# ── Resultaten ────────────────────────────────────────────────────────────────

try:
    resultaten = zoek_bedrijf(zoekterm, kvk_key)
except ValueError as e:
    st.error(str(e))
    st.stop()

if not resultaten:
    st.warning("Geen resultaten gevonden. Controleer de spelling of probeer een KvK-nummer.")
    st.stop()

st.caption(f"{len(resultaten)} resultaat{'en' if len(resultaten) != 1 else ''} gevonden")

for res in resultaten:
    naam     = res.get("naam", "—")
    kvk_nr   = res.get("kvkNummer", "")
    rsin     = res.get("rsin", "")
    adres    = res.get("adres", {}).get("binnenlandsAdres", {})
    plaats   = adres.get("plaats", "")
    href     = next((l["href"] for l in res.get("links", []) if l["rel"] == "basisprofiel"), None)

    with st.expander(f"**{naam}** — KvK {kvk_nr}  ·  {plaats}", expanded=len(resultaten) == 1):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="sbi-tile">
              <div class="label">Bedrijfsnaam</div>
              <div class="value" style="font-size:16px;">{naam}</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="sbi-tile">
              <div class="label">KvK-nummer · RSIN</div>
              <div class="value" style="font-size:16px;font-family:monospace;">{kvk_nr}</div>
              <div class="sub">{rsin}</div>
            </div>""", unsafe_allow_html=True)

        if href:
            sbi_codes = haal_sbi(href, kvk_key)
            if sbi_codes:
                hoofd = [s for s in sbi_codes if s.get("indHoofdactiviteit") == "Ja"]
                neven = [s for s in sbi_codes if s.get("indHoofdactiviteit") != "Ja"]

                badges_hoofd = "".join(
                    f'<span class="sbi-badge">{s["sbiCode"]}</span> {s["sbiOmschrijving"]}<br>'
                    for s in hoofd
                )
                badges_neven = "".join(
                    f'<span class="sbi-badge sbi-badge-neven">{s["sbiCode"]}</span> {s["sbiOmschrijving"]}<br>'
                    for s in neven
                ) if neven else ""

                st.markdown(f"""
                <div class="sbi-tile">
                  <div class="label">Hoofdactiviteit</div>
                  <div style="margin-top:6px;font-size:15px;line-height:2;">{badges_hoofd or "—"}</div>
                  {f'<div class="label" style="margin-top:10px;">Nevenactiviteit</div><div style="margin-top:6px;font-size:15px;line-height:2;">{badges_neven}</div>' if badges_neven else ''}
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="sbi-tile">
                  <div class="label">SBI-code</div>
                  <div class="sub" style="margin-top:4px;">Tijdelijk niet beschikbaar (KvK verwerkt de gegevens)</div>
                </div>""", unsafe_allow_html=True)

st.caption("Bron: KvK Handelsregister API")
