from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, HttpUrl
import requests
import trafilatura
from mcp.server.fastmcp import FastMCP

# --- MCP setup ---
mcp = FastMCP("url-to-markdown")

# --- FastAPI app ---
app = FastAPI(
    title="URL to Markdown API",
    description="Converts any URL to Markdown. Also exposes an MCP server for AI integrations.",
    version="1.0.0",
)

# Mount MCP with Streamable HTTP transport (compatible with Cursor, Claude, etc.)
mcp_app = mcp.streamable_http_app()
app.mount("/mcp", mcp_app)


# --- Schemas ---
class ConvertRequest(BaseModel):
    url: HttpUrl


class ConvertResponse(BaseModel):
    url: str
    markdown: str


# --- Core logic ---
def extract_markdown(url: str) -> str:
    """Download a URL and extract its main content as Markdown."""
    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0 (compatible; URLToMarkdown/1.0)"},
    )
    response.raise_for_status()

    markdown = trafilatura.extract(
        response.text,
        include_comments=False,
        include_tables=True,
        include_links=True,
        output_format="markdown",
        deduplicate=True,
    )

    if not markdown:
        raise ValueError("Could not extract content from the provided URL.")

    return markdown


# --- REST endpoints ---
@app.get("/health", tags=["Utility"])
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/convert", response_model=ConvertResponse, tags=["Converter"])
def convert(req: ConvertRequest):
    """
    Convert a URL to Markdown (JSON API).
    - **url**: The URL to convert
    - Returns: JSON with url + markdown
    """
    try:
        md = extract_markdown(str(req.url))
        return ConvertResponse(url=str(req.url), markdown=md)
    except requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {e}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/{full_url:path}", response_class=PlainTextResponse, tags=["Jina-style"])
def convert_from_path(full_url: str):
    """
    Jina Reader-style endpoint.
    Usage: GET http://localhost:8000/https://example.com
    Returns the page content as plain Markdown text.
    """
    # Ensure the URL has a scheme
    if not full_url.startswith("http://") and not full_url.startswith("https://"):
        full_url = "https://" + full_url
    try:
        return extract_markdown(full_url)
    except requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {e}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- MCP Tool ---
@mcp.tool()
def url_to_markdown(url: str) -> str:
    """
    Convert a URL to Markdown.
    Fetches the page at the given URL and returns its main content as Markdown.
    """
    return extract_markdown(url)
