"""
Página: Ofertas de empleo — tabla completa con filtros y gestión de estados.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.utils import (
    css_inject,
    get_database,
    platform_badge,
    status_badge,
    tag_pill,
    STATUS_CONFIG,
    PLATFORM_CONFIG,
)

st.set_page_config(page_title="Ofertas · Noelia Sintética", page_icon="💼", layout="wide")
css_inject()


# ---- Sidebar --------------------------------------------------------------- #
with st.sidebar:
    st.markdown("## 👗 Noelia Sintética")
    st.caption("Monitorización de empleo en moda y cine/TV")
    st.divider()
    st.markdown(
        "**Navegación**\n\n"
        "- 🏠 [Dashboard](../app)\n"
        "- 💼 Ofertas _(esta página)_\n"
        "- 🤖 [Agente](Agente)\n"
        "- 📋 [Reportes](Reportes)\n"
        "- ⚙️ [Configuración](Configuracion)\n"
    )


# ---- Datos ----------------------------------------------------------------- #
db = get_database()
all_jobs = db.get_jobs(limit=1000)

st.title("💼 Ofertas de empleo")

if not all_jobs:
    st.info("Aún no hay ofertas. Ejecuta el agente desde la página **🤖 Agente**.")
    st.stop()


# ---- Filtros --------------------------------------------------------------- #
st.subheader("Filtros")

filter_cols = st.columns([2, 2, 2, 2, 1])

with filter_cols[0]:
    plataformas = ["Todas"] + sorted({j.get("platform") or "empresa" for j in all_jobs})
    sel_platform = st.selectbox("Plataforma", plataformas)

with filter_cols[1]:
    companies = ["Todas"] + sorted({j.get("company", "") for j in all_jobs if j.get("company")})
    sel_company = st.selectbox("Empresa", companies)

with filter_cols[2]:
    estados = ["Todos"] + list(STATUS_CONFIG.keys())
    sel_status = st.selectbox("Estado", estados, format_func=lambda s: status_badge(s) if s != "Todos" else "Todos")

with filter_cols[3]:
    all_tags = sorted({t for j in all_jobs for t in (j.get("tags") or [])})
    sel_tag = st.selectbox("Tag", ["Todos"] + all_tags)

with filter_cols[4]:
    only_new = st.checkbox("Solo nuevas 🆕", value=False)

search_text = st.text_input("🔍 Buscar en título o empresa", placeholder="Ej: costume, Zara, stylist…")

st.divider()


# ---- Filtrado -------------------------------------------------------------- #
def matches(job: dict) -> bool:
    p = job.get("platform") or "empresa"
    if sel_platform != "Todas" and p != sel_platform:
        return False
    if sel_company != "Todas" and job.get("company", "") != sel_company:
        return False
    if sel_status != "Todos" and job.get("status", "nueva") != sel_status:
        return False
    if sel_tag != "Todos" and sel_tag not in (job.get("tags") or []):
        return False
    if only_new and not job.get("is_new"):
        return False
    if search_text:
        haystack = f"{job.get('title','')} {job.get('company','')}".lower()
        if search_text.lower() not in haystack:
            return False
    return True


filtered = [j for j in all_jobs if matches(j)]
st.caption(f"Mostrando **{len(filtered)}** ofertas de {len(all_jobs)} totales")


# ---- Acciones en lote ------------------------------------------------------- #
if filtered:
    with st.expander("⚡ Acciones en lote", expanded=False):
        batch_col1, batch_col2 = st.columns([3, 1])
        with batch_col1:
            batch_status = st.selectbox(
                "Cambiar estado de las ofertas filtradas a:",
                options=list(STATUS_CONFIG.keys()),
                format_func=lambda s: status_badge(s),
                key="batch_status_select",
            )
        with batch_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Aplicar", type="primary", use_container_width=True):
                for job in filtered:
                    db.update_job_status(job["id"], batch_status)
                st.success(f"✅ {len(filtered)} ofertas actualizadas a '{batch_status}'")
                st.cache_data.clear()
                st.rerun()

    st.divider()


# ---- Tarjetas de ofertas --------------------------------------------------- #
ITEMS_PER_PAGE = 25
total_pages = max(1, (len(filtered) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

if total_pages > 1:
    page_col1, page_col2, page_col3 = st.columns([1, 2, 1])
    with page_col2:
        page = st.number_input("Página", min_value=1, max_value=total_pages, value=1, step=1)
else:
    page = 1

start = (page - 1) * ITEMS_PER_PAGE
page_jobs = filtered[start : start + ITEMS_PER_PAGE]

for job in page_jobs:
    job_id = job["id"]
    tags = job.get("tags") or []
    platform = job.get("platform") or "empresa"
    title = job.get("title", "Sin título")
    company = job.get("company", "—")
    location = job.get("location") or ""
    url = job.get("url", "#")
    salary = job.get("salary") or ""
    modality = job.get("modality") or ""
    date_found = job.get("date_found", "")[:10]
    date_posted = job.get("date_posted") or ""
    description = job.get("description") or ""
    current_status = job.get("status", "nueva")
    is_new = bool(job.get("is_new"))

    # Borde de color según tag
    border_color = "#8B5E3C"
    if "top" in tags:
        border_color = "#8B5E3C"
    elif "interesante" in tags:
        border_color = "#4A7A8B"
    elif "revisar" in tags:
        border_color = "#8B8B4A"

    with st.container():
        st.markdown(
            f'<div style="border-left:4px solid {border_color};padding-left:12px;margin-bottom:4px">',
            unsafe_allow_html=True,
        )

        row1, row2 = st.columns([5, 1])
        with row1:
            new_badge = "🆕 " if is_new else ""
            st.markdown(
                f"### {new_badge}[{title}]({url})",
                unsafe_allow_html=True,
            )
            meta_parts = [f"🏢 **{company}**", platform_badge(platform)]
            if location:
                meta_parts.append(f"📍 {location}")
            if modality:
                meta_parts.append(f"🏠 {modality}")
            if salary:
                meta_parts.append(f"💰 {salary}")
            if date_posted:
                meta_parts.append(f"📅 Publicada: {date_posted}")
            st.markdown(" &nbsp;|&nbsp; ".join(meta_parts), unsafe_allow_html=True)

            pills_html = " ".join(tag_pill(t) for t in tags[:6])
            if pills_html:
                st.markdown(pills_html, unsafe_allow_html=True)

            if description:
                with st.expander("Ver descripción"):
                    st.caption(description[:600])

        with row2:
            st.caption(f"Encontrada:\n{date_found}")
            new_status = st.selectbox(
                "Estado",
                options=list(STATUS_CONFIG.keys()),
                index=list(STATUS_CONFIG.keys()).index(current_status)
                if current_status in STATUS_CONFIG
                else 0,
                format_func=lambda s: status_badge(s),
                key=f"status_{job_id}",
                label_visibility="collapsed",
            )
            if new_status != current_status:
                db.update_job_status(job_id, new_status)
                st.toast(f"Estado actualizado a '{new_status}'")
                st.rerun()

            st.link_button("Abrir oferta →", url, use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)
        st.divider()

if total_pages > 1:
    st.caption(f"Página {page} de {total_pages}")


# ---- Exportar --------------------------------------------------------------- #
if filtered:
    st.divider()
    st.subheader("📥 Exportar")

    df_export = pd.DataFrame([
        {
            "Título": j.get("title", ""),
            "Empresa": j.get("company", ""),
            "Plataforma": j.get("platform", ""),
            "Ubicación": j.get("location", ""),
            "Estado": j.get("status", ""),
            "Tags": ", ".join(j.get("tags") or []),
            "Salario": j.get("salary", ""),
            "Modalidad": j.get("modality", ""),
            "URL": j.get("url", ""),
            "Fecha encontrada": j.get("date_found", ""),
        }
        for j in filtered
    ])

    csv_data = df_export.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="⬇️ Descargar CSV",
        data=csv_data,
        file_name="noelia_ofertas.csv",
        mime="text/csv",
    )
