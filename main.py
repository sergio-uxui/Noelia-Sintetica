#!/usr/bin/env python3
"""
Noelia Sintética — Punto de entrada principal.

Uso:
  python main.py run            # Monitorización completa ahora
  python main.py search <kw>    # Búsqueda rápida de una keyword
  python main.py schedule       # Iniciar planificador semanal (bloqueante)
  python main.py report         # Generar reporte con las ofertas actuales
  python main.py stats          # Ver estadísticas de la base de datos
  python main.py jobs [--new]   # Listar ofertas (--new: solo nuevas)
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import print as rprint

# Cargar .env
load_dotenv()

# Configurar logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("noelia")
console = Console()


def load_config() -> dict:
    """Carga companies.yaml y settings.yaml."""
    config_dir = Path(__file__).parent / "config"
    config: dict = {}

    for fname, key in [("companies.yaml", "companies"), ("settings.yaml", "settings")]:
        fpath = config_dir / fname
        if fpath.exists():
            with open(fpath, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if key == "companies":
                config["companies"] = data.get("companies", [])
            else:
                config["settings"] = data
        else:
            logger.warning("Fichero de configuración no encontrado: %s", fpath)

    return config


def get_agent(config: dict):
    """Instancia el agente con la configuración cargada."""
    from noelia import NoeliAgent

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        console.print("[bold red]Error:[/bold red] ANTHROPIC_API_KEY no está definida.")
        console.print("Crea un fichero .env con tu clave o expórtala como variable de entorno.")
        sys.exit(1)

    db_path = config.get("settings", {}).get("database", {}).get("path", "data/noelia.db")
    return NoeliAgent(api_key=api_key, db_path=db_path, config=config)


def cmd_run(args, config: dict) -> None:
    """Ejecuta la monitorización completa."""
    from noelia.reporter import Reporter

    agent = get_agent(config)
    reporter = Reporter(
        reports_dir=config.get("settings", {}).get("reports", {}).get("path", "reports")
    )

    console.rule("[bold green]🤖 Noelia Sintética — Monitorización semanal")
    console.print("Iniciando análisis completo de ofertas de empleo…\n")

    result = agent.run()

    # Generar reporte
    report_path = reporter.generate_weekly_report(
        database=agent.database,
        run_stats=result,
        agent_summary=result.get("final_summary", ""),
    )

    console.rule("[bold green]✅ Monitorización completada")
    console.print(f"\n[bold]Turnos del agente:[/bold] {result['turns']}")
    console.print(f"[bold]Llamadas a herramientas:[/bold] {result['tool_calls']}")
    console.print(f"[bold]Reporte guardado en:[/bold] {report_path}\n")

    stats = result.get("db_stats", {})
    console.print(f"[bold]Nuevas ofertas esta semana:[/bold] {stats.get('new_this_week', 0)}")
    console.print(f"[bold]Total en base de datos:[/bold] {stats.get('total', 0)}\n")

    if result.get("final_summary"):
        console.rule("Resumen del agente")
        rprint(result["final_summary"])


def cmd_search(args, config: dict) -> None:
    """Búsqueda rápida de una keyword."""
    keyword = " ".join(args.keyword)
    location = args.location or "España"

    agent = get_agent(config)

    console.rule(f"[bold blue]🔍 Búsqueda: '{keyword}' en {location}")
    result = agent.run_quick_search(keyword, location)

    console.rule("Resultados")
    rprint(result.get("summary", "Sin resultados."))


def cmd_schedule(args, config: dict) -> None:
    """Inicia el planificador semanal."""
    from noelia.scheduler import WeeklyScheduler
    from noelia.reporter import Reporter

    scheduler_cfg = config.get("settings", {}).get("scheduler", {})
    day = scheduler_cfg.get("day", "monday")
    run_time = scheduler_cfg.get("time", "09:00")

    agent = get_agent(config)
    reporter = Reporter(
        reports_dir=config.get("settings", {}).get("reports", {}).get("path", "reports")
    )

    def weekly_task():
        result = agent.run()
        reporter.generate_weekly_report(
            database=agent.database,
            run_stats=result,
            agent_summary=result.get("final_summary", ""),
        )

    scheduler = WeeklyScheduler(weekly_task, day=day, run_time=run_time)

    if args.now:
        console.print("[bold yellow]Ejecutando inmediatamente (--now)[/bold yellow]")
        scheduler.run_now()
    else:
        console.print(
            f"[bold green]Planificador activo[/bold green] — "
            f"Próxima ejecución: {scheduler.get_next_run()}"
        )
        console.print("Pulsa [bold]Ctrl+C[/bold] para detener.\n")
        scheduler.start()


def cmd_report(args, config: dict) -> None:
    """Genera un reporte con las ofertas actuales."""
    from noelia.storage import Database
    from noelia.reporter import Reporter

    db_path = config.get("settings", {}).get("database", {}).get("path", "data/noelia.db")
    reports_dir = config.get("settings", {}).get("reports", {}).get("path", "reports")

    db = Database(db_path)
    reporter = Reporter(reports_dir)

    path = reporter.generate_weekly_report(database=db)
    console.print(f"[bold green]✅ Reporte generado:[/bold green] {path}")


def cmd_stats(args, config: dict) -> None:
    """Muestra estadísticas de la base de datos."""
    from noelia.storage import Database

    db_path = config.get("settings", {}).get("database", {}).get("path", "data/noelia.db")
    db = Database(db_path)
    stats = db.get_stats()

    console.rule("[bold]📊 Estadísticas de Noelia Sintética")
    console.print(f"\n[bold]Total ofertas:[/bold] {stats['total']}")
    console.print(f"[bold]Nuevas esta semana:[/bold] {stats['new_this_week']}\n")

    if stats["by_platform"]:
        table = Table(title="Por plataforma")
        table.add_column("Plataforma", style="cyan")
        table.add_column("Ofertas", justify="right", style="green")
        for row in stats["by_platform"]:
            table.add_row(row["platform"] or "otras", str(row["c"]))
        console.print(table)

    if stats["top_companies"]:
        table = Table(title="Top 10 empresas")
        table.add_column("Empresa", style="cyan")
        table.add_column("Ofertas", justify="right", style="green")
        for row in stats["top_companies"]:
            table.add_row(row["company"], str(row["c"]))
        console.print(table)


def cmd_jobs(args, config: dict) -> None:
    """Lista las ofertas de la base de datos."""
    from noelia.storage import Database

    db_path = config.get("settings", {}).get("database", {}).get("path", "data/noelia.db")
    db = Database(db_path)

    jobs = db.get_jobs(only_new=args.new, limit=args.limit)

    title = f"{'Nuevas ofertas' if args.new else 'Todas las ofertas'} ({len(jobs)})"
    table = Table(title=title, show_lines=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("Título", style="bold", max_width=45)
    table.add_column("Empresa", max_width=25)
    table.add_column("Plataforma", style="cyan", width=12)
    table.add_column("Ubicación", max_width=20)
    table.add_column("Fecha", width=10)

    for i, job in enumerate(jobs, 1):
        table.add_row(
            str(i),
            job.get("title", "")[:44],
            job.get("company", "")[:24],
            job.get("platform", "") or "—",
            job.get("location", "") or "—",
            job.get("date_found", "")[:10],
        )

    console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Noelia Sintética — Monitorización semanal de ofertas de empleo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = subparsers.add_parser("run", help="Monitorización completa ahora")
    p_run.set_defaults(func=cmd_run)

    # search
    p_search = subparsers.add_parser("search", help="Búsqueda rápida de una keyword")
    p_search.add_argument("keyword", nargs="+", help="Palabras clave a buscar")
    p_search.add_argument("--location", "-l", default="España", help="Ubicación")
    p_search.set_defaults(func=cmd_search)

    # schedule
    p_sched = subparsers.add_parser("schedule", help="Iniciar planificador semanal")
    p_sched.add_argument("--now", action="store_true", help="Ejecutar también ahora mismo")
    p_sched.set_defaults(func=cmd_schedule)

    # report
    p_report = subparsers.add_parser("report", help="Generar reporte con ofertas actuales")
    p_report.set_defaults(func=cmd_report)

    # stats
    p_stats = subparsers.add_parser("stats", help="Estadísticas de la base de datos")
    p_stats.set_defaults(func=cmd_stats)

    # jobs
    p_jobs = subparsers.add_parser("jobs", help="Listar ofertas")
    p_jobs.add_argument("--new", action="store_true", help="Solo mostrar ofertas nuevas")
    p_jobs.add_argument("--limit", type=int, default=50, help="Máximo de ofertas a mostrar")
    p_jobs.set_defaults(func=cmd_jobs)

    args = parser.parse_args()
    config = load_config()
    args.func(args, config)


if __name__ == "__main__":
    main()
