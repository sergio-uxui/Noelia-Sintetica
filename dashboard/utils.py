"""Utilidades compartidas entre páginas del dashboard."""

import os
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
    """Instancia y cachea la base de datos.
    La ruta se puede sobreescribir con DB_PATH en st.secrets (Streamlit Cloud)
    o como variable de entorno (local / Railway).
    """
    from noelia.storage.database import Database
    db_path = (
        (st.secrets.get("DB_PATH", "") if hasattr(st, "secrets") else "")
        or os.environ.get("DB_PATH", "")
        or load_settings().get("database", {}).get("path", "data/noelia.db")
    )
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
    """Inyecta CSS global de la app — incluye reglas responsive para móvil."""
    st.markdown(
        """
        <style>
        /* ---- Base -------------------------------------------------------- */
        a { color: #8B5E3C !important; }
        h1, h2, h3 { color: #2C1A0E; }
        hr { border-color: #D4C4B8; }

        /* ---- Métricas ---------------------------------------------------- */
        [data-testid="metric-container"] {
            background: #F0E8DF;
            border-radius: 12px;
            padding: 16px;
            border-left: 4px solid #8B5E3C;
        }

        /* ---- Botones ---------------------------------------------------- */
        .stButton > button[kind="primary"] {
            background-color: #8B5E3C;
            border: none;
            color: white;
            font-weight: 600;
            min-height: 44px;          /* tap target mínimo para móvil */
        }
        .stButton > button[kind="primary"]:hover { background-color: #6E4A2E; }

        .stButton > button {
            min-height: 44px;
            border-radius: 8px;
        }

        /* ---- Links como botones (link_button) --------------------------- */
        .stLinkButton a {
            min-height: 44px;
            display: flex;
            align-items: center;
        }

        /* ---- Dataframe -------------------------------------------------- */
        .stDataFrame { border-radius: 8px; }

        /* ---- Sidebar ---------------------------------------------------- */
        section[data-testid="stSidebar"] h1 { font-size: 1.4rem; }
        section[data-testid="stSidebar"] { padding-top: 1rem; }

        /* ---- Selectbox y inputs — tap targets --------------------------- */
        .stSelectbox > div > div,
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            min-height: 44px;
        }

        /* ================================================================ */
        /* MÓVIL  (≤ 768 px)                                               */
        /* ================================================================ */
        @media (max-width: 768px) {

            /* Tipografía */
            h1 { font-size: 1.5rem !important; }
            h2 { font-size: 1.25rem !important; }
            h3 { font-size: 1.1rem !important; }
            p, li, .stMarkdown { font-size: 0.95rem; }

            /* Padding general reducido */
            .main .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                padding-top: 1rem !important;
            }

            /* Columnas → apiladas en móvil */
            [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }

            /* Métricas más compactas */
            [data-testid="metric-container"] {
                padding: 10px 12px;
                margin-bottom: 8px;
            }
            [data-testid="metric-container"] [data-testid="stMetricValue"] {
                font-size: 1.4rem !important;
            }

            /* Botones full-width en móvil */
            .stButton > button { width: 100%; }

            /* Expanders más grandes */
            .streamlit-expanderHeader { font-size: 1rem; padding: 12px 8px; }

            /* Ocultar sidebar en móvil por defecto (se abre con el toggle) */
            section[data-testid="stSidebar"] {
                min-width: 260px !important;
                max-width: 80vw !important;
            }

            /* Gráficos a altura menor para que quepan sin scroll */
            .js-plotly-plot { max-height: 240px; }

            /* Separadores más finos */
            hr { margin: 0.5rem 0; }

            /* Tarjetas de oferta sin borde izquierdo tan prominente */
            [style*="border-left"] { padding-left: 8px !important; }

            /* Pills/tags más pequeñas */
            span[style*="border-radius:12px"] {
                font-size: 0.72em !important;
                padding: 2px 6px !important;
            }

            /* Tabla exportar — ocultar en móvil */
            .stDownloadButton button { font-size: 0.9rem; }
        }

        /* ================================================================ */
        /* TABLET  (769 px – 1024 px)                                      */
        /* ================================================================ */
        @media (min-width: 769px) and (max-width: 1024px) {
            .main .block-container {
                padding-left: 1.5rem !important;
                padding-right: 1.5rem !important;
            }
            h1 { font-size: 1.8rem !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
