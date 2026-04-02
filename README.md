# 🤖 Noelia Sintética

**Agente de IA para monitorización semanal de ofertas de empleo en moda y cine/TV.**

Noelia Sintética busca trabajo para **Noelia Arias** — Fashion Designer y Project Manager
de vestuario para cine y TV (Peris Costumes · La Casa del Dragón · Outlander · Wicked…).

El agente, basado en **Claude claude-opus-4-6** (Anthropic), cada semana:

1. Revisa las **páginas de empleo** de productoras, marcas de moda y medios configurados
2. Busca en **LinkedIn, InfoJobs, Indeed y Glassdoor** con keywords del sector moda/cine/TV
3. **Filtra por relevancia** usando el perfil de Noelia (vestuario, estilismo, diseño, patronaje)
4. Deduplica, guarda las ofertas en SQLite y **clasifica por encaje** (top / interesante / revisar)
5. Genera un **reporte Markdown** semanal con las mejores oportunidades

---

## Estructura del proyecto

```
noelia-sintetica/
├── noelia/
│   ├── agent.py          # Agente Claude con loop de tool use
│   ├── reporter.py       # Generador de reportes Markdown
│   ├── scheduler.py      # Planificador semanal
│   ├── tools/
│   │   ├── scraper.py        # Scraping de páginas corporativas
│   │   ├── platforms.py      # Búsqueda en InfoJobs/LinkedIn/Indeed/…
│   │   └── tool_definitions.py  # Esquemas JSON para Claude
│   └── storage/
│       └── database.py   # Capa SQLite
├── config/
│   ├── companies.yaml    # Empresas a monitorizar
│   └── settings.yaml     # Configuración general
├── reports/              # Reportes generados (Markdown)
├── data/                 # Base de datos SQLite (auto-creada)
├── main.py               # CLI principal
├── requirements.txt
└── .env.example
```

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/sergio-uxui/noelia-sintetica
cd noelia-sintetica

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env y añadir tu ANTHROPIC_API_KEY
```

---

## Dashboard web

```bash
streamlit run dashboard/app.py
```

Abre `http://localhost:8501` en el navegador.

### Páginas del dashboard

| Página | Descripción |
|:-------|:------------|
| 🏠 **Dashboard** | KPIs, gráficos de plataforma/estado, nuevas ofertas de la semana |
| 💼 **Ofertas** | Tabla completa con filtros por plataforma, empresa, estado y tag. Cambio de estado, exportación CSV |
| 🤖 **Agente** | Lanzar monitorización completa o búsqueda rápida. Log en tiempo real. Historial de ejecuciones |
| 📋 **Reportes** | Ver y descargar los reportes Markdown semanales generados |
| ⚙️ **Configuración** | Vista de empresas, keywords, planificador y perfil de candidata |

---

## Uso (CLI)

### Monitorización completa (ahora)

```bash
python main.py run
```

Ejecuta el ciclo completo: revisa empresas, busca en plataformas, guarda nuevas ofertas y genera el reporte semanal.

### Búsqueda rápida

```bash
python main.py search "python developer" --location Madrid
python main.py search "UX designer"
```

### Planificador semanal (proceso en segundo plano)

```bash
# Iniciar planificador (se ejecuta cada lunes a las 9:00)
python main.py schedule

# Ejecutar también ahora mismo y luego quedar planificado
python main.py schedule --now
```

### Generar reporte

```bash
python main.py report
```

Genera un reporte Markdown con todas las ofertas actuales en `reports/`.

### Ver estadísticas

```bash
python main.py stats
```

### Listar ofertas

```bash
python main.py jobs           # Todas las ofertas
python main.py jobs --new     # Solo las nuevas esta semana
python main.py jobs --limit 100
```

---

## Configuración

### Empresas a monitorizar (`config/companies.yaml`)

```yaml
companies:
  - name: "Telefónica"
    career_url: "https://www.telefonica.com/es/empleo/"
    social_linkedin: "https://www.linkedin.com/company/telefonica/jobs/"
    keywords: ["desarrollador", "engineer"]
```

### Búsqueda en plataformas (`config/settings.yaml`)

```yaml
search:
  keywords:
    - "python developer"
    - "data engineer"
    - "UX designer"
  locations:
    - "Madrid"
    - "Barcelona"
    - "España"
```

---

## Cómo funciona el agente

Noelia usa el **loop de tool use** de Claude claude-opus-4-6:

```
Usuario → Claude → [herramienta] → Claude → [herramienta] → … → Respuesta final
```

Las herramientas disponibles para Claude son:

| Herramienta | Descripción |
|:------------|:------------|
| `fetch_web_page` | Descarga y extrae texto de una URL |
| `search_job_platform` | Busca en una plataforma específica |
| `search_all_platforms` | Busca en todas las plataformas a la vez |
| `save_jobs` | Guarda ofertas en la base de datos |
| `get_existing_job_urls` | Obtiene URLs ya guardadas (deduplicación) |
| `get_database_stats` | Estadísticas de la BD |
| `get_companies_config` | Lista de empresas configuradas |
| `get_search_keywords` | Keywords y ubicaciones configuradas |

---

## Reportes

Los reportes se guardan en `reports/reporte_YYYY-MM-DD.md` con:

- Resumen ejecutivo (nuevas ofertas, empresas/plataformas revisadas)
- Análisis del agente (síntesis de Claude)
- Ofertas nuevas organizadas por plataforma
- Estadísticas acumuladas (por plataforma, estado y empresa)

---

## Licencia

MIT
