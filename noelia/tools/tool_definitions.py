"""
Definiciones de herramientas para el agente Claude y función de despacho.
Cada herramienta tiene un esquema JSON que Claude usa para llamarla,
y una función Python que la ejecuta.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Esquemas JSON de las herramientas (lo que Claude ve)                #
# ------------------------------------------------------------------ #

TOOL_DEFINITIONS = [
    {
        "name": "fetch_web_page",
        "description": (
            "Descarga el contenido de una URL y devuelve el texto limpio de la página. "
            "Útil para explorar páginas de empleo de empresas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL completa de la página a descargar (debe empezar por https://).",
                },
                "company": {
                    "type": "string",
                    "description": "Nombre de la empresa (para contexto).",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "search_job_platform",
        "description": (
            "Busca ofertas de empleo en una plataforma específica (infojobs, linkedin, "
            "indeed, tecnoempleo o glassdoor). Devuelve una lista de ofertas encontradas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["infojobs", "linkedin", "indeed", "tecnoempleo", "glassdoor"],
                    "description": "Plataforma donde buscar.",
                },
                "keyword": {
                    "type": "string",
                    "description": "Palabras clave de búsqueda (ej: 'python developer', 'UX designer').",
                },
                "location": {
                    "type": "string",
                    "description": "Ubicación (ej: 'Madrid', 'Barcelona', 'España'). Por defecto 'España'.",
                },
            },
            "required": ["platform", "keyword"],
        },
    },
    {
        "name": "search_all_platforms",
        "description": (
            "Busca una palabra clave en TODAS las plataformas de empleo a la vez "
            "(infojobs, linkedin, indeed, tecnoempleo, glassdoor). "
            "Más eficiente que llamar a cada plataforma por separado."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Palabras clave de búsqueda.",
                },
                "location": {
                    "type": "string",
                    "description": "Ubicación. Por defecto 'España'.",
                },
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "save_jobs",
        "description": (
            "Guarda una lista de ofertas de empleo en la base de datos. "
            "Devuelve el número de ofertas nuevas y actualizadas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "jobs": {
                    "type": "array",
                    "description": "Lista de ofertas a guardar.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL única de la oferta (obligatorio)."},
                            "title": {"type": "string", "description": "Título del puesto."},
                            "company": {"type": "string", "description": "Nombre de la empresa."},
                            "location": {"type": "string", "description": "Ubicación del puesto."},
                            "platform": {"type": "string", "description": "Plataforma donde se encontró."},
                            "description": {"type": "string", "description": "Descripción breve."},
                            "salary": {"type": "string", "description": "Salario si está disponible."},
                            "modality": {"type": "string", "description": "Presencial, remoto o híbrido."},
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Etiquetas relevantes (tecnologías, áreas, etc.).",
                            },
                            "date_posted": {"type": "string", "description": "Fecha de publicación (ISO 8601)."},
                        },
                        "required": ["url", "title", "company"],
                    },
                }
            },
            "required": ["jobs"],
        },
    },
    {
        "name": "get_existing_job_urls",
        "description": (
            "Devuelve la lista de URLs de ofertas ya guardadas en la base de datos. "
            "Usa esto para evitar duplicados antes de llamar a save_jobs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_database_stats",
        "description": (
            "Devuelve estadísticas de la base de datos: total de ofertas, "
            "ofertas nuevas esta semana, distribución por plataforma y empresa."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_companies_config",
        "description": (
            "Devuelve la lista de empresas configuradas para monitorizar, "
            "con sus URLs de empleo y palabras clave específicas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_search_keywords",
        "description": (
            "Devuelve las palabras clave de búsqueda y ubicaciones configuradas "
            "para la monitorización de plataformas de empleo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


def get_tool_definitions() -> list[dict]:
    """Devuelve la lista de definiciones de herramientas para la API de Claude."""
    return TOOL_DEFINITIONS


# ------------------------------------------------------------------ #
# Función de despacho                                                  #
# ------------------------------------------------------------------ #

def execute_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    *,
    scraper,
    platform_searcher,
    database,
    config: dict,
) -> str:
    """
    Ejecuta la herramienta indicada con los argumentos dados.
    Devuelve siempre un string (que se pasa como tool_result a Claude).
    """
    try:
        result = _dispatch(
            tool_name,
            tool_input,
            scraper=scraper,
            platform_searcher=platform_searcher,
            database=database,
            config=config,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.exception("Error ejecutando herramienta '%s': %s", tool_name, exc)
        return json.dumps({"error": str(exc), "tool": tool_name}, ensure_ascii=False)


def _dispatch(tool_name, tool_input, *, scraper, platform_searcher, database, config):
    if tool_name == "fetch_web_page":
        return scraper.scrape_career_page(
            url=tool_input["url"],
            company=tool_input.get("company", ""),
        )

    if tool_name == "search_job_platform":
        platform = tool_input["platform"]
        keyword = tool_input["keyword"]
        location = tool_input.get("location", "España")

        method_map = {
            "infojobs": platform_searcher.search_infojobs,
            "linkedin": platform_searcher.search_linkedin,
            "indeed": platform_searcher.search_indeed,
            "tecnoempleo": platform_searcher.search_tecnoempleo,
            "glassdoor": platform_searcher.search_glassdoor,
        }
        if platform not in method_map:
            return {"error": f"Plataforma desconocida: {platform}"}

        jobs = method_map[platform](keyword, location)
        return {"platform": platform, "keyword": keyword, "jobs": jobs, "count": len(jobs)}

    if tool_name == "search_all_platforms":
        keyword = tool_input["keyword"]
        location = tool_input.get("location", "España")
        return platform_searcher.search_all(keyword, location)

    if tool_name == "save_jobs":
        jobs = tool_input["jobs"]
        stats = database.save_jobs(jobs)
        return {"saved": True, **stats}

    if tool_name == "get_existing_job_urls":
        urls = database.get_job_urls()
        return {"urls": list(urls), "count": len(urls)}

    if tool_name == "get_database_stats":
        return database.get_stats()

    if tool_name == "get_companies_config":
        return {
            "companies": config.get("companies", []),
            "count": len(config.get("companies", [])),
        }

    if tool_name == "get_search_keywords":
        settings = config.get("settings", {})
        search = settings.get("search", {})
        return {
            "keywords": search.get("keywords", []),
            "locations": search.get("locations", ["España"]),
            "modality": search.get("modality", "todos"),
            "max_age_days": search.get("max_age_days", 30),
        }

    return {"error": f"Herramienta desconocida: {tool_name}"}
