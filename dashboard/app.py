"""
Noelia Sintética — Dashboard principal (página de inicio).
Ejecutar con:  streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.utils import (
    css_inject,
    get_database,
    load_companies,
    load_settings,
    platform_badge,
    status_badge,
    tag_pill,
    PLATFORM_CONFIG,
    STATUS_CONFIG,
)

# ---- Configuración de página ---------------------------------------------- #

st.set_page_config(
    page_title="Noelia Sintética",
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="expanded",
)
css_inject()


# ---- Sidebar --------------------------------------------------------------- #

with st.sidebar:
    st.markdown("## 👗 Noelia Sintética")
    st.caption("Monitorización de empleo en moda y cine/TV")
    st.divider()
    st.markdown(
        """
        **Candidata:** Noelia Arias
        **Perfil:** Fashion Designer · Vestuario Cine & TV · Estilista
        """
    )
    st.divider()
    st.markdown(
        "**Navegación**\n\n"
        "- 🏠 Dashboard _(esta página)_\n"
        "- 💼 [Ofertas](Ofertas)\n"
        "- 🤖 [Agente](Agente)\n"
        "- 📋 [Reportes](Reportes)\n"
        "- ⚙️ [Configuración](Configuracion)\n"
    )


# ---- Carga de datos -------------------------------------------------------- #

db = get_database()
stats = db.get_stats()
new_jobs = db.get_jobs(only_new=True, limit=100)
all_jobs = db.get_jobs(limit=500)
last_runs = db.get_last_runs(limit=5)


# ---- Cabecera -------------------------------------------------------------- #

col_title, col_action = st.columns([5, 1])
with col_title:
    st.title("🏠 Dashboard")
    st.caption("Resumen semanal de oportunidades de empleo")
with col_action:
    if st.button("🔄 Actualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()


# ---- KPIs ------------------------------------------------------------------ #

k1, k2, k3, k4, k5 = st.columns(5)

total = stats.get("total", 0)
new_count = stats.get("new_this_week", 0)

by_status_dict = {r["status"]: r["c"] for r in stats.get("by_status", [])}
applied = by_status_dict.get("aplicada", 0)
saved = by_status_dict.get("guardada", 0)
companies_monitored = len(load_companies())

k1.metric("📋 Total ofertas", total)
k2.metric("🆕 Nuevas esta semana", new_count, delta=f"+{new_count}" if new_count else None)
k3.metric("⭐ Guardadas", saved)
k4.metric("✅ Aplicadas", applied)
k5.metric("🏢 Empresas monitorizadas", companies_monitored)

st.divider()


# ---- Gráficos -------------------------------------------------------------- #

chart_col1, chart_col2 = st.columns(2)

# Gráfico 1: Distribución por plataforma
with chart_col1:
    st.subheader("Por plataforma")
    by_platform = stats.get("by_platform", [])
    if by_platform:
        labels = [r.get("platform") or "otras" for r in by_platform]
        values = [r["c"] for r in by_platform]
        colors = [
            PLATFORM_CONFIG.get(lbl.lower(), {}).get("color", "#8B5E3C")
            for lbl in labels
        ]
        fig = go.Figure(
            go.Bar(
                x=labels,
                y=values,
                marker_color=colors,
                text=values,
                textposition="outside",
            )
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=20, l=0, r=0),
            height=280,
            showlegend=False,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#E8DDD5"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin datos aún. Ejecuta el agente para empezar.")

# Gráfico 2: Distribución por estado
with chart_col2:
    st.subheader("Por estado")
    by_status = stats.get("by_status", [])
    if by_status:
        labels_s = [r["status"] for r in by_status]
        values_s = [r["c"] for r in by_status]
        colors_s = [
            STATUS_CONFIG.get(lbl.lower(), {}).get("color", "#8B5E3C")
            for lbl in labels_s
        ]
        fig2 = go.Figure(
            go.Pie(
                labels=[status_badge(l) for l in labels_s],
                values=values_s,
                marker_colors=colors_s,
                hole=0.45,
                textinfo="label+value",
            )
        )
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=20, l=0, r=0),
            height=280,
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sin datos aún.")

st.divider()


# ---- Nuevas ofertas esta semana -------------------------------------------- #

st.subheader(f"🆕 Nuevas esta semana ({len(new_jobs)})")

if not new_jobs:
    st.info("No hay ofertas nuevas esta semana. Ejecuta el agente desde la página **🤖 Agente**.")
else:
    # Ordenar: primero las "top", luego "interesante", luego resto
    def sort_key(j):
        tags = j.get("tags") or []
        if "top" in tags:
            return 0
        if "interesante" in tags:
            return 1
        return 2

    new_jobs_sorted = sorted(new_jobs, key=sort_key)

    for job in new_jobs_sorted[:20]:
        tags = job.get("tags") or []
        pills_html = " ".join(tag_pill(t) for t in tags[:4]) if tags else ""
        platform = job.get("platform") or "empresa"
        company = job.get("company", "—")
        title = job.get("title", "Sin título")
        location = job.get("location") or ""
        url = job.get("url", "#")
        date_found = job.get("date_found", "")[:10]

        with st.container():
            col_info, col_meta = st.columns([4, 1])
            with col_info:
                st.markdown(
                    f"**[{title}]({url})**  \n"
                    f"🏢 {company} &nbsp;|&nbsp; {platform_badge(platform)}"
                    + (f" &nbsp;|&nbsp; 📍 {location}" if location else ""),
                    unsafe_allow_html=True,
                )
                if pills_html:
                    st.markdown(pills_html, unsafe_allow_html=True)
            with col_meta:
                st.caption(f"Encontrada: {date_found}")
        st.divider()

    if len(new_jobs) > 20:
        st.caption(f"Mostrando 20 de {len(new_jobs)}. Ver todas en **💼 Ofertas**.")


# ---- Top empresas ---------------------------------------------------------- #

st.divider()
col_companies, col_runs = st.columns(2)

with col_companies:
    st.subheader("🏆 Empresas con más ofertas")
    top_companies = stats.get("top_companies", [])
    if top_companies:
        for row in top_companies[:8]:
            pct = int((row["c"] / max(total, 1)) * 100)
            st.markdown(
                f"**{row['company']}** — {row['c']} oferta{'s' if row['c'] != 1 else ''}"
            )
            st.progress(pct / 100)
    else:
        st.info("Sin datos aún.")

with col_runs:
    st.subheader("🕐 Últimas ejecuciones")
    if last_runs:
        for run in last_runs:
            status_icon = "✅" if run["status"] == "completed" else ("❌" if run["status"] == "failed" else "🔄")
            started = str(run.get("started_at", ""))[:16]
            new_in_run = run.get("jobs_new", 0)
            st.markdown(
                f"{status_icon} **{started}** — "
                f"{new_in_run} nuevas · {run.get('jobs_found', 0)} encontradas"
            )
    else:
        st.info("Aún no se ha ejecutado el agente.")
        st.markdown("👉 Ve a **🤖 Agente** para lanzar la primera monitorización.")
