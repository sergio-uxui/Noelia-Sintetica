"""
Generador de reportes semanales de Noelia Sintética.
Produce un informe en Markdown con las ofertas nuevas encontradas esa semana.
"""

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Reporter:
    """Genera reportes Markdown con las ofertas de empleo de la semana."""

    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_weekly_report(
        self,
        database,
        run_stats: Optional[dict] = None,
        agent_summary: str = "",
    ) -> str:
        """
        Genera el reporte semanal y lo guarda en disco.
        Devuelve la ruta del fichero generado.
        """
        today = date.today()
        jobs = database.get_jobs(only_new=True, limit=500)
        db_stats = database.get_stats()

        report = self._build_report(today, jobs, db_stats, run_stats, agent_summary)

        filename = f"reporte_{today.isoformat()}.md"
        path = self.reports_dir / filename
        path.write_text(report, encoding="utf-8")

        logger.info("Reporte generado: %s (%d nuevas ofertas)", path, len(jobs))
        return str(path)

    def _build_report(
        self,
        today: date,
        new_jobs: list[dict],
        db_stats: dict,
        run_stats: Optional[dict],
        agent_summary: str,
    ) -> str:
        lines = []

        # Cabecera
        lines += [
            f"# 📋 Reporte semanal de empleo — {today.strftime('%d/%m/%Y')}",
            "",
            f"> Generado por **Noelia Sintética** el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}",
            "",
        ]

        # Resumen ejecutivo
        lines += [
            "## Resumen ejecutivo",
            "",
            f"- **Ofertas nuevas esta semana:** {len(new_jobs)}",
            f"- **Total acumulado en base de datos:** {db_stats.get('total', 0)}",
        ]
        if run_stats:
            lines += [
                f"- **Empresas revisadas:** {run_stats.get('companies_checked', '—')}",
                f"- **Plataformas consultadas:** {run_stats.get('platforms_checked', '—')}",
                f"- **Llamadas a herramientas:** {run_stats.get('tool_calls', '—')}",
            ]
        lines.append("")

        # Resumen del agente
        if agent_summary:
            lines += [
                "## 🤖 Análisis del agente",
                "",
                agent_summary,
                "",
            ]

        # Nuevas ofertas por plataforma
        if new_jobs:
            by_platform: dict[str, list] = {}
            for job in new_jobs:
                p = job.get("platform") or "otras"
                by_platform.setdefault(p, []).append(job)

            lines += ["## 🆕 Nuevas ofertas por plataforma", ""]

            for platform, jobs in sorted(by_platform.items(), key=lambda x: -len(x[1])):
                lines += [
                    f"### {_platform_emoji(platform)} {platform.capitalize()} ({len(jobs)} ofertas)",
                    "",
                ]
                for job in jobs[:30]:  # Máximo 30 por plataforma en el reporte
                    title = job.get("title", "Sin título")
                    company = job.get("company", "Empresa desconocida")
                    location = job.get("location", "")
                    url = job.get("url", "")
                    salary = job.get("salary", "")
                    modality = job.get("modality", "")
                    tags = job.get("tags", [])
                    date_posted = job.get("date_posted", "")

                    meta_parts = []
                    if location:
                        meta_parts.append(f"📍 {location}")
                    if modality:
                        meta_parts.append(f"🏠 {modality}")
                    if salary:
                        meta_parts.append(f"💰 {salary}")
                    if date_posted:
                        meta_parts.append(f"📅 {date_posted}")

                    meta = " | ".join(meta_parts) if meta_parts else ""
                    tag_str = " ".join(f"`{t}`" for t in tags[:6]) if tags else ""

                    lines += [
                        f"#### [{title}]({url})",
                        f"**{company}**",
                    ]
                    if meta:
                        lines.append(f"_{meta}_")
                    if tag_str:
                        lines.append(tag_str)
                    lines.append("")

        else:
            lines += [
                "## Nuevas ofertas",
                "",
                "_No se encontraron ofertas nuevas esta semana._",
                "",
            ]

        # Estadísticas de la base de datos
        lines += [
            "---",
            "",
            "## 📊 Estadísticas acumuladas",
            "",
        ]

        # Por plataforma
        if db_stats.get("by_platform"):
            lines += ["### Por plataforma", ""]
            lines.append("| Plataforma | Ofertas |")
            lines.append("|:-----------|--------:|")
            for row in db_stats["by_platform"]:
                p = row.get("platform") or "otras"
                lines.append(f"| {_platform_emoji(p)} {p.capitalize()} | {row['c']} |")
            lines.append("")

        # Por estado
        if db_stats.get("by_status"):
            lines += ["### Por estado", ""]
            lines.append("| Estado | Ofertas |")
            lines.append("|:-------|--------:|")
            for row in db_stats["by_status"]:
                lines.append(f"| {_status_emoji(row['status'])} {row['status'].capitalize()} | {row['c']} |")
            lines.append("")

        # Top empresas
        if db_stats.get("top_companies"):
            lines += ["### Empresas con más ofertas (top 10)", ""]
            lines.append("| Empresa | Ofertas |")
            lines.append("|:--------|--------:|")
            for row in db_stats["top_companies"]:
                lines.append(f"| {row['company']} | {row['c']} |")
            lines.append("")

        lines += [
            "---",
            "",
            "_Reporte generado automáticamente por [Noelia Sintética](https://github.com/sergio-uxui/noelia-sintetica)_",
        ]

        return "\n".join(lines)

    def list_reports(self) -> list[str]:
        """Devuelve la lista de reportes disponibles ordenados por fecha."""
        return sorted(
            [str(p) for p in self.reports_dir.glob("reporte_*.md")],
            reverse=True,
        )


def _platform_emoji(platform: str) -> str:
    emojis = {
        "infojobs": "💼",
        "linkedin": "🔵",
        "indeed": "🔍",
        "tecnoempleo": "💻",
        "glassdoor": "🚪",
        "empresa": "🏢",
        "otras": "📌",
    }
    return emojis.get(platform.lower(), "📌")


def _status_emoji(status: str) -> str:
    emojis = {
        "nueva": "🆕",
        "vista": "👁️",
        "guardada": "⭐",
        "descartada": "🗑️",
        "aplicada": "✅",
    }
    return emojis.get(status.lower(), "•")
