"""
Buscador en plataformas de empleo usando SerpApi (Google Jobs).
Google Jobs agrega resultados de LinkedIn, Indeed, InfoJobs, Glassdoor y más,
evitando los bloqueos de scraping directo.

Documentación SerpApi: https://serpapi.com/google-jobs-api
"""

import logging
import time
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


class PlatformSearcher:
    """Busca ofertas de empleo usando SerpApi Google Jobs."""

    def __init__(self, api_key: str, delay: float = 1.0):
        self.api_key = api_key
        self.delay = delay

    def _sleep(self) -> None:
        time.sleep(self.delay)

    # ------------------------------------------------------------------ #
    # Búsqueda base                                                        #
    # ------------------------------------------------------------------ #

    def _search(self, query: str, location: str = "España", num: int = 10) -> list[dict]:
        """Llama a SerpApi Google Jobs y devuelve lista de ofertas parseadas."""
        try:
            import serpapi
        except ImportError:
            logger.error("serpapi no instalado. Ejecuta: pip install serpapi")
            return []

        try:
            results = serpapi.search(
                engine="google_jobs",
                q=query,
                location=location,
                hl="es",
                gl="es",
                num=num,
                api_key=self.api_key,
            )
            data = dict(results)

            if "error" in data:
                logger.error("SerpApi error: %s", data["error"])
                return []

            jobs = self._parse_results(data)
            logger.info("SerpApi '%s' en %s → %d resultados", query, location, len(jobs))
            self._sleep()
            return jobs

        except Exception as exc:
            logger.error("Error llamando a SerpApi: %s", exc)
            return []

    def _parse_results(self, data: dict) -> list[dict]:
        """Convierte la respuesta de SerpApi al formato interno."""
        jobs = []
        for job in data.get("jobs_results", []):
            # Detectar plataforma desde el campo "via"
            via = job.get("via", "").lower()
            platform = "google_jobs"
            if "linkedin" in via:
                platform = "linkedin"
            elif "indeed" in via:
                platform = "indeed"
            elif "infojobs" in via:
                platform = "infojobs"
            elif "glassdoor" in via:
                platform = "glassdoor"
            elif "tecnoempleo" in via:
                platform = "tecnoempleo"

            # URL: preferir related_links, fallback a búsqueda de Google
            url = ""
            for link in job.get("related_links", []):
                if link.get("link"):
                    url = link["link"]
                    break
            if not url:
                title = quote_plus(job.get("title", ""))
                company = quote_plus(job.get("company_name", ""))
                url = f"https://www.google.com/search?q={title}+{company}+empleo"

            ext = job.get("detected_extensions", {})

            jobs.append({
                "url": url,
                "title": job.get("title", "")[:200],
                "company": job.get("company_name", "")[:100],
                "location": job.get("location", "")[:100],
                "platform": platform,
                "description": job.get("description", "")[:1000],
                "salary": ext.get("salary", ""),
                "date_posted": ext.get("posted_at", ""),
                "modality": "remoto" if ext.get("work_from_home") else "",
            })

        return jobs

    # ------------------------------------------------------------------ #
    # API pública (misma interfaz que antes)                               #
    # ------------------------------------------------------------------ #

    def search_infojobs(self, keyword: str, location: str = "España") -> list[dict]:
        return self._search(f"{keyword} InfoJobs", location)

    def search_linkedin(self, keyword: str, location: str = "España") -> list[dict]:
        return self._search(f"{keyword} LinkedIn", location)

    def search_indeed(self, keyword: str, location: str = "España") -> list[dict]:
        return self._search(f"{keyword} Indeed", location)

    def search_tecnoempleo(self, keyword: str, location: str = "") -> list[dict]:
        return self._search(f"{keyword} Tecnoempleo", location or "España")

    def search_glassdoor(self, keyword: str, location: str = "España") -> list[dict]:
        return self._search(f"{keyword} Glassdoor", location)

    def search_company(self, company_name: str, keywords: list[str], location: str = "España") -> list[dict]:
        """Busca ofertas específicas de una empresa."""
        kw = " ".join(keywords[:2]) if keywords else "empleo"
        query = f"{company_name} {kw}"
        return self._search(query, location, num=5)

    def search_all(
        self,
        keyword: str,
        location: str = "España",
        platforms: list[str] | None = None,
    ) -> dict:
        """
        Busca en Google Jobs (agrega resultados de todas las plataformas).
        Devuelve un dict con resultados por plataforma y el total.
        """
        jobs = self._search(keyword, location, num=10)

        # Agrupar por plataforma detectada
        by_platform: dict[str, list] = {}
        for job in jobs:
            p = job["platform"]
            by_platform.setdefault(p, []).append(job)

        return {
            "keyword": keyword,
            "location": location,
            "results_by_platform": by_platform,
            "total_jobs": len(jobs),
            "jobs": jobs,
        }
