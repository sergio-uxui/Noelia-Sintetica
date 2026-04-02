"""
Agente principal de Noelia Sintética.
Usa Claude claude-opus-4-6 con herramientas (tool use) para orquestar la monitorización
semanal de ofertas de empleo en redes sociales, páginas de empresas y plataformas.
"""

import json
import logging
import os
from datetime import date
from typing import Any

import anthropic

from .tools.scraper import WebScraper
from .tools.platforms import PlatformSearcher
from .tools.tool_definitions import get_tool_definitions, execute_tool
from .storage.database import Database

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Eres Noelia Sintética, una agente de IA especializada en monitorización
de ofertas de empleo en España. Tu misión es:

1. **Revisar las páginas de empleo** de las empresas configuradas.
2. **Buscar en plataformas** (InfoJobs, LinkedIn, Indeed, Tecnoempleo, Glassdoor) usando
   las palabras clave configuradas.
3. **Filtrar y guardar** las ofertas relevantes, evitando duplicados.
4. **Proporcionar un resumen claro** de lo encontrado.

## Flujo de trabajo recomendado:
1. Primero llama a `get_companies_config` y `get_search_keywords` para saber qué buscar.
2. Llama a `get_existing_job_urls` para conocer las URLs ya guardadas.
3. Para cada empresa, llama a `fetch_web_page` con su `career_url`.
4. Busca en plataformas con `search_all_platforms` para cada keyword importante.
5. Filtra los resultados: elimina las URLs ya existentes.
6. Guarda las nuevas ofertas con `save_jobs`.
7. Termina con un resumen en español de lo que encontraste.

## Criterios de relevancia:
- Prioriza ofertas de tecnología, digital, datos, diseño y producto.
- Descarta ofertas claramente irrelevantes (comerciales, administrativos básicos, etc.)
- Si una oferta tiene información ambigua, inclúyela con el tag "revisar".

## Formato de resumen final:
Al terminar, proporciona un resumen con:
- Total de ofertas encontradas y cuántas son nuevas
- Top 5 ofertas más interesantes con empresa, puesto y URL
- Empresas que tienen más ofertas activas
- Plataformas con más actividad esta semana
"""


class NoeliAgent:
    """
    Agente orquestador de monitorización de empleo.
    Implementa un loop de tool use con Claude claude-opus-4-6.
    """

    MAX_TURNS = 40  # Límite de seguridad para el loop

    def __init__(
        self,
        api_key: str | None = None,
        db_path: str = "data/noelia.db",
        config: dict | None = None,
    ):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        )
        self.database = Database(db_path)
        self.scraper = WebScraper(delay=2.5, timeout=20)
        self.platform_searcher = PlatformSearcher(delay=2.0)
        self.config = config or {}
        self.tools = get_tool_definitions()

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Despacha una llamada a herramienta y devuelve el resultado como string."""
        logger.info("Herramienta: %s | args: %s", tool_name, list(tool_input.keys()))
        return execute_tool(
            tool_name,
            tool_input,
            scraper=self.scraper,
            platform_searcher=self.platform_searcher,
            database=self.database,
            config=self.config,
        )

    def run(self, extra_instructions: str = "") -> dict[str, Any]:
        """
        Ejecuta el ciclo completo de monitorización semanal.
        Devuelve un dict con el resumen de la ejecución.
        """
        today = date.today().strftime("%A, %d de %B de %Y")
        prompt = (
            f"Hoy es {today}. "
            "Ejecuta la monitorización semanal completa de ofertas de empleo. "
            "Revisa todas las empresas configuradas, busca en todas las plataformas "
            "con las keywords configuradas, filtra duplicados y guarda las ofertas nuevas."
        )
        if extra_instructions:
            prompt += f"\n\nInstrucciones adicionales: {extra_instructions}"

        messages: list[dict] = [{"role": "user", "content": prompt}]
        turns = 0
        final_summary = ""
        total_tool_calls = 0

        logger.info("Iniciando monitorización semanal con Claude claude-opus-4-6…")

        while turns < self.MAX_TURNS:
            turns += 1
            logger.debug("Turno %d/%d", turns, self.MAX_TURNS)

            response = self.client.messages.create(
                model="claude-opus-4-6",
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                tools=self.tools,
                thinking={"type": "adaptive"},
                messages=messages,
            )

            # Añadir respuesta del asistente al historial
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                # Claude ha terminado — extraer texto final
                for block in response.content:
                    if hasattr(block, "type") and block.type == "text":
                        final_summary = block.text
                logger.info("Agente completó la monitorización en %d turnos.", turns)
                break

            if response.stop_reason == "tool_use":
                # Ejecutar herramientas solicitadas
                tool_results = []
                for block in response.content:
                    if not (hasattr(block, "type") and block.type == "tool_use"):
                        continue

                    total_tool_calls += 1
                    result_str = self._execute_tool(block.name, block.input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

                messages.append({"role": "user", "content": tool_results})

            else:
                # stop_reason inesperado
                logger.warning("stop_reason inesperado: %s", response.stop_reason)
                break

        if turns >= self.MAX_TURNS:
            logger.warning("Alcanzado límite de turnos (%d).", self.MAX_TURNS)

        stats = self.database.get_stats()
        return {
            "success": True,
            "turns": turns,
            "tool_calls": total_tool_calls,
            "final_summary": final_summary,
            "db_stats": stats,
        }

    def run_quick_search(self, keyword: str, location: str = "España") -> dict:
        """
        Búsqueda rápida de una keyword específica en todas las plataformas.
        No requiere configuración previa.
        """
        prompt = (
            f"Busca ofertas de empleo para '{keyword}' en {location}. "
            "Usa search_all_platforms, filtra duplicados y guarda las nuevas con save_jobs. "
            "Muestra un resumen de los mejores resultados."
        )
        messages: list[dict] = [{"role": "user", "content": prompt}]
        turns = 0
        final_summary = ""

        while turns < 15:
            turns += 1
            response = self.client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=self.tools,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "type") and block.type == "text":
                        final_summary = block.text
                break

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if hasattr(block, "type") and block.type == "tool_use":
                        result_str = self._execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        })
                messages.append({"role": "user", "content": tool_results})
            else:
                break

        return {"summary": final_summary, "turns": turns}
