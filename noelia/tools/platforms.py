"""
Buscador en plataformas de empleo: InfoJobs, LinkedIn Jobs, Indeed, Tecnoempleo, Glassdoor.
Construye URLs de búsqueda y extrae resultados mediante scraping del HTML público.
"""

import re
import time
import logging
from urllib.parse import quote_plus, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}


def _get(url: str, timeout: int = 15) -> tuple[str, int]:
    """Petición GET simple con manejo de errores."""
    try:
        with httpx.Client(headers=HEADERS, timeout=timeout, follow_redirects=True) as client:
            r = client.get(url)
            return r.text, r.status_code
    except Exception as exc:
        logger.error("Error al obtener %s: %s", url, exc)
        return "", 0


class PlatformSearcher:
    """Busca ofertas en plataformas de empleo mediante scraping del HTML público."""

    def __init__(self, delay: float = 2.0):
        self.delay = delay

    def _sleep(self) -> None:
        time.sleep(self.delay)

    # ------------------------------------------------------------------ #
    # InfoJobs                                                             #
    # ------------------------------------------------------------------ #

    def search_infojobs(self, keyword: str, location: str = "España") -> list[dict]:
        """Busca en InfoJobs.net. Extrae hasta 20 resultados."""
        url = (
            f"https://www.infojobs.net/jobsearch/search-results/list.xhtml"
            f"?keyword={quote_plus(keyword)}&normalizedJobCity={quote_plus(location)}"
        )
        html, status = _get(url)
        self._sleep()

        if not html or status >= 400:
            return []

        soup = BeautifulSoup(html, "lxml")
        jobs = []

        for item in soup.select(".ij-OfferCardContent, [data-jobad], .sui-AtomCard")[:20]:
            title_elem = item.select_one("h2 a, .ij-OfferCardContent-description-title a, a.h4")
            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            href = title_elem.get("href", "")
            job_url = urljoin("https://www.infojobs.net", href)

            company_elem = item.select_one(
                ".ij-OfferCardContent-description-subtitle, "
                "[class*='company'], .company"
            )
            company = company_elem.get_text(strip=True) if company_elem else ""

            location_elem = item.select_one(
                "[class*='location'], .ij-OfferCardContent-location"
            )
            location_text = location_elem.get_text(strip=True) if location_elem else ""

            jobs.append({
                "url": job_url,
                "title": title[:200],
                "company": company[:100],
                "location": location_text[:100],
                "platform": "infojobs",
            })

        return jobs

    # ------------------------------------------------------------------ #
    # LinkedIn Jobs                                                        #
    # ------------------------------------------------------------------ #

    def search_linkedin(self, keyword: str, location: str = "Spain") -> list[dict]:
        """Busca en LinkedIn Jobs (búsqueda pública, sin autenticación)."""
        url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={quote_plus(keyword)}"
            f"&location={quote_plus(location)}"
            f"&f_TPR=r604800"  # Últimos 7 días
        )
        html, status = _get(url)
        self._sleep()

        if not html or status >= 400:
            return []

        soup = BeautifulSoup(html, "lxml")
        jobs = []

        for card in soup.select(
            ".base-card, .jobs-search__results-list li, "
            "[class*='job-search-card'], [class*='base-job-card']"
        )[:20]:
            title_elem = card.select_one(
                "h3.base-search-card__title, "
                ".job-search-card__title, "
                "h3 a, h3"
            )
            link_elem = card.select_one("a.base-card__full-link, a[href*='/jobs/view/']")

            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            job_url = link_elem.get("href", "") if link_elem else ""
            if job_url and not job_url.startswith("http"):
                job_url = urljoin("https://www.linkedin.com", job_url)

            company_elem = card.select_one(
                "h4.base-search-card__subtitle, "
                ".job-search-card__company-name, "
                "h4 a, h4"
            )
            company = company_elem.get_text(strip=True) if company_elem else ""

            location_elem = card.select_one(
                "span.job-search-card__location, "
                "[class*='location']"
            )
            loc = location_elem.get_text(strip=True) if location_elem else ""

            if title and job_url:
                jobs.append({
                    "url": job_url,
                    "title": title[:200],
                    "company": company[:100],
                    "location": loc[:100],
                    "platform": "linkedin",
                })

        return jobs

    # ------------------------------------------------------------------ #
    # Indeed España                                                        #
    # ------------------------------------------------------------------ #

    def search_indeed(self, keyword: str, location: str = "España") -> list[dict]:
        """Busca en Indeed España."""
        url = (
            f"https://es.indeed.com/jobs"
            f"?q={quote_plus(keyword)}"
            f"&l={quote_plus(location)}"
            f"&fromage=14"  # Últimos 14 días
        )
        html, status = _get(url)
        self._sleep()

        if not html or status >= 400:
            return []

        soup = BeautifulSoup(html, "lxml")
        jobs = []

        for card in soup.select(
            ".job_seen_beacon, [class*='result '], "
            ".jobsearch-ResultsList > li"
        )[:20]:
            title_elem = card.select_one(
                "h2.jobTitle span, h2 a, [id^='jobTitle']"
            )
            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            link_elem = card.select_one("h2 a, a[id^='job_']")
            href = link_elem.get("href", "") if link_elem else ""
            job_url = urljoin("https://es.indeed.com", href)

            company_elem = card.select_one(
                "[class*='companyName'], span[class*='company']"
            )
            company = company_elem.get_text(strip=True) if company_elem else ""

            location_elem = card.select_one(
                "[class*='companyLocation'], div[class*='location']"
            )
            loc = location_elem.get_text(strip=True) if location_elem else ""

            if title and job_url:
                jobs.append({
                    "url": job_url,
                    "title": title[:200],
                    "company": company[:100],
                    "location": loc[:100],
                    "platform": "indeed",
                })

        return jobs

    # ------------------------------------------------------------------ #
    # Tecnoempleo                                                          #
    # ------------------------------------------------------------------ #

    def search_tecnoempleo(self, keyword: str, location: str = "") -> list[dict]:
        """Busca en Tecnoempleo (especializado en tecnología)."""
        url = (
            f"https://www.tecnoempleo.com/busqueda-empleo.php"
            f"?te={quote_plus(keyword)}"
            + (f"&pr={quote_plus(location)}" if location else "")
        )
        html, status = _get(url)
        self._sleep()

        if not html or status >= 400:
            return []

        soup = BeautifulSoup(html, "lxml")
        jobs = []

        for card in soup.select(".oferta, article.oferta, [class*='oferta']")[:20]:
            title_elem = card.select_one("h3 a, h2 a, .titulo a")
            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            href = title_elem.get("href", "")
            job_url = urljoin("https://www.tecnoempleo.com", href)

            company_elem = card.select_one(".empresa, [class*='company']")
            company = company_elem.get_text(strip=True) if company_elem else ""

            location_elem = card.select_one(".ubicacion, [class*='location']")
            loc = location_elem.get_text(strip=True) if location_elem else ""

            if title and job_url:
                jobs.append({
                    "url": job_url,
                    "title": title[:200],
                    "company": company[:100],
                    "location": loc[:100],
                    "platform": "tecnoempleo",
                })

        return jobs

    # ------------------------------------------------------------------ #
    # Glassdoor España                                                     #
    # ------------------------------------------------------------------ #

    def search_glassdoor(self, keyword: str, location: str = "España") -> list[dict]:
        """Busca en Glassdoor Jobs."""
        url = (
            f"https://www.glassdoor.es/Empleo/{quote_plus(location)}-"
            f"{quote_plus(keyword)}-empleos-SRCH_IL.0,6_IN219_KO7,"
            f"{7 + len(keyword)}.htm"
        )
        html, status = _get(url)
        self._sleep()

        if not html or status >= 400:
            return []

        soup = BeautifulSoup(html, "lxml")
        jobs = []

        for card in soup.select(
            "[data-jobid], li[class*='react-job-listing'], "
            "[class*='JobCard']"
        )[:20]:
            title_elem = card.select_one(
                "a[class*='jobLink'], [class*='job-title'], h3 a, [data-test='job-link']"
            )
            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            href = title_elem.get("href", "")
            job_url = urljoin("https://www.glassdoor.es", href)

            company_elem = card.select_one(
                "[class*='employer-name'], [class*='EmployerName'], "
                "[data-test='employer-name']"
            )
            company = company_elem.get_text(strip=True) if company_elem else ""

            location_elem = card.select_one("[class*='location'], [data-test='emp-location']")
            loc = location_elem.get_text(strip=True) if location_elem else ""

            if title and job_url:
                jobs.append({
                    "url": job_url,
                    "title": title[:200],
                    "company": company[:100],
                    "location": loc[:100],
                    "platform": "glassdoor",
                })

        return jobs

    # ------------------------------------------------------------------ #
    # Búsqueda unificada                                                   #
    # ------------------------------------------------------------------ #

    def search_all(
        self,
        keyword: str,
        location: str = "España",
        platforms: list[str] | None = None,
    ) -> dict:
        """
        Busca en todas las plataformas habilitadas.
        Devuelve un dict con resultados por plataforma y el total.
        """
        available = {
            "infojobs": self.search_infojobs,
            "linkedin": self.search_linkedin,
            "indeed": self.search_indeed,
            "tecnoempleo": self.search_tecnoempleo,
            "glassdoor": self.search_glassdoor,
        }

        enabled = platforms or list(available.keys())
        results: dict[str, list] = {}
        total = 0

        for name in enabled:
            if name not in available:
                continue
            try:
                logger.info("Buscando '%s' en %s…", keyword, name)
                jobs = available[name](keyword, location)
                results[name] = jobs
                total += len(jobs)
                logger.info("  → %d resultados en %s", len(jobs), name)
            except Exception as exc:
                logger.error("Error buscando en %s: %s", name, exc)
                results[name] = []

        return {
            "keyword": keyword,
            "location": location,
            "results_by_platform": results,
            "total_jobs": total,
        }
