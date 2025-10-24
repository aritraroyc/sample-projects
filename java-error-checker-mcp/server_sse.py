#!/usr/bin/env python3
"""
Java Error Checker MCP Server with SSE Transport

Provides HTTP/SSE transport for remote access from LangGraph agents and other clients.
"""

import asyncio
import logging
import sys
import json
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.sse import sse_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import Response
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from session_manager import SessionManager
from jdtls_client import JDTLSClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/java-error-checker-mcp-sse.log'),
        logging.StreamHandler(sys.stderr)
    ]
)

logger = logging.getLogger(__name__)


class JavaErrorCheckerServer:
    """MCP Server for Java error checking with SSE transport."""

    def __init__(self):
        """Initialize the server."""
        self.server = Server("java-error-checker")
        self.session_manager = SessionManager()
        self.jdtls_client = JDTLSClient()

        # Register handlers
        self._register_handlers()

        logger.info("Java Error Checker MCP Server (SSE) initialized")

    def _register_handlers(self):
        """Register MCP handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="create_session",
                    description="Create a new Java project session with isolated workspace",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_name": {
                                "type": "string",
                                "description": "Name of the Java project (optional)",
                                "default": "default"
                            }
                        }
                    }
                ),
                Tool(
                    name="write_java_file",
                    description="Write a Java source file to the session workspace",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "file_path": {"type": "string"},
                            "content": {"type": "string"}
                        },
                        "required": ["session_id", "file_path", "content"]
                    }
                ),
                Tool(
                    name="write_multiple_files",
                    description="Write multiple Java source files in batch. Ideal for agentic workflows.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "files": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "file_path": {"type": "string"},
                                        "content": {"type": "string"}
                                    },
                                    "required": ["file_path", "content"]
                                }
                            }
                        },
                        "required": ["session_id", "files"]
                    }
                ),
                Tool(
                    name="check_errors",
                    description="Check for compilation errors in the Java project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"}
                        },
                        "required": ["session_id"]
                    }
                ),
                Tool(
                    name="list_files",
                    description="List all Java files in the session workspace",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"}
                        },
                        "required": ["session_id"]
                    }
                ),
                Tool(
                    name="read_file",
                    description="Read a Java file from the session workspace",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "file_path": {"type": "string"}
                        },
                        "required": ["session_id", "file_path"]
                    }
                ),
                Tool(
                    name="delete_session",
                    description="Delete a session and clean up its workspace",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"}
                        },
                        "required": ["session_id"]
                    }
                ),
                Tool(
                    name="get_recommendations",
                    description="Get recommendations for fixing compilation errors",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "error": {
                                "type": "object",
                                "properties": {
                                    "file": {"type": "string"},
                                    "line": {"type": "number"},
                                    "message": {"type": "string"}
                                }
                            }
                        },
                        "required": ["session_id", "error"]
                    }
                ),
                Tool(
                    name="refresh_session",
                    description="Refresh session to extend timeout for long-running workflows",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"}
                        },
                        "required": ["session_id"]
                    }
                ),
                Tool(
                    name="get_session_info",
                    description="Get detailed session information including file count and age",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"}
                        },
                        "required": ["session_id"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent | ImageContent | EmbeddedResource]:
            """Handle tool calls."""
            try:
                if name == "create_session":
                    return await self._handle_create_session(arguments)
                elif name == "write_java_file":
                    return await self._handle_write_java_file(arguments)
                elif name == "write_multiple_files":
                    return await self._handle_write_multiple_files(arguments)
                elif name == "check_errors":
                    return await self._handle_check_errors(arguments)
                elif name == "list_files":
                    return await self._handle_list_files(arguments)
                elif name == "read_file":
                    return await self._handle_read_file(arguments)
                elif name == "delete_session":
                    return await self._handle_delete_session(arguments)
                elif name == "get_recommendations":
                    return await self._handle_get_recommendations(arguments)
                elif name == "refresh_session":
                    return await self._handle_refresh_session(arguments)
                elif name == "get_session_info":
                    return await self._handle_get_session_info(arguments)
                else:
                    return [TextContent(type="text", text=json.dumps({
                        "status": "error",
                        "message": f"Unknown tool: {name}"
                    }))]
            except Exception as e:
                logger.error(f"Error handling tool {name}: {e}", exc_info=True)
                return [TextContent(type="text", text=json.dumps({
                    "status": "error",
                    "message": str(e)
                }))]

    # Handler methods (same as in server.py)
    async def _handle_create_session(self, arguments: Dict[str, Any]) -> list[TextContent]:
        project_name = arguments.get("project_name", "default")
        session_id = self.session_manager.create_session(project_name)
        response = {
            "session_id": session_id,
            "project_name": project_name,
            "status": "created",
            "message": f"Session created successfully. Use this session_id for subsequent operations."
        }
        return [TextContent(type="text", text=json.dumps(response))]

    async def _handle_write_java_file(self, arguments: Dict[str, Any]) -> list[TextContent]:
        session_id = arguments["session_id"]
        file_path = arguments["file_path"]
        content = arguments["content"]
        success = self.session_manager.write_file(session_id, file_path, content)
        response = {
            "status": "success" if success else "error",
            "file_path": file_path,
            "message": f"File {file_path} written successfully" if success else f"Failed to write file {file_path}"
        }
        return [TextContent(type="text", text=json.dumps(response))]

    async def _handle_write_multiple_files(self, arguments: Dict[str, Any]) -> list[TextContent]:
        session_id = arguments["session_id"]
        files = arguments["files"]
        result = self.session_manager.write_multiple_files(session_id, files)
        if result.get("success"):
            response = {
                "status": "success",
                "session_id": session_id,
                "written": result["written"],
                "failed": result["failed"],
                "total": result["total"],
                "message": f"Batch write complete: {result['written']} files written, {result['failed']} failed"
            }
            if "failed_files" in result:
                response["failed_files"] = result["failed_files"]
        else:
            response = {
                "status": "error",
                "message": result.get("error", "Failed to write files")
            }
        return [TextContent(type="text", text=json.dumps(response))]

    async def _handle_check_errors(self, arguments: Dict[str, Any]) -> list[TextContent]:
        session_id = arguments["session_id"]
        workspace_path = self.session_manager.get_workspace_path(session_id)
        if not workspace_path:
            return [TextContent(type="text", text=json.dumps({
                "status": "error",
                "message": f"Session {session_id} not found"
            }))]
        errors = await self.jdtls_client.check_compilation_errors(workspace_path)
        response = {
            "status": "success",
            "session_id": session_id,
            "error_count": len(errors),
            "errors": errors,
            "message": "No compilation errors found!" if not errors else f"Found {len(errors)} compilation error(s)"
        }
        return [TextContent(type="text", text=json.dumps(response))]

    async def _handle_list_files(self, arguments: Dict[str, Any]) -> list[TextContent]:
        session_id = arguments["session_id"]
        files = self.session_manager.list_files(session_id)
        response = {
            "status": "success",
            "session_id": session_id,
            "file_count": len(files),
            "files": files
        }
        return [TextContent(type="text", text=json.dumps(response))]

    async def _handle_read_file(self, arguments: Dict[str, Any]) -> list[TextContent]:
        session_id = arguments["session_id"]
        file_path = arguments["file_path"]
        content = self.session_manager.read_file(session_id, file_path)
        response = {
            "status": "success" if content is not None else "error",
            "file_path": file_path,
            "content": content,
            "message": None if content is not None else f"File {file_path} not found"
        }
        return [TextContent(type="text", text=json.dumps(response))]

    async def _handle_delete_session(self, arguments: Dict[str, Any]) -> list[TextContent]:
        session_id = arguments["session_id"]
        success = self.session_manager.delete_session(session_id)
        response = {
            "status": "success" if success else "error",
            "message": f"Session {session_id} deleted successfully" if success else f"Session {session_id} not found"
        }
        return [TextContent(type="text", text=json.dumps(response))]

    async def _handle_get_recommendations(self, arguments: Dict[str, Any]) -> list[TextContent]:
        from server import JavaErrorCheckerServer as StdioServer
        temp_server = StdioServer()
        session_id = arguments["session_id"]
        error = arguments["error"]
        recommendations = temp_server._generate_recommendations(error)
        response = {
            "status": "success",
            "session_id": session_id,
            "error": error,
            "recommendations": recommendations
        }
        return [TextContent(type="text", text=json.dumps(response))]

    async def _handle_refresh_session(self, arguments: Dict[str, Any]) -> list[TextContent]:
        session_id = arguments["session_id"]
        success = self.session_manager.refresh_session(session_id)
        response = {
            "status": "success" if success else "error",
            "session_id": session_id,
            "message": "Session timeout refreshed successfully" if success else f"Session {session_id} not found"
        }
        return [TextContent(type="text", text=json.dumps(response))]

    async def _handle_get_session_info(self, arguments: Dict[str, Any]) -> list[TextContent]:
        session_id = arguments["session_id"]
        info = self.session_manager.get_session_info(session_id)
        if info:
            response = {"status": "success", **info}
        else:
            response = {
                "status": "error",
                "message": f"Session {session_id} not found"
            }
        return [TextContent(type="text", text=json.dumps(response))]


# Create the MCP server instance
mcp_server = JavaErrorCheckerServer()


# Create Starlette app with SSE support
async def handle_sse(request):
    """Handle SSE connections."""
    async with sse_server() as streams:
        await mcp_server.server.run(
            streams[0],
            streams[1],
            mcp_server.server.create_initialization_options()
        )


async def handle_health(request):
    """Health check endpoint."""
    return Response(
        content=json.dumps({
            "status": "healthy",
            "service": "java-error-checker-mcp",
            "transport": "sse"
        }),
        media_type="application/json"
    )


# Create Starlette application
app = Starlette(
    debug=True,
    routes=[
        Route("/sse", handle_sse),
        Route("/health", handle_health),
    ]
)

# Add CORS middleware for remote access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Java Error Checker MCP Server (SSE)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    args = parser.parse_args()

    logger.info(f"Starting Java Error Checker MCP Server (SSE) on {args.host}:{args.port}")
    logger.info(f"SSE endpoint: http://{args.host}:{args.port}/sse")
    logger.info(f"Health check: http://{args.host}:{args.port}/health")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
