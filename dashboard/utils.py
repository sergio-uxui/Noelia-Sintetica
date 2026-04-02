"""Utilidades compartidas entre páginas del dashboard."""

import sys
from pathlib import Path

import streamlit as st
import yaml

# Asegurar que el raíz del proyecto esté en el path para importar `noelia`
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---- Constantes visuales -------------------------------------------------- #

STATUS_CONFIG = {
    "nueva":      {"emoji": "🆕", "color": "#4A90D9"},
    "vista":      {"emoji": "👁️",  "color": "#8B8B8B"},
    "guardada":   {"emoji": "⭐",  "color": "#E6A817"},
    "aplicada":   {"emoji": "✅",  "color": "#27AE60"},
    "descartada": {"emoji": "🗑️", "color": "#C0392B"},
}

PLATFORM_CONFIG = {
    "linkedin":    {"emoji": "🔵", "color": "#0A66C2"},
    "infojobs":    {"emoji": "💼", "color": "#FF6600"},
    "indeed":      {"emoji": "🔍", "color": "#003A9B"},
    "glassdoor":   {"emoji": "🚪", "color": "#0CAA41"},
    "tecnoempleo": {"emoji": "💻", "color": "#333333"},
    "empresa":     {"emoji": "🏢", "color": "#8B5E3C"},
}

TAG_COLORS = {
    "top":         "#8B5E3C",
    "interesante": "#4A7A8B",
    "revisar":     "#8B8B4A",
}


# ---- Helpers --------------------------------------------------------------- #

@st.cache_resource
def get_database():
    """Instancia y cachea la base de datos."""
    from noelia.storage.database import Database
    db_path = load_settings().get("database", {}).get("path", "data/noelia.db")
    return Database(db_path)


@st.cache_data(ttl=60)
def load_settings() -> dict:
    """Carga settings.yaml cacheando 60 s."""
    path = ROOT / "config" / "settings.yaml"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


@st.cache_data(ttl=60)
def load_companies() -> list:
    """Carga companies.yaml cacheando 60 s."""
    path = ROOT / "config" / "companies.yaml"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data.get("companies", [])
    return []


def platform_badge(platform: str) -> str:
    cfg = PLATFORM_CONFIG.get(platform.lower() if platform else "", {})
    emoji = cfg.get("emoji", "📌")
    return f"{emoji} {platform.capitalize()}" if platform else "—"


def status_badge(status: str) -> str:
    cfg = STATUS_CONFIG.get(status.lower() if status else "nueva", {})
    emoji = cfg.get("emoji", "•")
    return f"{emoji} {status.capitalize()}" if status else "—"


def tag_pill(tag: str) -> str:
    color = TAG_COLORS.get(tag.lower(), "#666")
    return (
        f'<span style="background:{color};color:#fff;padding:2px 8px;'
        f'border-radius:12px;font-size:0.78em;margin:2px">{tag}</span>'
    )


def css_inject() -> None:
    """Inyecta CSS global de la app."""
    st.markdown(
        """
        <style>
        /* Métricas */
        [data-testid="metric-container"] {
            background: #F0E8DF;
            border-radius: 12px;
            padding: 16px;
            border-left: 4px solid #8B5E3C;
        }
        /* Botón primario */
        .stButton > button[kind="primary"] {
            background-color: #8B5E3C;
            border: none;
            color: white;
            font-weight: 600;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: #6E4A2E;
        }
        /* Links en tablas */
        a { color: #8B5E3C !important; }
        /* Encabezados */
        h1, h2, h3 { color: #2C1A0E; }
        /* Sidebar título */
        section[data-testid="stSidebar"] h1 {
            font-size: 1.4rem;
        }
        /* Dataframe compacto */
        .stDataFrame { border-radius: 8px; }
        /* Divider */
        hr { border-color: #D4C4B8; }
        </style>
        """,
        unsafe_allow_html=True,
    )
