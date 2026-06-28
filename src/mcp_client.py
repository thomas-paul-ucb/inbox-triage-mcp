"""
Connects to Google's official Gmail MCP server and pulls recent emails.

Uses the access token from auth.py (already obtained via OAuth) to
authenticate, then calls the server's search_threads and get_thread
tools to retrieve recent email content.
"""

import os
import asyncio

import httpx
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from src.auth import get_access_token

load_dotenv()

MCP_SERVER_URL = os.getenv("GMAIL_MCP_SERVER_URL", "https://gmailmcp.googleapis.com/mcp/v1")


class _BearerAuth(httpx.Auth):
    """Attaches our OAuth access token to every request to the MCP server."""

    def __init__(self, token: str):
        self.token = token

    def auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self.token}"
        yield request


async def list_available_tools():
    """Connects to the Gmail MCP server and prints what tools it exposes.

    Mainly useful as a first connectivity check before we start
    calling real tools like search_threads / get_thread.
    """
    token = get_access_token()
    auth = _BearerAuth(token)

    async with streamablehttp_client(MCP_SERVER_URL, auth=auth) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            return tools


if __name__ == "__main__":
    result = asyncio.run(list_available_tools())
    print(result)