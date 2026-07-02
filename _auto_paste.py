import streamlit.components.v1 as components
from pathlib import Path

_COMP_DIR = Path(__file__).parent / "_components" / "auto_paste"
auto_paste_input = components.declare_component("auto_paste", path=str(_COMP_DIR))
