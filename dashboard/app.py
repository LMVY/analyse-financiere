"""Dashboard Streamlit - Launcher avec navigation par onglets."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="NEO-FINANCE",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Navigation : boutons radio horizontaux en haut du contenu
page = st.radio(
    "Navigation",
    ["📊 Analyse", "⚙️ Admin"],
    horizontal=True,
    label_visibility="collapsed",
    key="nav_page",
)

st.divider()

# Executer le body correspondant
HERE = Path(__file__).parent
if page == "📊 Analyse":
    body_path = HERE / "_analyse_body.py"
else:
    body_path = HERE / "_admin_body.py"

code = body_path.read_text(encoding="utf-8")
exec(compile(code, str(body_path), "exec"))
