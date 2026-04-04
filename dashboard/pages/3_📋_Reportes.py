"""
Página: Reportes semanales generados por Noelia Sintética.
"""

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.utils import css_inject, load_settings

st.set_page_config(page_title="Reportes · Noelia Sintética", page_icon="📋", layout="wide")
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
        "- 📋 Reportes _(esta página)_\n"
        "- ⚙️ [Configuración](Configuracion)\n"
    )

st.title("📋 Reportes semanales")

# ---- Listar reportes ------------------------------------------------------- #
settings = load_settings()
reports_dir = Path(ROOT) / settings.get("reports", {}).get("path", "reports")

report_files = sorted(reports_dir.glob("reporte_*.md"), reverse=True) if reports_dir.exists() else []

if not report_files:
    st.info(
        "Aún no se han generado reportes. "
        "Ejecuta el agente desde **🤖 Agente** para crear el primero."
    )
    st.stop()

# ---- Selector de reporte --------------------------------------------------- #
col_sel, col_dl = st.columns([4, 1])
with col_sel:
    report_names = [f.name for f in report_files]
    selected_name = st.selectbox(
        "Seleccionar reporte",
        report_names,
        format_func=lambda n: n.replace("reporte_", "Semana del ").replace(".md", ""),
    )

selected_path = reports_dir / selected_name
report_content = selected_path.read_text(encoding="utf-8")

with col_dl:
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label="⬇️ Descargar",
        data=report_content,
        file_name=selected_name,
        mime="text/markdown",
        use_container_width=True,
    )

st.divider()

# ---- Render del reporte ---------------------------------------------------- #
# Estadísticas rápidas del fichero
lines = report_content.split("\n")
job_lines = [l for l in lines if l.startswith("####")]
st.caption(
    f"Reporte: **{selected_name}** · "
    f"{len(job_lines)} ofertas · "
    f"{len(report_content):,} caracteres"
)

# Vista seleccionable: renderizado o raw
view_mode = st.radio("Vista", ["📖 Renderizado", "📄 Markdown raw"], horizontal=True, label_visibility="collapsed")

if view_mode == "📖 Renderizado":
    st.markdown(report_content, unsafe_allow_html=False)
else:
    st.code(report_content, language="markdown")

# ---- Historial de reportes ------------------------------------------------- #
if len(report_files) > 1:
    st.divider()
    st.subheader(f"📁 Todos los reportes ({len(report_files)})")
    for f in report_files:
        size_kb = f.stat().st_size / 1024
        date_str = f.name.replace("reporte_", "").replace(".md", "")
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(f"📋 **{date_str}** — {size_kb:.1f} KB")
        with c2:
            content = f.read_text(encoding="utf-8")
            st.download_button(
                "⬇️",
                data=content,
                file_name=f.name,
                mime="text/markdown",
                key=f"dl_{f.name}",
            )
