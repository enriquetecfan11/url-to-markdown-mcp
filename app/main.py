from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import requests
import trafilatura
from mcp.server.fastmcp import FastMCP
from app.sse import create_sse_server

# --- App & MCP setup ---
app = FastAPI(
    title="URL to Markdown API",
    description="Converts any URL to Markdown. Also exposes an MCP SSE server for AI integrations.",
    version="1.0.0",
)
mcp = FastMCP("url-to-markdown")

# Mount SSE server at /sse
app.mount("/", create_sse_server(mcp))


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
    Convert a URL to Markdown.

    - **url**: The URL to convert (must be a valid HTTP/HTTPS URL)
    - Returns: The extracted Markdown content
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


# --- MCP Tool ---
@mcp.tool()
def url_to_markdown(url: str) -> str:
    """
    Convert a URL to Markdown.
    Fetches the page at the given URL and returns its main content as Markdown.
    """
    return extract_markdown(url)
