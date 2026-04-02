"""
Página: Agente — lanzar monitorización y ver historial de ejecuciones.
"""

import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue

import streamlit as st

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.utils import css_inject, get_database, load_companies, load_settings

st.set_page_config(page_title="Agente · Noelia Sintética", page_icon="🤖", layout="wide")
css_inject()

# ---- Sidebar --------------------------------------------------------------- #
with st.sidebar:
    st.markdown("## 👗 Noelia Sintética")
    st.caption("Monitorización de empleo en moda y cine/TV")
    st.divider()
    st.markdown(
        "**Navegación**\n\n"
        "- 🏠 [Dashboard](../app)\n"
        "- 💼 [Ofertas](Ofertas)\n"
        "- 🤖 Agente _(esta página)_\n"
        "- 📋 [Reportes](Reportes)\n"
        "- ⚙️ [Configuración](Configuracion)\n"
    )


# ---- Estado de sesión ------------------------------------------------------ #
if "agent_running" not in st.session_state:
    st.session_state.agent_running = False
if "agent_log" not in st.session_state:
    st.session_state.agent_log = []
if "agent_result" not in st.session_state:
    st.session_state.agent_result = None
if "log_queue" not in st.session_state:
    st.session_state.log_queue = Queue()


# ---- Handler de logging para Streamlit ------------------------------------- #
class QueueLogHandler(logging.Handler):
    """Envía registros de log a una Queue para mostrarlos en Streamlit."""

    def __init__(self, queue: Queue):
        super().__init__()
        self.queue = queue

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        level = record.levelname
        self.queue.put({"level": level, "msg": msg})


# ---- Runner del agente en hilo --------------------------------------------- #
def run_agent_thread(queue: Queue, extra: str, api_key: str, db_path: str, config: dict):
    """Ejecuta el agente en un hilo separado y envía resultados a la queue."""
    # Configurar logging para este hilo
    handler = QueueLogHandler(queue)
    handler.setFormatter(logging.Formatter("%(name)s — %(message)s"))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    try:
        from noelia.agent import NoeliAgent
        from noelia.reporter import Reporter

        queue.put({"level": "START", "msg": "🤖 Agente iniciado…"})

        agent = NoeliAgent(api_key=api_key, db_path=db_path, config=config)
        reporter = Reporter(
            reports_dir=config.get("settings", {}).get("reports", {}).get("path", "reports")
        )

        result = agent.run(extra_instructions=extra)

        report_path = reporter.generate_weekly_report(
            database=agent.database,
            run_stats=result,
            agent_summary=result.get("final_summary", ""),
        )
        result["report_path"] = report_path

        queue.put({"level": "DONE", "msg": result})

    except Exception as exc:
        queue.put({"level": "ERROR", "msg": f"Error: {exc}"})
    finally:
        root_logger.removeHandler(handler)


# ---- Interfaz -------------------------------------------------------------- #
st.title("🤖 Agente de monitorización")

db = get_database()
settings = load_settings()
companies = load_companies()

# Información del estado actual
info_col, stat_col = st.columns([3, 1])
with info_col:
    st.markdown(
        """
        El agente usa **Claude claude-opus-4-6** con adaptive thinking para:
        1. Revisar las páginas de empleo de las **{n_companies} empresas** configuradas
        2. Buscar en **LinkedIn, InfoJobs, Indeed y Glassdoor** con las keywords del perfil
        3. Filtrar, clasificar y guardar las nuevas ofertas
        4. Generar el reporte semanal en Markdown
        """.format(n_companies=len(companies))
    )
with stat_col:
    stats = db.get_stats()
    st.metric("Total en BD", stats.get("total", 0))
    st.metric("Nuevas esta semana", stats.get("new_this_week", 0))

st.divider()


# ---- Configuración de la ejecución ----------------------------------------- #
st.subheader("⚙️ Configurar ejecución")

run_col1, run_col2 = st.columns([3, 1])
with run_col1:
    extra_instructions = st.text_area(
        "Instrucciones adicionales (opcional)",
        placeholder=(
            "Ej: 'Prioriza producciones de Netflix y Amazon' · "
            "'Busca también en Zara y Mango' · "
            "'Ignora ofertas que requieran más de 5 años de experiencia'"
        ),
        height=80,
        disabled=st.session_state.agent_running,
    )
with run_col2:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.warning("⚠️ Sin ANTHROPIC_API_KEY")
    else:
        st.success("✅ API Key configurada")

st.divider()


# ---- Botón de lanzamiento -------------------------------------------------- #
launch_col, stop_col, _ = st.columns([2, 1, 3])

with launch_col:
    if not st.session_state.agent_running:
        launch_btn = st.button(
            "🚀 Lanzar monitorización completa",
            type="primary",
            use_container_width=True,
            disabled=not api_key,
        )
    else:
        st.button(
            "⏳ Agente ejecutándose…",
            disabled=True,
            use_container_width=True,
        )
        launch_btn = False

with stop_col:
    if st.button("🔍 Búsqueda rápida", use_container_width=True,
                 disabled=st.session_state.agent_running or not api_key):
        st.session_state.show_quick_search = True

# Búsqueda rápida
if st.session_state.get("show_quick_search"):
    with st.form("quick_search_form"):
        kw = st.text_input("Keyword a buscar", placeholder="Ej: costume designer Madrid")
        loc = st.text_input("Ubicación", value="España")
        submitted = st.form_submit_button("Buscar ahora", type="primary")
        if submitted and kw:
            st.session_state.show_quick_search = False
            st.session_state.quick_search_kw = kw
            st.session_state.quick_search_loc = loc
            st.rerun()


# ---- Lanzar agente completo ------------------------------------------------ #
if launch_btn and api_key and not st.session_state.agent_running:
    st.session_state.agent_running = True
    st.session_state.agent_log = []
    st.session_state.agent_result = None
    q = Queue()
    st.session_state.log_queue = q

    import yaml
    config: dict = {}
    for fname, key in [("companies.yaml", "companies"), ("settings.yaml", "settings")]:
        fpath = ROOT / "config" / fname
        if fpath.exists():
            with open(fpath, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            config["companies" if key == "companies" else "settings"] = (
                data.get("companies", []) if key == "companies" else data
            )

    db_path = config.get("settings", {}).get("database", {}).get("path", "data/noelia.db")

    t = threading.Thread(
        target=run_agent_thread,
        args=(q, extra_instructions, api_key, db_path, config),
        daemon=True,
    )
    t.start()
    st.rerun()


# ---- Ejecutar búsqueda rápida ---------------------------------------------- #
if st.session_state.get("quick_search_kw") and api_key:
    kw = st.session_state.pop("quick_search_kw")
    loc = st.session_state.pop("quick_search_loc", "España")
    with st.spinner(f"Buscando '{kw}' en {loc}…"):
        import yaml
        config = {}
        for fname, key in [("companies.yaml", "companies"), ("settings.yaml", "settings")]:
            fpath = ROOT / "config" / fname
            if fpath.exists():
                with open(fpath, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                config["companies" if key == "companies" else "settings"] = (
                    data.get("companies", []) if key == "companies" else data
                )
        db_path = config.get("settings", {}).get("database", {}).get("path", "data/noelia.db")
        from noelia.agent import NoeliAgent
        agent = NoeliAgent(api_key=api_key, db_path=db_path, config=config)
        result = agent.run_quick_search(kw, loc)

    st.success("Búsqueda completada")
    st.markdown(result.get("summary", "Sin resultados."))
    st.cache_data.clear()


# ---- Panel de log en tiempo real ------------------------------------------- #
if st.session_state.agent_running:
    st.divider()
    st.subheader("📡 Progreso del agente")

    log_container = st.container()
    progress_bar = st.progress(0, text="Iniciando…")

    # Vaciar la queue y recoger mensajes nuevos
    q = st.session_state.log_queue
    done = False
    new_msgs = []

    while True:
        try:
            item = q.get_nowait()
            new_msgs.append(item)
            if item["level"] in ("DONE", "ERROR"):
                done = True
                break
        except Empty:
            break

    st.session_state.agent_log.extend(new_msgs)

    # Mostrar log
    with log_container:
        log_lines = []
        for i, entry in enumerate(st.session_state.agent_log[-40:]):
            level = entry["level"]
            msg = entry["msg"]
            if level == "START":
                log_lines.append(f"🟢 {msg}")
            elif level == "DONE":
                log_lines.append("✅ Monitorización completada")
            elif level == "ERROR":
                log_lines.append(f"❌ {msg}")
            elif level == "WARNING":
                log_lines.append(f"⚠️ {msg}")
            elif isinstance(msg, str) and "Herramienta:" in msg:
                log_lines.append(f"🔧 {msg}")
            else:
                log_lines.append(f"   {msg}")

        st.code("\n".join(log_lines), language=None)

    if done:
        st.session_state.agent_running = False
        result_item = next(
            (e for e in st.session_state.agent_log if e["level"] == "DONE"), None
        )
        error_item = next(
            (e for e in st.session_state.agent_log if e["level"] == "ERROR"), None
        )

        if result_item:
            st.session_state.agent_result = result_item["msg"]
        if error_item:
            st.error(str(error_item["msg"]))

        st.cache_data.clear()
        st.rerun()
    else:
        # Seguir reejecutando mientras el agente corre
        tool_calls = sum(
            1 for e in st.session_state.agent_log
            if isinstance(e.get("msg"), str) and "Herramienta:" in e["msg"]
        )
        progress_bar.progress(
            min(tool_calls / 30, 0.95),
            text=f"Herramientas ejecutadas: {tool_calls}…",
        )
        import time
        time.sleep(1)
        st.rerun()


# ---- Resultado de la última ejecución -------------------------------------- #
if st.session_state.agent_result and not st.session_state.agent_running:
    result = st.session_state.agent_result
    if isinstance(result, dict):
        st.divider()
        st.subheader("📊 Resultado de la ejecución")

        r1, r2, r3 = st.columns(3)
        r1.metric("Nuevas ofertas", result.get("db_stats", {}).get("new_this_week", 0))
        r2.metric("Turnos del agente", result.get("turns", 0))
        r3.metric("Herramientas usadas", result.get("tool_calls", 0))

        if result.get("final_summary"):
            st.divider()
            st.subheader("📝 Resumen del agente")
            st.markdown(result["final_summary"])

        if result.get("report_path"):
            st.success(f"📋 Reporte generado: `{result['report_path']}`")
            st.page_link("pages/3_📋_Reportes.py", label="Ver reportes →", icon="📋")


# ---- Historial de ejecuciones ---------------------------------------------- #
st.divider()
st.subheader("🕐 Historial de ejecuciones")

last_runs = db.get_last_runs(limit=10)
if not last_runs:
    st.info("Sin ejecuciones previas.")
else:
    for run in last_runs:
        status_icon = {"completed": "✅", "failed": "❌", "running": "🔄"}.get(
            run["status"], "•"
        )
        started = str(run.get("started_at", ""))[:16]
        finished = str(run.get("finished_at", ""))[:16] if run.get("finished_at") else "—"
        duration = "—"
        if run.get("started_at") and run.get("finished_at"):
            try:
                fmt = "%Y-%m-%d %H:%M:%S"
                s = datetime.strptime(run["started_at"][:19], fmt)
                f = datetime.strptime(run["finished_at"][:19], fmt)
                secs = int((f - s).total_seconds())
                duration = f"{secs // 60}m {secs % 60}s"
            except Exception:
                pass

        with st.expander(
            f"{status_icon} {started} — {run.get('jobs_new', 0)} nuevas · "
            f"{run.get('jobs_found', 0)} encontradas · {duration}"
        ):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Empresas revisadas", run.get("companies_checked", "—"))
            c2.metric("Plataformas", run.get("platforms_checked", "—"))
            c3.metric("Nuevas", run.get("jobs_new", 0))
            c4.metric("Total encontradas", run.get("jobs_found", 0))
            if run.get("error_message"):
                st.error(run["error_message"])
            if run.get("report_path"):
                st.caption(f"Reporte: {run['report_path']}")
