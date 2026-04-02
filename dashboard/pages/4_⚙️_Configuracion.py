"""
Página: Configuración — vista de empresas monitorizadas y ajustes.
"""

import sys
from pathlib import Path

import streamlit as st
import yaml

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.utils import css_inject, load_companies, load_settings

st.set_page_config(page_title="Configuración · Noelia Sintética", page_icon="⚙️", layout="wide")
css_inject()

with st.sidebar:
    st.markdown("## 👗 Noelia Sintética")
    st.caption("Monitorización de empleo en moda y cine/TV")
    st.divider()
    st.markdown(
        "**Navegación**\n\n"
        "- 🏠 [Dashboard](../app)\n"
        "- 💼 [Ofertas](Ofertas)\n"
        "- 🤖 [Agente](Agente)\n"
        "- 📋 [Reportes](Reportes)\n"
        "- ⚙️ Configuración _(esta página)_\n"
    )

st.title("⚙️ Configuración")

companies = load_companies()
settings = load_settings()

tab_companies, tab_keywords, tab_scheduler, tab_candidate, tab_raw = st.tabs([
    "🏢 Empresas",
    "🔍 Keywords",
    "⏰ Planificador",
    "👩‍🎨 Candidata",
    "📄 YAML raw",
])


# ---- Tab: Empresas --------------------------------------------------------- #
with tab_companies:
    st.subheader(f"Empresas monitorizadas ({len(companies)})")
    st.caption("Edita `config/companies.yaml` para añadir o eliminar empresas.")

    # Agrupar por categoría inferida de notes
    for i, company in enumerate(companies, 1):
        name = company.get("name", "—")
        career_url = company.get("career_url", "")
        linkedin = company.get("social_linkedin", "")
        keywords = company.get("keywords", [])
        notes = company.get("notes", "")

        with st.expander(f"{i}. **{name}**" + (f" — _{notes}_" if notes else "")):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Página de empleo:**")
                if career_url:
                    st.markdown(f"[{career_url}]({career_url})")
                else:
                    st.caption("No configurada")
            with c2:
                st.markdown("**LinkedIn:**")
                if linkedin:
                    st.markdown(f"[{linkedin}]({linkedin})")
                else:
                    st.caption("No configurado")
            if keywords:
                st.markdown("**Keywords específicas:**")
                st.markdown(" ".join(f"`{k}`" for k in keywords))


# ---- Tab: Keywords --------------------------------------------------------- #
with tab_keywords:
    search_cfg = settings.get("search", {})
    keywords = search_cfg.get("keywords", [])
    locations = search_cfg.get("locations", [])
    relevance = search_cfg.get("relevance_criteria", {})

    col_kw, col_loc = st.columns(2)
    with col_kw:
        st.subheader(f"Palabras clave ({len(keywords)})")
        for kw in keywords:
            st.markdown(f"- `{kw}`")

    with col_loc:
        st.subheader("Ubicaciones")
        for loc in locations:
            st.markdown(f"- 📍 {loc}")

    st.divider()

    if relevance:
        st.subheader("Criterios de relevancia")
        c_inc, c_disc = st.columns(2)
        with c_inc:
            st.markdown("**✅ Incluir si contiene:**")
            for term in relevance.get("must_include_any", []):
                st.markdown(f"- `{term}`")
        with c_disc:
            st.markdown("**🚫 Descartar si contiene:**")
            for term in relevance.get("discard_if", []):
                st.markdown(f"- `{term}`")

    st.divider()
    st.subheader("Plataformas")
    platforms = settings.get("platforms", {})
    for name, cfg in platforms.items():
        enabled = cfg.get("enabled", True)
        note = cfg.get("notes", "")
        icon = "✅" if enabled else "❌"
        st.markdown(
            f"{icon} **{name.capitalize()}** — {cfg.get('base_url', '')} "
            + (f"_{note}_" if note else "")
        )


# ---- Tab: Planificador ----------------------------------------------------- #
with tab_scheduler:
    sched = settings.get("scheduler", {})
    st.subheader("Planificador semanal")

    c1, c2 = st.columns(2)
    c1.metric("Día de ejecución", sched.get("day", "monday").capitalize())
    c2.metric("Hora", sched.get("time", "09:00"))

    st.markdown(
        """
        Para iniciar el planificador en background, ejecuta:
        ```bash
        python main.py schedule
        ```
        O directamente desde el dashboard con:
        ```bash
        python main.py schedule --now
        ```
        """
    )

    st.divider()
    st.subheader("Configuración de scraping")
    scraping = settings.get("scraping", {})
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Delay entre peticiones", f"{scraping.get('delay_between_requests', 2)}s")
    sc2.metric("Timeout", f"{scraping.get('request_timeout', 15)}s")
    sc3.metric("Reintentos máx.", scraping.get("max_retries", 3))


# ---- Tab: Candidata -------------------------------------------------------- #
with tab_candidate:
    candidate = settings.get("candidate", {})
    if not candidate:
        st.info("Perfil de candidata no configurado en settings.yaml")
        st.stop()

    st.subheader(f"👩‍🎨 {candidate.get('name', 'Candidata')}")
    st.markdown(candidate.get("profile", ""))

    st.divider()
    skills = candidate.get("skills", {})
    if skills:
        c_soft, c_domain = st.columns(2)
        with c_soft:
            st.markdown("**Software y herramientas:**")
            for s in skills.get("software", []):
                st.markdown(f"- `{s}`")
        with c_domain:
            st.markdown("**Dominio profesional:**")
            for s in skills.get("domain", []):
                st.markdown(f"- {s}")

    langs = candidate.get("languages", [])
    if langs:
        st.divider()
        st.markdown("**Idiomas:** " + " · ".join(f"🌐 {l}" for l in langs))

    prefs = candidate.get("location_preference", [])
    if prefs:
        st.markdown("**Preferencia de ubicación:** " + " · ".join(f"📍 {p}" for p in prefs))


# ---- Tab: YAML raw --------------------------------------------------------- #
with tab_raw:
    st.subheader("settings.yaml")
    settings_path = ROOT / "config" / "settings.yaml"
    if settings_path.exists():
        raw_settings = settings_path.read_text(encoding="utf-8")
        st.code(raw_settings, language="yaml")
        st.download_button(
            "⬇️ Descargar settings.yaml",
            data=raw_settings,
            file_name="settings.yaml",
            mime="text/yaml",
        )

    st.divider()
    st.subheader("companies.yaml")
    companies_path = ROOT / "config" / "companies.yaml"
    if companies_path.exists():
        raw_companies = companies_path.read_text(encoding="utf-8")
        st.code(raw_companies, language="yaml")
        st.download_button(
            "⬇️ Descargar companies.yaml",
            data=raw_companies,
            file_name="companies.yaml",
            mime="text/yaml",
        )
