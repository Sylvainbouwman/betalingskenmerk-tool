import streamlit as st
import requests
from datetime import date
from fpdf import FPDF
from _auto_paste import auto_paste_input as _auto_paste_input

# ── Bijtelling tarieven ──────────────────────────────────────────────────────
_STD_BIJ = {j: 22.0 for j in range(2017, 2031)}
for j in range(2012, 2017):
    _STD_BIJ[j] = 25.0

_EV_BIJ = {
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
        ts_str = v.get("datum_tenaamstelling", "")
        datum_ts = None
        if len(ts_str) == 8:
            try:
                datum_ts = date(int(ts_str[:4]), int(ts_str[4:6]), int(ts_str[6:8]))
            except (ValueError, TypeError):
                pass
        return {
            "voertuig": (v.get("merk", "") + " " + v.get("handelsbenaming", "")).strip(),
            "bouwjaar": str(v.get("datum_eerste_toelating", ""))[:4],
            "brandstof": brandstof,
            "co2": co2,
            "catalogusprijs": int(cat_str) if cat_str else None,
            "datum_tenaamstelling": datum_ts,
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


def _pdf_bedrag(x: float) -> str:
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"EUR {s}"


def nl_date(d: date) -> str:
    return d.strftime("%d-%m-%Y")


def _maak_pdf(kenteken, auto, klant_naam, klant_nr, jaar, periode_label, dagen,
              marge, catalogusprijs, btw, bij, bij_label) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(25, 20, 25)
    pdf.set_auto_page_break(auto=True, margin=20)

    # Header balk
    pdf.set_fill_color(36, 48, 74)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 11, "BTW-correctie en bijtelling zakelijke auto", fill=True,
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    def _rij(label: str, waarde: str):
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(50, 6, label)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, waarde, new_x="LMARGIN", new_y="NEXT")

    def _sectie(titel: str):
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(36, 48, 74)
        pdf.cell(0, 7, titel, new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(200, 210, 225)
        pdf.line(25, pdf.get_y(), 185, pdf.get_y())
        pdf.ln(2)

    # Klantgegevens
    if klant_naam or klant_nr:
        _sectie("Klantgegevens")
        if klant_naam:
            _rij("Naam:", klant_naam)
        if klant_nr:
            _rij("Klantnummer:", klant_nr)

    # Voertuig
    _sectie("Voertuig")
    _rij("Kenteken:", kenteken)
    _rij("Voertuig:", f"{auto['voertuig']} ({auto['bouwjaar']})")
    _rij("Brandstof:", auto["brandstof"])
    co2_txt = f"{auto['co2']} g/km" if auto["co2"] is not None else "Onbekend"
    _rij("CO2-uitstoot:", co2_txt)
    _rij("Catalogusprijs:", _pdf_bedrag(catalogusprijs))

    # Berekening
    _sectie("Berekening")
    _rij("Berekeningsjaar:", str(jaar))
    _rij("Periode:", f"{periode_label} ({dagen} dagen)")
    _rij("BTW-tarief:", "1,5% (marge-auto)" if marge else "2,7%")

    # Resultaten
    _sectie("Resultaten")
    pdf.ln(1)

    # BTW-correctie blok
    pdf.set_fill_color(230, 238, 255)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, "BTW-correctie privégebruik (forfaitmethode art. 4 lid 2 Wet OB)",
             fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 58, 110)
    pdf.cell(0, 10, _pdf_bedrag(btw), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Bijtelling blok
    pdf.set_fill_color(225, 245, 232)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Bijtelling fiscale waarde ({bij_label})",
             fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 77, 46)
    pdf.cell(0, 10, _pdf_bedrag(bij), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Footer
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, f"Gegenereerd op {date.today().strftime('%d-%m-%Y')} via belastingtooljoindk.streamlit.app",
             new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 5,
        "Berekening op basis van forfaitmethode. Voertuiggegevens via RDW Open Data. "
        "Dit document is indicatief en vervangt geen fiscaal advies.")

    return bytes(pdf.output())


# ── Opmaak ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: linear-gradient(180deg,#f8fbfd 0%,#eef3f7 100%); }
  .bk-header { background: linear-gradient(135deg,#24304A,#2f3d5d); color: white;
    border-radius: 12px; padding: 12px 18px; margin-bottom: 12px; }
  .bk-header h1 { margin: 0 0 3px; font-size: 22px; color: white; }
  .bk-header p  { margin: 0; font-size: 13px; color: rgba(255,255,255,0.82); }
  .bk-tile { background: white; border-radius: 10px; padding: 12px 14px;
    box-shadow: 0 2px 10px rgba(36,48,74,.07); margin-bottom: 8px; }
  .bk-tile .label { font-size: 11px; color: #6b7a99; margin-bottom: 2px; }
  .bk-tile .value { font-size: 17px; font-weight: bold; color: #24304A; }
  .bk-tile .sub   { font-size: 12px; color: #6b7a99; margin-top: 1px; }
  .auto-info { background: white; border-radius: 8px; padding: 8px 14px;
    font-size: 13px; color: #24304A; box-shadow: 0 1px 6px rgba(36,48,74,.07);
    margin-bottom: 10px; }
  .auto-info b { color: #1a3a6e; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="bk-header">
  <h1>🚗 Auto BTW privé</h1>
  <p>BTW-correctie en bijtelling voor privégebruik zakelijke auto — forfaitmethode, RDW-koppeling.</p>
</div>
""", unsafe_allow_html=True)

# ── Invoer: kenteken + klantgegevens ────────────────────────────────────────
col_k, col_n, col_nr = st.columns([1.2, 1.5, 1])

with col_k:
    if "kenteken_norm" not in st.session_state:
        st.session_state["kenteken_norm"] = ""
    st.markdown('<p style="font-size:13px;font-weight:600;color:#31333F;margin-bottom:3px;">Kenteken</p>', unsafe_allow_html=True)
    _kent_val = _auto_paste_input(
        value=st.session_state["kenteken_norm"],
        pattern=r"^[A-Z0-9]{6}$",
        placeholder="bijv. TH-992-G",
        key="kenteken_comp",
        default=None,
    )
    if _kent_val is not None:
        st.session_state["kenteken_norm"] = _kent_val

with col_n:
    klant_naam = st.text_input("Klantnaam", key="klant_naam", placeholder="Optioneel — voor de PDF")

with col_nr:
    klant_nr = st.text_input("Klantnummer", key="klant_nr", placeholder="bijv. 12345")

kenteken_norm = st.session_state["kenteken_norm"]
auto_data = None

if len(kenteken_norm) == 6:
    with st.spinner("RDW ophalen…"):
        auto_data = _rdw_ophalen(kenteken_norm)
    if auto_data is None:
        st.error(f"Kenteken **{kenteken_norm}** niet gevonden in het RDW.")
elif len(kenteken_norm) > 0:
    st.caption(f"{len(kenteken_norm)}/6 tekens — voer een geldig kenteken in.")

if auto_data is None:
    st.stop()

# ── Compacte auto-info ────────────────────────────────────────────────────────
co2_txt = f"{auto_data['co2']} g/km" if auto_data["co2"] is not None else "CO₂ onbekend"
cat_txt = nl_euro(auto_data["catalogusprijs"]) if auto_data["catalogusprijs"] else "—"
ts = auto_data["datum_tenaamstelling"]
ts_txt = f"In gebruik vanaf {nl_date(ts)}" if ts else ""
st.markdown(
    f'<div class="auto-info">'
    f'<b>{kenteken_norm}</b> &nbsp;·&nbsp; {auto_data["voertuig"]} &nbsp;·&nbsp; '
    f'Bouwjaar {auto_data["bouwjaar"]} &nbsp;·&nbsp; {auto_data["brandstof"]} &nbsp;·&nbsp; '
    f'{co2_txt} &nbsp;·&nbsp; Catalogusprijs {cat_txt}'
    + (f' &nbsp;·&nbsp; <span style="color:#1a4d2e;font-weight:600;">{ts_txt}</span>' if ts_txt else '')
    + f'</div>',
    unsafe_allow_html=True,
)

# Handmatig invullen als RDW geen catalogusprijs heeft
catalogusprijs = float(auto_data["catalogusprijs"]) if auto_data["catalogusprijs"] else None
if catalogusprijs is None:
    st.warning("Catalogusprijs niet gevonden in het RDW — vul handmatig in.")
    cat_handmatig = st.number_input("Catalogusprijs (€, incl. BTW en BPM)", min_value=0, value=0, step=500)
    if cat_handmatig == 0:
        st.stop()
    catalogusprijs = float(cat_handmatig)

# ── Berekeningsinvoer (compact, één rij) ────────────────────────────────────
huidig_jaar = date.today().year
col_a, col_b, col_c = st.columns([1, 1, 2])

with col_a:
    berekeningsjaar = st.selectbox(
        "Berekeningsjaar",
        options=list(range(huidig_jaar, huidig_jaar - 8, -1)),
        index=0,
    )
with col_b:
    marge = st.toggle(
        "Marge-auto (1,5%)",
        value=False,
        help="Vink aan als de auto als marge-auto is gekocht (zonder BTW-factuur).",
    )
with col_c:
    # Slimme default: tenaamstelling in dit jaar → gebruik als startdatum
    if ts and ts.year == berekeningsjaar:
        default_van = ts
    else:
        default_van = date(berekeningsjaar, 1, 1)
    default_tot = date(berekeningsjaar, 12, 31)

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        datum_van = st.date_input(
            "Van",
            value=default_van,
            min_value=date(berekeningsjaar, 1, 1),
            max_value=date(berekeningsjaar, 12, 31),
            format="DD-MM-YYYY",
            key=f"datum_van_{kenteken_norm}_{berekeningsjaar}",
        )
    with col_d2:
        datum_tot = st.date_input(
            "Tot en met",
            value=default_tot,
            min_value=date(berekeningsjaar, 1, 1),
            max_value=date(berekeningsjaar, 12, 31),
            format="DD-MM-YYYY",
            key=f"datum_tot_{kenteken_norm}_{berekeningsjaar}",
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

# ── Resultaten ────────────────────────────────────────────────────────────────
col_r1, col_r2 = st.columns(2)
with col_r1:
    st.html(f"""
    <div style="background:linear-gradient(135deg,#1a3a6e,#1e4680);color:white;
      border-radius:12px;padding:16px 20px;text-align:center;
      box-shadow:0 4px 14px rgba(26,58,110,.22);">
      <div style="font-size:11px;color:rgba(255,255,255,0.8);margin-bottom:4px;letter-spacing:.06em;">
        BTW-CORRECTIE PRIVÉGEBRUIK
      </div>
      <div style="font-size:32px;font-weight:bold;font-family:monospace;">{nl_euro(btw)}</div>
      <div style="font-size:11px;color:rgba(255,255,255,0.7);margin-top:4px;">
        {tarief_str} forfait &nbsp;·&nbsp; {dagen} dagen
      </div>
    </div>""")
with col_r2:
    st.html(f"""
    <div style="background:linear-gradient(135deg,#1a4d2e,#1e5c36);color:white;
      border-radius:12px;padding:16px 20px;text-align:center;
      box-shadow:0 4px 14px rgba(26,77,46,.22);">
      <div style="font-size:11px;color:rgba(255,255,255,0.8);margin-bottom:4px;letter-spacing:.06em;">
        BIJTELLING (FISCALE WAARDE)
      </div>
      <div style="font-size:32px;font-weight:bold;font-family:monospace;">{nl_euro(bij)}</div>
      <div style="font-size:11px;color:rgba(255,255,255,0.7);margin-top:4px;">
        {bij_label} &nbsp;·&nbsp; {dagen} dagen
      </div>
    </div>""")

# ── PDF download ──────────────────────────────────────────────────────────────
bestandsnaam = f"BTW_auto_{kenteken_norm}_{berekeningsjaar}.pdf"

if st.button("📄 Genereer PDF", use_container_width=True):
    try:
        pdf_bytes = _maak_pdf(
            kenteken=kenteken_norm,
            auto=auto_data,
            klant_naam=klant_naam,
            klant_nr=klant_nr,
            jaar=berekeningsjaar,
            periode_label=periode_label,
            dagen=dagen,
            marge=marge,
            catalogusprijs=catalogusprijs,
            btw=btw,
            bij=bij,
            bij_label=bij_label,
        )
        st.session_state["pdf_bytes"] = pdf_bytes
        st.session_state["pdf_naam"] = bestandsnaam
    except Exception as e:
        st.error(f"PDF genereren mislukt: {e}")

if "pdf_bytes" in st.session_state and st.session_state.get("pdf_naam") == bestandsnaam:
    st.download_button(
        label="📥 Download PDF",
        data=st.session_state["pdf_bytes"],
        file_name=bestandsnaam,
        mime="application/pdf",
        use_container_width=True,
    )

st.caption(
    "Forfaitmethode art. 4 lid 2 Wet OB · Voertuiggegevens via RDW Open Data · "
    "Toekomstig: opslaan in AFAS-dossier."
)
