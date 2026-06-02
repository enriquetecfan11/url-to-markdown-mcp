# url-to-markdown-mcp

> FastAPI service that converts any URL to Markdown + MCP server via SSE for AI integrations.

## Requirements

> **Python >= 3.10 is required.** The `mcp` SDK does not support Python 3.9 or below.

## What is this?

A lightweight Python service with two interfaces:

1. **REST API** — Endpoint `POST /convert` que recibe una URL y devuelve el contenido de la página en formato Markdown limpio.
2. **MCP Server via SSE** — Servidor compatible con el [Model Context Protocol](https://modelcontextprotocol.io/) que expone la misma funcionalidad como tool, para que cualquier IA (Claude, Cursor, etc.) pueda usarla directamente.

## Stack

- **FastAPI** — API REST rápida con documentación automática
- **trafilatura** — Extracción inteligente del contenido principal (ignora menús, footers, publicidad)
- **mcp** — SDK oficial de Model Context Protocol
- **Starlette SSE** — Transporte SSE para el servidor MCP
- **uvicorn** — Servidor ASGI de producción

## Project structure

```
url-to-markdown-mcp/
├── app/
│   ├── __init__.py      # Package marker
│   ├── main.py          # FastAPI app + MCP tool definition
│   └── sse.py           # SSE transport for MCP
├── requirements.txt
├── Dockerfile
├── .gitignore
└── README.md
```

## Installation

### 0. Check your Python version

```bash
python3 --version
# Must be 3.10 or higher. If not, install it:
```

**macOS (with pyenv):**

```bash
brew install pyenv
pyenv install 3.11
pyenv local 3.11   # sets 3.11 for this project folder
```

**Or with Homebrew directly:**

```bash
brew install python@3.11
# Then use: /opt/homebrew/bin/python3.11
```

### 1. Clone and set up

```bash
git clone https://github.com/enriquetecfan11/url-to-markdown-mcp.git
cd url-to-markdown-mcp

# Create virtualenv with Python 3.10+
python3.11 -m venv .venv          # adjust version as needed
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker (no Python version worries)

```bash
# Build
docker build -t url-to-markdown-mcp .

# Run
docker run -p 8000:8000 url-to-markdown-mcp
```

## REST API Usage

### Health check

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### Convert URL to Markdown

```bash
curl -X POST http://localhost:8000/convert \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

Response:

```json
{
  "url": "https://example.com",
  "markdown": "# Example Domain\n\nThis domain is for use in illustrative examples..."
}
```

### Interactive docs

Once the server is running, visit:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## MCP Server Usage (SSE)

The service exposes an MCP-compatible server that AI assistants can connect to.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/sse/` | SSE connection — clients connect here |
| `POST` | `/messages/` | MCP message handler |

### Connecting from Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "url-to-markdown": {
      "url": "http://localhost:8000/sse/"
    }
  }
}
```

### Connecting from Cursor / other MCP clients

Use the SSE endpoint:
```
http://localhost:8000/sse/
```

### Available MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `url_to_markdown` | Converts a URL to Markdown | `url: str` — The URL to convert |

## Error codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `400` | Invalid request body |
| `422` | Content could not be extracted |
| `502` | Failed to fetch the URL (upstream error) |
| `500` | Internal server error |

## License

MIT
