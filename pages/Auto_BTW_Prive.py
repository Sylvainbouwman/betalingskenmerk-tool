import streamlit as st
import requests
from datetime import date, timedelta
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


def _maak_pdf(auto_results: list, klant_naam: str, klant_nr: str, jaar: int, marge: bool) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(25, 20, 25)
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.set_fill_color(36, 48, 74)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 11, "BTW-correctie en bijtelling zakelijke auto", fill=True,
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    def _rij(label, waarde):
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(50, 6, label)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, waarde, new_x="LMARGIN", new_y="NEXT")

    def _sectie(titel):
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(36, 48, 74)
        pdf.cell(0, 7, titel, new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(200, 210, 225)
        pdf.line(25, pdf.get_y(), 185, pdf.get_y())
        pdf.ln(2)

    if klant_naam or klant_nr:
        _sectie("Klantgegevens")
        if klant_naam:
            _rij("Naam:", klant_naam)
        if klant_nr:
            _rij("Klantnummer:", klant_nr)

    _sectie(f"Berekening {jaar}")
    _rij("BTW-tarief:", "1,5% (marge-auto)" if marge else "2,7%")

    for i, r in enumerate(auto_results):
        label = f"Auto {i + 1}" if len(auto_results) > 1 else "Voertuig"
        _sectie(label)
        _rij("Kenteken:", r["kenteken"])
        _rij("Voertuig:", f"{r['auto']['voertuig']} ({r['auto']['bouwjaar']})")
        _rij("Brandstof:", r["auto"]["brandstof"])
        co2_txt = f"{r['auto']['co2']} g/km" if r["auto"]["co2"] is not None else "Onbekend"
        _rij("CO2-uitstoot:", co2_txt)
        _rij("Catalogusprijs:", _pdf_bedrag(r["catalogusprijs"]))
        _rij("Periode:", f"{r['periode_label']} ({r['dagen']} dagen)")

        pdf.ln(2)
        pdf.set_fill_color(230, 238, 255)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, "BTW-correctie privégebruik", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(26, 58, 110)
        pdf.cell(0, 8, _pdf_bedrag(r["btw"]), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        pdf.set_fill_color(225, 245, 232)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, f"Bijtelling ({r['bij_label']})", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(26, 77, 46)
        pdf.cell(0, 8, _pdf_bedrag(r["bij"]), new_x="LMARGIN", new_y="NEXT")

    if len(auto_results) > 1:
        _sectie("Totaal")
        total_btw = sum(r["btw"] for r in auto_results)
        total_bij = sum(r["bij"] for r in auto_results)
        pdf.ln(1)
        pdf.set_fill_color(220, 232, 255)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, "Totaal BTW-correctie", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(26, 58, 110)
        pdf.cell(0, 8, _pdf_bedrag(total_btw), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        pdf.set_fill_color(210, 240, 220)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, "Totaal bijtelling", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(26, 77, 46)
        pdf.cell(0, 8, _pdf_bedrag(total_bij), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, f"Gegenereerd op {date.today().strftime('%d-%m-%Y')} via belastingtooljoindk.streamlit.app",
             new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 5,
        "Berekening op basis van forfaitmethode (art. 4 lid 2 Wet OB). "
        "Voertuiggegevens via RDW Open Data. Indicatief — geen fiscaal advies.")

    return bytes(pdf.output())


# ── Opmaak ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: linear-gradient(180deg,#f8fbfd 0%,#eef3f7 100%); }
  .bk-header { background: linear-gradient(135deg,#24304A,#2f3d5d); color: white;
    border-radius: 14px; padding: 16px 22px; margin-bottom: 14px; }
  .bk-header h1 { margin: 0 0 4px; font-size: 24px; color: white; }
  .bk-header p  { margin: 0; font-size: 13px; color: rgba(255,255,255,0.85); }
  .auto-info { background: #f0f4f8; border-radius: 8px; padding: 8px 14px;
    font-size: 13px; color: #24304A; margin: 6px 0 10px 0; }
  .auto-info b { color: #1a3a6e; }
  .auto-nr { font-size: 13px; font-weight: 700; color: #6b7a99;
    text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="bk-header">
  <h1>🚗 Auto BTW privé</h1>
  <p>BTW-correctie en bijtelling voor privégebruik zakelijke auto — forfaitmethode, RDW-koppeling.</p>
</div>
""", unsafe_allow_html=True)

# ── Globale instellingen ──────────────────────────────────────────────────────
huidig_jaar = date.today().year
col_a, col_b, col_n, col_nr = st.columns([1, 1, 2, 1])
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
with col_n:
    klant_naam = st.text_input("Klantnaam", key="klant_naam", placeholder="Optioneel — voor de PDF")
with col_nr:
    klant_nr = st.text_input("Klantnummer", key="klant_nr", placeholder="bijv. 12345")

tarief_str = "1,5%" if marge else "2,7%"

# ── Session state: lijst van auto's ─────────────────────────────────────────
if "autos" not in st.session_state:
    st.session_state["autos"] = [{"id": 0, "kenteken": ""}]
if "_next_id" not in st.session_state:
    st.session_state["_next_id"] = 1

n_autos = len(st.session_state["autos"])

# ── Per-auto secties ──────────────────────────────────────────────────────────
auto_results = []

for idx, auto_entry in enumerate(list(st.session_state["autos"])):
    car_id = auto_entry["id"]

    with st.container(border=True):

        # Label + verwijderknop
        hcol1, hcol2 = st.columns([20, 1])
        with hcol1:
            if n_autos > 1:
                st.markdown(f'<div class="auto-nr">Auto {idx + 1}</div>', unsafe_allow_html=True)
        with hcol2:
            if idx > 0:
                if st.button("✕", key=f"del_{car_id}", help="Verwijder deze auto"):
                    st.session_state["autos"] = [a for a in st.session_state["autos"] if a["id"] != car_id]
                    st.rerun()

        # Kenteken
        st.markdown('<p style="font-size:13px;font-weight:600;color:#31333F;margin-bottom:3px;">Kenteken</p>',
                    unsafe_allow_html=True)
        _kent_val = _auto_paste_input(
            value=auto_entry["kenteken"],
            pattern=r"^[A-Z0-9]{6}$",
            placeholder="bijv. TH-992-G",
            key=f"kenteken_comp_{car_id}",
            default=None,
        )
        if _kent_val is not None and _kent_val != auto_entry["kenteken"]:
            auto_entry["kenteken"] = _kent_val
            st.rerun()

        kenteken_i = auto_entry["kenteken"]

        if len(kenteken_i) < 6:
            if len(kenteken_i) > 0:
                st.caption(f"{len(kenteken_i)}/6 tekens — voer een geldig kenteken in.")
            auto_results.append(None)
            continue

        with st.spinner("RDW ophalen…"):
            auto_data_i = _rdw_ophalen(kenteken_i)

        if auto_data_i is None:
            st.error(f"Kenteken **{kenteken_i}** niet gevonden in het RDW.")
            auto_results.append(None)
            continue

        # Auto-info strip
        ts_i = auto_data_i["datum_tenaamstelling"]
        co2_txt = f"{auto_data_i['co2']} g/km" if auto_data_i["co2"] is not None else "CO₂ onbekend"
        cat_txt = nl_euro(auto_data_i["catalogusprijs"]) if auto_data_i["catalogusprijs"] else "—"
        ts_html = (f' &nbsp;·&nbsp; <span style="color:#1a4d2e;font-weight:600;">In gebruik vanaf {nl_date(ts_i)}</span>'
                   if ts_i else "")
        st.markdown(
            f'<div class="auto-info">'
            f'<b>{kenteken_i}</b> &nbsp;·&nbsp; {auto_data_i["voertuig"]} &nbsp;·&nbsp; '
            f'Bouwjaar {auto_data_i["bouwjaar"]} &nbsp;·&nbsp; {auto_data_i["brandstof"]} &nbsp;·&nbsp; '
            f'{co2_txt} &nbsp;·&nbsp; Catalogusprijs {cat_txt}{ts_html}</div>',
            unsafe_allow_html=True,
        )

        # Catalogusprijs
        catalogusprijs_i = float(auto_data_i["catalogusprijs"]) if auto_data_i["catalogusprijs"] else None
        if catalogusprijs_i is None:
            st.warning("Catalogusprijs niet gevonden — vul handmatig in.")
            cat_h = st.number_input("Catalogusprijs (€, incl. BTW en BPM)",
                                    min_value=0, value=0, step=500, key=f"cat_{car_id}")
            if cat_h == 0:
                auto_results.append(None)
                continue
            catalogusprijs_i = float(cat_h)

        # Slimme default periode
        van_key = f"datum_van_{car_id}_{berekeningsjaar}"
        tot_key = f"datum_tot_{car_id}_{berekeningsjaar}"

        if van_key not in st.session_state:
            if idx == 0:
                if ts_i and ts_i.year == berekeningsjaar:
                    st.session_state[van_key] = ts_i
                else:
                    st.session_state[van_key] = date(berekeningsjaar, 1, 1)
            else:
                prev_id = st.session_state["autos"][idx - 1]["id"]
                prev_tot = st.session_state.get(f"datum_tot_{prev_id}_{berekeningsjaar}",
                                                 date(berekeningsjaar, 6, 30))
                chained = prev_tot + timedelta(days=1)
                st.session_state[van_key] = min(chained, date(berekeningsjaar, 12, 31))

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            datum_van_i = st.date_input(
                "Van",
                min_value=date(berekeningsjaar, 1, 1),
                max_value=date(berekeningsjaar, 12, 31),
                format="DD-MM-YYYY",
                key=van_key,
            )
        with col_d2:
            datum_tot_i = st.date_input(
                "Tot en met",
                value=date(berekeningsjaar, 12, 31),
                min_value=date(berekeningsjaar, 1, 1),
                max_value=date(berekeningsjaar, 12, 31),
                format="DD-MM-YYYY",
                key=tot_key,
            )

        if datum_tot_i < datum_van_i:
            st.error("Einddatum moet na de begindatum liggen.")
            auto_results.append(None)
            continue

        dagen_i = (datum_tot_i - datum_van_i).days + 1
        periode_label_i = f"{nl_date(datum_van_i)} t/m {nl_date(datum_tot_i)}"

        btw_i = _btw_correctie(catalogusprijs_i, marge, dagen_i)
        bij_i, bij_label_i = _bijtelling(
            catalogusprijs_i, auto_data_i["co2"], auto_data_i["brandstof"],
            berekeningsjaar, dagen_i,
        )

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.html(f"""
            <div style="background:linear-gradient(135deg,#1a3a6e,#1e4680);color:white;
              border-radius:12px;padding:16px 20px;text-align:center;
              box-shadow:0 4px 14px rgba(26,58,110,.2);">
              <div style="font-size:11px;color:rgba(255,255,255,0.8);margin-bottom:4px;letter-spacing:.06em;">
                BTW-CORRECTIE PRIVÉGEBRUIK
              </div>
              <div style="font-size:30px;font-weight:bold;font-family:monospace;">{nl_euro(btw_i)}</div>
              <div style="font-size:11px;color:rgba(255,255,255,0.7);margin-top:4px;">
                {tarief_str} forfait &nbsp;·&nbsp; {dagen_i} dagen
              </div>
            </div>""")
        with col_r2:
            st.html(f"""
            <div style="background:linear-gradient(135deg,#1a4d2e,#1e5c36);color:white;
              border-radius:12px;padding:16px 20px;text-align:center;
              box-shadow:0 4px 14px rgba(26,77,46,.2);">
              <div style="font-size:11px;color:rgba(255,255,255,0.8);margin-bottom:4px;letter-spacing:.06em;">
                BIJTELLING (FISCALE WAARDE)
              </div>
              <div style="font-size:30px;font-weight:bold;font-family:monospace;">{nl_euro(bij_i)}</div>
              <div style="font-size:11px;color:rgba(255,255,255,0.7);margin-top:4px;">
                {bij_label_i} &nbsp;·&nbsp; {dagen_i} dagen
              </div>
            </div>""")

        auto_results.append({
            "kenteken": kenteken_i,
            "auto": auto_data_i,
            "catalogusprijs": catalogusprijs_i,
            "periode_label": periode_label_i,
            "dagen": dagen_i,
            "btw": btw_i,
            "bij": bij_i,
            "bij_label": bij_label_i,
        })

# ── Auto toevoegen ────────────────────────────────────────────────────────────
if n_autos < 5:
    if st.button("＋ Auto toevoegen", use_container_width=False):
        new_id = st.session_state["_next_id"]
        st.session_state["_next_id"] += 1
        last_id = st.session_state["autos"][-1]["id"]
        last_tot = st.session_state.get(
            f"datum_tot_{last_id}_{berekeningsjaar}",
            date(berekeningsjaar, 6, 30),
        )
        chained_van = last_tot + timedelta(days=1)
        if chained_van.year == berekeningsjaar:
            st.session_state[f"datum_van_{new_id}_{berekeningsjaar}"] = chained_van
        st.session_state["autos"].append({"id": new_id, "kenteken": ""})
        st.rerun()

# ── Totalen (bij meerdere auto's) ─────────────────────────────────────────────
valid_results = [r for r in auto_results if r is not None]

if len(valid_results) > 1:
    total_btw = sum(r["btw"] for r in valid_results)
    total_bij = sum(r["bij"] for r in valid_results)
    st.markdown("---")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.html(f"""
        <div style="background:linear-gradient(135deg,#0f2a5e,#153470);color:white;
          border-radius:12px;padding:14px 20px;text-align:center;
          box-shadow:0 4px 14px rgba(15,42,94,.25);">
          <div style="font-size:11px;color:rgba(255,255,255,0.75);margin-bottom:4px;letter-spacing:.06em;">
            TOTAAL BTW-CORRECTIE
          </div>
          <div style="font-size:26px;font-weight:bold;font-family:monospace;">{nl_euro(total_btw)}</div>
          <div style="font-size:11px;color:rgba(255,255,255,0.6);margin-top:3px;">
            {len(valid_results)} auto's · {sum(r['dagen'] for r in valid_results)} dagen totaal
          </div>
        </div>""")
    with col_t2:
        st.html(f"""
        <div style="background:linear-gradient(135deg,#0f3d22,#134a28);color:white;
          border-radius:12px;padding:14px 20px;text-align:center;
          box-shadow:0 4px 14px rgba(15,61,34,.25);">
          <div style="font-size:11px;color:rgba(255,255,255,0.75);margin-bottom:4px;letter-spacing:.06em;">
            TOTAAL BIJTELLING
          </div>
          <div style="font-size:26px;font-weight:bold;font-family:monospace;">{nl_euro(total_bij)}</div>
          <div style="font-size:11px;color:rgba(255,255,255,0.6);margin-top:3px;">
            {len(valid_results)} auto's · {berekeningsjaar}
          </div>
        </div>""")

# ── PDF ───────────────────────────────────────────────────────────────────────
if valid_results:
    kenteken_label = "_".join(r["kenteken"] for r in valid_results)
    bestandsnaam = f"BTW_auto_{kenteken_label}_{berekeningsjaar}.pdf"

    if st.button("📄 Genereer PDF", use_container_width=True):
        try:
            pdf_bytes = _maak_pdf(valid_results, klant_naam, klant_nr, berekeningsjaar, marge)
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
