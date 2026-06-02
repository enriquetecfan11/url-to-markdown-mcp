import asyncio
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, HttpUrl
import httpx
import trafilatura
from mcp.server.fastmcp import FastMCP

# --- MCP setup ---
mcp = FastMCP("url-to-markdown")

# --- FastAPI app ---
app = FastAPI(
    title="URL to Markdown API",
    description="Converts any URL to Markdown. Also exposes an MCP server for AI integrations.",
    version="2.0.0",
)

# Mount MCP with Streamable HTTP transport (compatible with Cursor, Claude, etc.)
mcp_app = mcp.streamable_http_app()
app.mount("/mcp", mcp_app)

# --- User-Agent generico para evitar bloqueos ---
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# --- Schemas ---
class ConvertRequest(BaseModel):
    url: HttpUrl

class ConvertResponse(BaseModel):
    url: str
    markdown: str

class BulkConvertRequest(BaseModel):
    urls: List[str]

class BulkConvertResult(BaseModel):
    url: str
    markdown: str | None
    error: str | None = None


# --- Core async function ---
async def fetch_and_extract(url: str) -> str:
    """Descarga el HTML de una URL de forma asincrona y extrae el Markdown con Trafilatura."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        html = response.text

    markdown = trafilatura.extract(
        html,
        include_links=True,
        include_images=True,
        output_format="markdown",
    )
    if not markdown:
        raise ValueError("No se pudo extraer contenido de la URL")
    return markdown


# --- Endpoints ---

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/convert", response_model=ConvertResponse)
async def convert(request: ConvertRequest):
    """Convierte una URL a Markdown de forma asincrona."""
    url = str(request.url)
    try:
        markdown = await fetch_and_extract(url)
        return ConvertResponse(url=url, markdown=markdown)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Error al obtener la URL: {e}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Error de red: {e}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/convert/bulk")
async def convert_bulk(request: BulkConvertRequest):
    """Convierte multiples URLs a Markdown en paralelo usando asyncio.gather."""
    async def process(url: str) -> BulkConvertResult:
        try:
            # Asegurar que la URL tiene esquema
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            markdown = await fetch_and_extract(url)
            return BulkConvertResult(url=url, markdown=markdown)
        except Exception as e:
            return BulkConvertResult(url=url, markdown=None, error=str(e))

    results = await asyncio.gather(*[process(url) for url in request.urls])
    return {"results": [r.model_dump() for r in results]}


@app.get("/r/{full_url:path}", response_class=PlainTextResponse)
async def convert_from_path(full_url: str):
    """
    Endpoint estilo prefijo para usar desde el navegador.
    Uso: GET http://localhost:8000/r/https://ejemplo.com
    Devuelve el contenido de la pagina en Markdown plano.
    """
    if not full_url.startswith(("http://", "https://")):
        full_url = "https://" + full_url
    try:
        return await fetch_and_extract(full_url)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Error al obtener la URL: {e}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Error de red: {e}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- MCP Tool ---
@mcp.tool()
async def url_to_markdown(url: str) -> str:
    """
    Convierte una URL a Markdown.
    Descarga la pagina de forma asincrona y extrae el contenido con Trafilatura.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return await fetch_and_extract(url)
