"""
Herramienta de scraping web para páginas de empleo de empresas.
Obtiene el HTML de una URL y extrae las ofertas de trabajo con BeautifulSoup.
"""

import re
import time
import logging
from urllib.parse import urljoin, urlparse

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
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "DNT": "1",
}


class WebScraper:
    """Descarga y extrae ofertas de empleo de páginas web corporativas."""

    def __init__(self, delay: float = 2.0, timeout: int = 15, max_retries: int = 3):
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self._last_request: dict[str, float] = {}  # dominio → timestamp

    def _wait_for_domain(self, domain: str) -> None:
        """Respeta el delay entre peticiones al mismo dominio."""
        last = self._last_request.get(domain, 0)
        elapsed = time.time() - last
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def fetch_html(self, url: str) -> tuple[str, int]:
        """
        Descarga el HTML de una URL.
        Devuelve (html_content, status_code).
        Lanza httpx.HTTPError si falla tras los reintentos.
        """
        domain = urlparse(url).netloc
        self._wait_for_domain(domain)

        for attempt in range(self.max_retries):
            try:
                with httpx.Client(
                    headers=HEADERS,
                    timeout=self.timeout,
                    follow_redirects=True,
                ) as client:
                    response = client.get(url)
                    self._last_request[domain] = time.time()
                    return response.text, response.status_code
            except httpx.TimeoutException:
                logger.warning("Timeout en %s (intento %d/%d)", url, attempt + 1, self.max_retries)
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
            except httpx.HTTPError as exc:
                logger.error("Error HTTP en %s: %s", url, exc)
                raise

        raise httpx.TimeoutException(f"Máximos reintentos alcanzados para {url}")

    def extract_text_content(self, html: str, url: str = "") -> str:
        """
        Extrae el texto limpio de una página HTML, eliminando scripts, estilos y
        etiquetas de navegación. Útil para pasar el contenido a Claude.
        """
        soup = BeautifulSoup(html, "lxml")

        # Eliminar elementos no relevantes
        for tag in soup(["script", "style", "nav", "footer", "header",
                          "noscript", "iframe", "img", "svg", "form"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        # Colapsar líneas en blanco múltiples
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:15_000]  # Máximo ~15k caracteres para no saturar contexto

    def extract_job_links(self, html: str, base_url: str) -> list[dict]:
        """
        Heurística para extraer enlaces que parecen ofertas de empleo
        de la página de empleo de una empresa.
        Devuelve lista de {"url": ..., "title": ...}
        """
        soup = BeautifulSoup(html, "lxml")
        job_patterns = re.compile(
            r"(job|empleo|vacante|oferta|posici[oó]n|carrer|work|hire|recruit"
            r"|careers|talent|apply|puesto|plaza)",
            re.IGNORECASE,
        )

        results = []
        seen_urls = set()

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text(strip=True)

            if not href or href.startswith(("#", "javascript:", "mailto:")):
                continue

            full_url = urljoin(base_url, href)

            if full_url in seen_urls:
                continue

            # El enlace o su texto contienen palabras relacionadas con empleo
            if job_patterns.search(text) or job_patterns.search(href):
                seen_urls.add(full_url)
                results.append({"url": full_url, "title": text[:200]})

        return results[:50]  # Máximo 50 por página

    def scrape_career_page(self, url: str, company: str) -> dict:
        """
        Descarga la página de empleo de una empresa y devuelve un resumen
        estructurado para que Claude lo analice.
        """
        try:
            html, status = self.fetch_html(url)
        except Exception as exc:
            return {
                "success": False,
                "url": url,
                "company": company,
                "error": str(exc),
            }

        if status >= 400:
            return {
                "success": False,
                "url": url,
                "company": company,
                "error": f"HTTP {status}",
            }

        text = self.extract_text_content(html, url)
        job_links = self.extract_job_links(html, url)

        return {
            "success": True,
            "url": url,
            "company": company,
            "status_code": status,
            "text_content": text,
            "job_links_found": len(job_links),
            "job_links": job_links[:20],  # Primeros 20 para Claude
        }

    def scrape_job_detail(self, url: str) -> dict:
        """
        Descarga y extrae el detalle de una oferta de empleo individual.
        """
        try:
            html, status = self.fetch_html(url)
        except Exception as exc:
            return {"success": False, "url": url, "error": str(exc)}

        if status >= 400:
            return {"success": False, "url": url, "error": f"HTTP {status}"}

        soup = BeautifulSoup(html, "lxml")

        # Intentar extraer título
        title = ""
        for selector in ["h1", '[class*="job-title"]', '[class*="position"]', "title"]:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)[:300]
                break

        text = self.extract_text_content(html, url)

        return {
            "success": True,
            "url": url,
            "status_code": status,
            "title": title,
            "text_content": text,
        }
