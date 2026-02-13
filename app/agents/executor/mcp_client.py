# app/core/mcp_client.py
"""
MCP Client for connecting to Google Drive MCP Server
Handles communication with MCP servers via stdio or HTTP
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
import subprocess

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Client for communicating with MCP servers
    Supports stdio communication (recommended for production)
    """
    
    def __init__(self, server_command: str, server_args: List[str]):
        """
        Initialize MCP client
        
        Args:
            server_command: Command to run MCP server (e.g., "npx")
            server_args: Arguments (e.g., ["-y", "@piotr-agier/google-drive-mcp"])
        """
        self.server_command = server_command
        self.server_args = server_args
        self.process: Optional[subprocess.Popen] = None
        logger.info(f"✅ MCP Client initialized: {server_command} {' '.join(server_args)}")
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call an MCP tool
        
        Args:
            tool_name: Name of the tool (e.g., "gdrive_create_file")
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        try:
            logger.info(f"📞 Calling MCP tool: {tool_name}")
            
            # Build JSON-RPC request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            # Start MCP server process
            process = await asyncio.create_subprocess_exec(
                self.server_command,
                *self.server_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send request
            request_json = json.dumps(request) + "\n"
            process.stdin.write(request_json.encode())
            await process.stdin.drain()
            process.stdin.close()
            
            # Read response
            stdout, stderr = await process.communicate()
            
            if stderr:
                logger.warning(f"MCP stderr: {stderr.decode()}")
            
            # Parse response
            response_text = stdout.decode().strip()
            
            # Handle multiple lines (MCP servers may output logs before JSON)
            for line in response_text.split('\n'):
                try:
                    response = json.loads(line)
                    if "result" in response:
                        logger.info(f"✅ MCP tool completed: {tool_name}")
                        return response["result"]
                    elif "error" in response:
                        error = response["error"]
                        logger.error(f"❌ MCP tool error: {error}")
                        raise Exception(f"MCP error: {error}")
                except json.JSONDecodeError:
                    continue
            
            raise Exception("No valid JSON response from MCP server")
        
        except Exception as e:
            logger.error(f"❌ MCP call failed: {e}", exc_info=True)
            raise
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from MCP server
        
        Returns:
            List of tool definitions
        """
        try:
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
            
            process = await asyncio.create_subprocess_exec(
                self.server_command,
                *self.server_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            request_json = json.dumps(request) + "\n"
            process.stdin.write(request_json.encode())
            await process.stdin.drain()
            process.stdin.close()
            
            stdout, stderr = await process.communicate()
            
            response_text = stdout.decode().strip()
            for line in response_text.split('\n'):
                try:
                    response = json.loads(line)
                    if "result" in response:
                        tools = response["result"].get("tools", [])
                        logger.info(f"✅ Found {len(tools)} MCP tools")
                        return tools
                except json.JSONDecodeError:
                    continue
            
            return []
        
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []


# Singleton instance
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """
    Get or create MCP client singleton
    """
    global _mcp_client
    if _mcp_client is None:
        # Initialize with Google Drive MCP server
        _mcp_client = MCPClient(
            server_command="npx",
            server_args=["-y", "@piotr-agier/google-drive-mcp"]
        )
    return _mcp_client
