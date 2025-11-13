# /// script # noqa: CPY001
# dependencies = [
#   "semantic-kernel[mcp]",
# ]
# ///
# Copyright (c) Microsoft. All rights reserved.
import argparse
import logging
from typing import Annotated, Any, Literal
import os
import anyio
from azure.identity.aio import DefaultAzureCredential

from semantic_kernel.agents import AzureAIAgent, AzureAIAgentSettings
from semantic_kernel.functions import kernel_function

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Run the Semantic Kernel MCP server.")
    parser.add_argument(
        "--transport",
        type=str,
        choices=["sse", "stdio"],
        default="stdio",
        help="Transport method to use (default: stdio).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to use for SSE transport (required if transport is 'sse').",
    )
    return parser.parse_args()


async def run(transport: Literal["sse", "stdio"] = "stdio", port: int | None = None) -> None:
    async with (
        # 1. Login to Azure and create a Azure AI Project Client
        DefaultAzureCredential() as creds,
        AzureAIAgent.create_client(credential=creds) as client,
    ):

        agent_id = os.environ["AZURE_AI_AGENT_ID"]

        agent_definition = await client.agents.get_agent(
            agent_id=agent_id
        )

        agent = AzureAIAgent(
            client=client,
            definition=agent_definition,
        )

    # async with (
    #     DefaultAzureCredential() as creds,
    #     AzureAIAgent.create_client(credential=creds) as client,
    # ):

    #     agent_definition = await client.agents.get_agent(
    #         agent_id=""
    #     )

    #     # 2. Create a Semantic Kernel agent for the Azure AI agent
    #     agent = AzureAIAgent(
    #         client=client,
    #         definition=agent_definition,
    #     )
        
        server = agent.as_mcp_server()

        if transport == "sse" and port is not None:
            import nest_asyncio
            import uvicorn
            from mcp.server.sse import SseServerTransport
            from starlette.applications import Starlette
            from starlette.routing import Mount, Route

            sse = SseServerTransport("/messages/")

            async def handle_sse(request):
                async with sse.connect_sse(request.scope, request.receive, request._send) as (
                    read_stream,
                    write_stream,
                ):
                    await server.run(read_stream, write_stream, server.create_initialization_options())

            starlette_app = Starlette(
                debug=True,
                routes=[
                    Route("/sse", endpoint=handle_sse),
                    Mount("/messages/", app=sse.handle_post_message),
                ],
            )
            nest_asyncio.apply()
            uvicorn.run(starlette_app, host="0.0.0.0", port=port)  # nosec
        elif transport == "stdio":
            from mcp.server.stdio import stdio_server

            async def handle_stdin(stdin: Any | None = None, stdout: Any | None = None) -> None:
                async with stdio_server() as (read_stream, write_stream):
                    await server.run(read_stream, write_stream, server.create_initialization_options())

            await handle_stdin()


if __name__ == "__main__":
    args = parse_arguments()
    anyio.run(run, args.transport, args.port)