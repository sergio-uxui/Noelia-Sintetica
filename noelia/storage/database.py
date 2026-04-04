"""
Capa de almacenamiento SQLite para Noelia Sintética.
Gestiona las ofertas de empleo encontradas, su estado y el historial de ejecuciones.
"""

import sqlite3
import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional


class Database:
    """Gestiona la base de datos SQLite de ofertas de empleo."""

    def __init__(self, db_path: str = "data/noelia.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        """Crea las tablas si no existen."""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    url         TEXT    UNIQUE NOT NULL,
                    title       TEXT    NOT NULL,
                    company     TEXT    NOT NULL,
                    location    TEXT,
                    platform    TEXT,
                    description TEXT,
                    salary      TEXT,
                    modality    TEXT,
                    tags        TEXT,           -- JSON array de etiquetas
                    date_posted TEXT,           -- Fecha publicación (ISO 8601)
                    date_found  TEXT    NOT NULL,
                    is_new      INTEGER DEFAULT 1,   -- 1 si es nueva esta semana
                    status      TEXT    DEFAULT 'nueva',
                    -- Estados: nueva, vista, guardada, descartada, aplicada
                    notes       TEXT,
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS runs (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at      TEXT NOT NULL,
                    finished_at     TEXT,
                    jobs_found      INTEGER DEFAULT 0,
                    jobs_new        INTEGER DEFAULT 0,
                    companies_checked INTEGER DEFAULT 0,
                    platforms_checked INTEGER DEFAULT 0,
                    status          TEXT DEFAULT 'running',  -- running, completed, failed
                    error_message   TEXT,
                    report_path     TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_company   ON jobs(company);
                CREATE INDEX IF NOT EXISTS idx_jobs_platform  ON jobs(platform);
                CREATE INDEX IF NOT EXISTS idx_jobs_date_found ON jobs(date_found);
                CREATE INDEX IF NOT EXISTS idx_jobs_status    ON jobs(status);
                CREATE INDEX IF NOT EXISTS idx_jobs_is_new    ON jobs(is_new);
            """)

    # ------------------------------------------------------------------ #
    # Jobs                                                                 #
    # ------------------------------------------------------------------ #

    def save_job(self, job: dict) -> tuple[bool, int]:
        """
        Guarda una oferta. Devuelve (is_new, job_id).
        Si la URL ya existe, actualiza el título/descripción pero no la marca como nueva.
        """
        tags_json = json.dumps(job.get("tags", []), ensure_ascii=False)
        date_found = date.today().isoformat()

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM jobs WHERE url = ?", (job["url"],)
            ).fetchone()

            if existing:
                conn.execute(
                    """UPDATE jobs
                       SET title       = ?,
                           description = ?,
                           salary      = ?,
                           tags        = ?,
                           updated_at  = datetime('now')
                       WHERE url = ?""",
                    (
                        job.get("title", ""),
                        job.get("description", ""),
                        job.get("salary", ""),
                        tags_json,
                        job["url"],
                    ),
                )
                return False, existing["id"]

            cursor = conn.execute(
                """INSERT INTO jobs
                   (url, title, company, location, platform, description,
                    salary, modality, tags, date_posted, date_found)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job["url"],
                    job.get("title", "Sin título"),
                    job.get("company", "Desconocida"),
                    job.get("location", ""),
                    job.get("platform", ""),
                    job.get("description", ""),
                    job.get("salary", ""),
                    job.get("modality", ""),
                    tags_json,
                    job.get("date_posted", ""),
                    date_found,
                ),
            )
            return True, cursor.lastrowid

    def save_jobs(self, jobs: list[dict]) -> dict:
        """Guarda múltiples ofertas. Devuelve estadísticas."""
        new_count = 0
        updated_count = 0
        for job in jobs:
            is_new, _ = self.save_job(job)
            if is_new:
                new_count += 1
            else:
                updated_count += 1
        return {"new": new_count, "updated": updated_count, "total": len(jobs)}

    def get_jobs(
        self,
        only_new: bool = False,
        company: Optional[str] = None,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 200,
    ) -> list[dict]:
        """Recupera ofertas con filtros opcionales."""
        filters = []
        params: list = []

        if only_new:
            filters.append("is_new = 1")
        if company:
            filters.append("LOWER(company) LIKE LOWER(?)")
            params.append(f"%{company}%")
        if platform:
            filters.append("platform = ?")
            params.append(platform)
        if status:
            filters.append("status = ?")
            params.append(status)

        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM jobs {where} ORDER BY date_found DESC, id DESC LIMIT ?",
                params,
            ).fetchall()

        result = []
        for row in rows:
            job = dict(row)
            job["tags"] = json.loads(job["tags"] or "[]")
            result.append(job)
        return result

    def get_job_urls(self) -> set[str]:
        """Devuelve el conjunto de todas las URLs ya guardadas (para deduplicar)."""
        with self._connect() as conn:
            rows = conn.execute("SELECT url FROM jobs").fetchall()
        return {row["url"] for row in rows}

    def update_job_status(self, job_id: int, status: str, notes: str = "") -> None:
        """Actualiza el estado de una oferta (vista, guardada, descartada, aplicada)."""
        with self._connect() as conn:
            conn.execute(
                """UPDATE jobs SET status = ?, notes = ?, updated_at = datetime('now')
                   WHERE id = ?""",
                (status, notes, job_id),
            )

    def mark_all_as_seen(self) -> int:
        """Marca todas las ofertas 'nueva' como vistas. Devuelve número afectado."""
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE jobs SET is_new = 0 WHERE is_new = 1"
            )
            return cursor.rowcount

    def get_stats(self) -> dict:
        """Devuelve estadísticas generales de la base de datos."""
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            new = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE is_new = 1"
            ).fetchone()[0]
            by_platform = conn.execute(
                "SELECT platform, COUNT(*) as c FROM jobs GROUP BY platform ORDER BY c DESC"
            ).fetchall()
            by_status = conn.execute(
                "SELECT status, COUNT(*) as c FROM jobs GROUP BY status"
            ).fetchall()
            by_company = conn.execute(
                "SELECT company, COUNT(*) as c FROM jobs GROUP BY company ORDER BY c DESC LIMIT 10"
            ).fetchall()

        return {
            "total": total,
            "new_this_week": new,
            "by_platform": [dict(r) for r in by_platform],
            "by_status": [dict(r) for r in by_status],
            "top_companies": [dict(r) for r in by_company],
        }

    # ------------------------------------------------------------------ #
    # Runs (historial de ejecuciones)                                      #
    # ------------------------------------------------------------------ #

    def start_run(self) -> int:
        """Registra el inicio de una ejecución. Devuelve run_id."""
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO runs (started_at) VALUES (datetime('now'))"
            )
            return cursor.lastrowid

    def finish_run(self, run_id: int, stats: dict, report_path: str = "") -> None:
        """Registra el fin de una ejecución."""
        with self._connect() as conn:
            conn.execute(
                """UPDATE runs
                   SET finished_at         = datetime('now'),
                       jobs_found          = ?,
                       jobs_new            = ?,
                       companies_checked   = ?,
                       platforms_checked   = ?,
                       status              = 'completed',
                       report_path         = ?
                   WHERE id = ?""",
                (
                    stats.get("jobs_found", 0),
                    stats.get("jobs_new", 0),
                    stats.get("companies_checked", 0),
                    stats.get("platforms_checked", 0),
                    report_path,
                    run_id,
                ),
            )

    def fail_run(self, run_id: int, error: str) -> None:
        """Marca una ejecución como fallida."""
        with self._connect() as conn:
            conn.execute(
                """UPDATE runs
                   SET finished_at   = datetime('now'),
                       status        = 'failed',
                       error_message = ?
                   WHERE id = ?""",
                (error, run_id),
            )

    def get_last_runs(self, limit: int = 10) -> list[dict]:
        """Devuelve el historial de las últimas ejecuciones."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
