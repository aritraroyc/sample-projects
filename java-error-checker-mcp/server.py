#!/usr/bin/env python3
"""
Java Error Checker MCP Server

A Model Context Protocol (MCP) server that provides Java compilation error checking
using the Eclipse JDT Language Server (JDTLS).

This server allows MCP clients to:
- Create isolated Java project sessions
- Submit Java code for compilation checking
- Get detailed error reports and recommendations
- Manage multiple concurrent sessions
"""

import asyncio
import logging
import sys
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from session_manager import SessionManager
from jdtls_client import JDTLSClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/java-error-checker-mcp.log'),
        logging.StreamHandler(sys.stderr)
    ]
)

logger = logging.getLogger(__name__)


class JavaErrorCheckerServer:
    """MCP Server for Java error checking."""

    def __init__(self):
        """Initialize the server."""
        self.server = Server("java-error-checker")
        self.session_manager = SessionManager()
        self.jdtls_client = JDTLSClient()

        # Register handlers
        self._register_handlers()

        logger.info("Java Error Checker MCP Server initialized")

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
                            "session_id": {
                                "type": "string",
                                "description": "Session ID from create_session"
                            },
                            "file_path": {
                                "type": "string",
                                "description": "Relative path to Java file (e.g., 'com/example/Main.java')"
                            },
                            "content": {
                                "type": "string",
                                "description": "Java source code content"
                            }
                        },
                        "required": ["session_id", "file_path", "content"]
                    }
                ),
                Tool(
                    name="check_errors",
                    description="Check for compilation errors in the Java project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            }
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
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            }
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
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            },
                            "file_path": {
                                "type": "string",
                                "description": "Relative path to Java file"
                            }
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
                            "session_id": {
                                "type": "string",
                                "description": "Session ID to delete"
                            }
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
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            },
                            "error": {
                                "type": "object",
                                "description": "Error object from check_errors",
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
                    name="write_multiple_files",
                    description="Write multiple Java source files to the session workspace in a batch operation. Ideal for agentic workflows that generate multiple classes at once.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID from create_session"
                            },
                            "files": {
                                "type": "array",
                                "description": "Array of file objects to write",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "file_path": {
                                            "type": "string",
                                            "description": "Relative path to Java file (e.g., 'com/example/Main.java')"
                                        },
                                        "content": {
                                            "type": "string",
                                            "description": "Java source code content"
                                        }
                                    },
                                    "required": ["file_path", "content"]
                                }
                            }
                        },
                        "required": ["session_id", "files"]
                    }
                ),
                Tool(
                    name="refresh_session",
                    description="Refresh a session to extend its timeout. Use this in long-running agentic workflows to prevent session cleanup.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID to refresh"
                            }
                        },
                        "required": ["session_id"]
                    }
                ),
                Tool(
                    name="get_session_info",
                    description="Get detailed information about a session including age, file count, and workspace details",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            }
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
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                logger.error(f"Error handling tool {name}: {e}", exc_info=True)
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_create_session(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle create_session tool call."""
        project_name = arguments.get("project_name", "default")
        session_id = self.session_manager.create_session(project_name)

        response = {
            "session_id": session_id,
            "project_name": project_name,
            "status": "created",
            "message": f"Session created successfully. Use this session_id for subsequent operations."
        }

        return [TextContent(type="text", text=str(response))]

    async def _handle_write_java_file(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle write_java_file tool call."""
        session_id = arguments["session_id"]
        file_path = arguments["file_path"]
        content = arguments["content"]

        success = self.session_manager.write_file(session_id, file_path, content)

        if success:
            response = {
                "status": "success",
                "file_path": file_path,
                "message": f"File {file_path} written successfully"
            }
        else:
            response = {
                "status": "error",
                "message": f"Failed to write file {file_path}. Session may not exist."
            }

        return [TextContent(type="text", text=str(response))]

    async def _handle_check_errors(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle check_errors tool call."""
        session_id = arguments["session_id"]

        workspace_path = self.session_manager.get_workspace_path(session_id)
        if not workspace_path:
            return [TextContent(type="text", text=str({
                "status": "error",
                "message": f"Session {session_id} not found"
            }))]

        # Check for compilation errors
        errors = await self.jdtls_client.check_compilation_errors(workspace_path)

        response = {
            "status": "success",
            "session_id": session_id,
            "error_count": len(errors),
            "errors": errors
        }

        if not errors:
            response["message"] = "No compilation errors found!"
        else:
            response["message"] = f"Found {len(errors)} compilation error(s)"

        return [TextContent(type="text", text=str(response))]

    async def _handle_list_files(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle list_files tool call."""
        session_id = arguments["session_id"]

        files = self.session_manager.list_files(session_id)

        response = {
            "status": "success",
            "session_id": session_id,
            "file_count": len(files),
            "files": files
        }

        return [TextContent(type="text", text=str(response))]

    async def _handle_read_file(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle read_file tool call."""
        session_id = arguments["session_id"]
        file_path = arguments["file_path"]

        content = self.session_manager.read_file(session_id, file_path)

        if content is not None:
            response = {
                "status": "success",
                "file_path": file_path,
                "content": content
            }
        else:
            response = {
                "status": "error",
                "message": f"File {file_path} not found"
            }

        return [TextContent(type="text", text=str(response))]

    async def _handle_delete_session(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle delete_session tool call."""
        session_id = arguments["session_id"]

        success = self.session_manager.delete_session(session_id)

        if success:
            response = {
                "status": "success",
                "message": f"Session {session_id} deleted successfully"
            }
        else:
            response = {
                "status": "error",
                "message": f"Session {session_id} not found"
            }

        return [TextContent(type="text", text=str(response))]

    async def _handle_get_recommendations(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle get_recommendations tool call."""
        session_id = arguments["session_id"]
        error = arguments["error"]

        # Generate recommendations based on error message
        recommendations = self._generate_recommendations(error)

        response = {
            "status": "success",
            "session_id": session_id,
            "error": error,
            "recommendations": recommendations
        }

        return [TextContent(type="text", text=str(response))]

    async def _handle_write_multiple_files(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle write_multiple_files tool call."""
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

        return [TextContent(type="text", text=str(response))]

    async def _handle_refresh_session(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle refresh_session tool call."""
        session_id = arguments["session_id"]

        success = self.session_manager.refresh_session(session_id)

        if success:
            response = {
                "status": "success",
                "session_id": session_id,
                "message": "Session timeout refreshed successfully"
            }
        else:
            response = {
                "status": "error",
                "message": f"Session {session_id} not found"
            }

        return [TextContent(type="text", text=str(response))]

    async def _handle_get_session_info(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle get_session_info tool call."""
        session_id = arguments["session_id"]

        info = self.session_manager.get_session_info(session_id)

        if info:
            response = {
                "status": "success",
                **info
            }
        else:
            response = {
                "status": "error",
                "message": f"Session {session_id} not found"
            }

        return [TextContent(type="text", text=str(response))]

    def _generate_recommendations(self, error: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations for fixing an error.

        Args:
            error: Error object with message, file, line, etc.

        Returns:
            List of recommendation strings
        """
        message = error.get("message", "").lower()
        recommendations = []

        # Common error patterns and recommendations
        if "cannot find symbol" in message:
            recommendations.append("Check that the class, variable, or method name is spelled correctly")
            recommendations.append("Ensure the required import statement is present")
            recommendations.append("Verify that the variable is declared before use")

        elif "class, interface, or enum expected" in message:
            recommendations.append("Check for missing or extra braces { }")
            recommendations.append("Ensure all methods are inside a class")
            recommendations.append("Verify that all blocks are properly closed")

        elif "';' expected" in message:
            recommendations.append("Add a semicolon at the end of the statement")
            recommendations.append("Check for syntax errors in the line")

        elif "incompatible types" in message or "type mismatch" in message:
            recommendations.append("Check that variable types match the assigned values")
            recommendations.append("Consider type casting if appropriate")
            recommendations.append("Verify method return types match expectations")

        elif "method" in message and "cannot be applied" in message:
            recommendations.append("Check the number and types of method arguments")
            recommendations.append("Verify the method signature matches the call")

        elif "duplicate" in message:
            recommendations.append("Remove or rename the duplicate declaration")
            recommendations.append("Check for conflicting imports")

        elif "package" in message and "does not exist" in message:
            recommendations.append("Verify the package name is correct")
            recommendations.append("Ensure required dependencies are available")

        elif "unreachable statement" in message:
            recommendations.append("Remove code after return, break, or continue statements")
            recommendations.append("Check logic flow in conditionals")

        else:
            # Generic recommendations
            recommendations.append("Review the error message carefully")
            recommendations.append("Check Java syntax and conventions")
            recommendations.append("Consult Java documentation for the relevant API")

        return recommendations

    async def run(self):
        """Run the MCP server."""
        logger.info("Starting Java Error Checker MCP Server...")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point."""
    server = JavaErrorCheckerServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
