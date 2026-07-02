import re
import streamlit as st
import requests
from datetime import date

BELASTINGDIENST_URL = (
    "https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/"
    "standaard_functies/prive/contact/rechten_en_plichten_bij_de_belastingdienst/"
    "belastingrente/overzicht_percentages_belastingrente"
)


@st.cache_data(show_spinner=False)
def _haal_pagina_op(maand: str) -> str | None:
    """Haalt de tarieven-pagina op, gecached per maand (maand = 'YYYY-MM')."""
    try:
        resp = requests.get(
            BELASTINGDIENST_URL,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (compatible; BouwmanTools)"},
        )
        return resp.text if resp.ok else None
    except Exception:
        return None


def controleer_nieuwe_tarieven(tarieven: list) -> str | None:
    """
    Controleert eens per maand of belastingdienst.nl datums noemt die nieuwer
    zijn dan de laatste invoer in TARIEVEN. Geeft een waarschuwingsstring terug
    of None als alles actueel lijkt / de pagina niet bereikbaar is.
    """
    maand_sleutel = date.today().strftime("%Y-%m")
    html = _haal_pagina_op(maand_sleutel)
    if not html:
        return None  # Pagina niet bereikbaar — stilzwijgend doorgaan

    laatste_bekende_datum = tarieven[0][0]  # meest recente datum in de tabel

    for d_str in re.findall(r"\b(\d{1,2}-\d{1,2}-\d{4})\b", html):
        try:
            dag, mnd, jaar = map(int, d_str.split("-"))
            if date(jaar, mnd, dag) > laatste_bekende_datum:
                return (
                    f"Mogelijk zijn er nieuwe belastingrentetarieven gepubliceerd "
                    f"(datum **{d_str}** gevonden op belastingdienst.nl, nieuwer dan de "
                    f"laatste invoer in de tarieven-tabel). "
                    f"[Controleer de actuele percentages]({BELASTINGDIENST_URL}) "
                    f"en pas de tarieven aan in de code."
                )
        except Exception:
            pass
    return None
