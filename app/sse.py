from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Mount, Route


def create_sse_server(mcp):
    """
    Creates a Starlette sub-application that exposes the MCP server via SSE.

    Routes:
        GET  /sse/      - SSE connection endpoint (clients connect here)
        POST /messages/ - MCP message handler
    """
    transport = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp._mcp_server.run(
                streams[0],
                streams[1],
                mcp._mcp_server.create_initialization_options(),
            )

    routes = [
        Route("/sse/", endpoint=handle_sse),
        Mount("/messages/", app=transport.handle_post_message),
    ]

    return Starlette(routes=routes)
