"""
mcp_server.py - Stdio entrypoint for Claude Desktop.

Claude Desktop does NOT support remote MCP servers (HTTP/SSE).
It only supports stdio-based MCP servers that it spawns as a subprocess.

Usage in claude_desktop_config.json:
{
  "mcpServers": {
    "url-to-markdown": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/url-to-markdown-mcp/mcp_server.py"]
    }
  }
}
"""
import requests
import trafilatura
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("url-to-markdown")


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


@mcp.tool()
def url_to_markdown(url: str) -> str:
    """
    Convert a URL to Markdown.
    Fetches the page at the given URL and returns its main content as Markdown.
    """
    return extract_markdown(url)


if __name__ == "__main__":
    mcp.run(transport="stdio")
