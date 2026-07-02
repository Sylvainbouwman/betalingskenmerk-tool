import streamlit as st

st.set_page_config(
    page_title="Bouwman Tools",
    page_icon="🏦",
    layout="centered",
)

pg = st.navigation([
    st.Page("pages/Betalingskenmerk.py",    title="Betalingskenmerk",    icon="🏦"),
    st.Page("pages/Belastingrente_IB.py",   title="Belastingrente IB",   icon="📊"),
    st.Page("pages/Belastingrente_VpB.py",  title="Belastingrente VpB",  icon="📊"),
])
pg.run()
