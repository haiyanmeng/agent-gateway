# agent.py
import asyncio
import os
import aiohttp
from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport

server_url = os.environ.get("MCP_SERVER_URL", "http://envoy-service:10001")

server_url_calculator = server_url + "/mcp-server1/mcp"

server_url_deepwiki = server_url + "/mcp-server2/mcp"

# The standard path where the service account token is mounted.
TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"

def get_sa_token():
    """Reads the service account token from the default location."""
    try:
        with open(TOKEN_PATH, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Service account token file not found at {TOKEN_PATH}.")
        print(f"This script is likely not running inside a Kubernetes pod.")
        return None
    except Exception as e:
        print(f"An error occurred while reading the token: {e}")
        return None
    
async def call_tool_safely(transport, tool_name, arguments, timeout=5.0):
    """
    Creates a short-lived client to make a single, isolated tool call
    with a timeout. This prevents a timeout from corrupting the client state.
    """
    try:
        async with Client(transport) as client:
            result = await asyncio.wait_for(
                client.call_tool(tool_name, arguments=arguments),
                timeout=timeout
            )
            print(f"DEBUG: Tool call result: {result}")
            return result
    except asyncio.TimeoutError:
        print(f"⌛️ Tool call to '{tool_name}' timed out after {timeout} seconds.")
        # We raise an exception here to be caught by the per-call try/except blocks
        raise Exception(f"Tool call to '{tool_name}' timed out.")
    except Exception as e:
        # Re-raise any other exceptions (like 403s) to be caught by the caller
        raise e

async def interact_with_service(service_name, server_url, token, tool_calls):
    """
    Connects to a service, discovers tools, and executes a list of tool calls.
    """
    transport = StreamableHttpTransport(
        url=server_url,
        headers={"x-k8s-sa-token": token},
    )
    print(f"🤖 Agent starting up and connecting to {service_name} at {server_url}...\n")

    try:
        # Discover available tools using a temporary client
        async with Client(transport) as temp_client:
            print(f"✅ Connection successful!")
            print(f"🛠️ Discovering tools...")
            tools = await temp_client.list_tools()
            for tool in tools:
                print(f"  - Found tool: '{tool.name}' - {tool.description}")

        # Call a specific tool with parameters
        if tools:
            for tool_call in tool_calls:
                try:
                    tool_name = tool_call["name"]
                    arguments = tool_call["args"]
                    display_params = tool_call["display_params"]
                    print(f"\n▶️ Calling tool '{tool_name}' with parameters {display_params}...")
                    result = await call_tool_safely(transport, tool_name, arguments=arguments)
                    print(f"  - Result from tool: '{result}'")
                except Exception as e:
                    print(f"    - ❌ Error calling tool '{tool_name}': {e}")

    except Exception as e:
        print(f"❌ An error occurred during the {service_name} client session: {e}")
    finally:
        print(f"\n🔌 Connection closed for {service_name}.")


async def main():
    """
    An example AI agent that connects to and interacts with an MCP server.
    """
    token = get_sa_token()
    if not token:
        print(f"Could not obtain a service account token. Exiting.")
        return
    print(f"Successfully read the service account token (first 8 chars): {token[:8]}...  v21\n")

    calculator_tool_calls = [
        {"name": "add", "args": {"a": 9, "b": 3}, "display_params": "'a=9, b=3'"},
        {"name": "subtract", "args": {"a": 8, "b": 3}, "display_params": "'a=8, b=3'"},
    ]
    await interact_with_service("Calculator", server_url_calculator, token, calculator_tool_calls)

    repo = "kubernetes/kubernetes"
    question = "how to contribute?"
    deepwiki_tool_calls = [
        {"name": "read_wiki_structure", "args": {"repoName": repo}, "display_params": f"repoName='{repo}'"},
        {"name": "read_wiki_contents", "args": {"repoName": repo}, "display_params": f"repoName='{repo}'"},
        {"name": "ask_question", "args": {"repoName": repo, "question": question}, "display_params": f"repoName='{repo}' question='{question}'"},
    ]
    await interact_with_service("DeepWiki", server_url_deepwiki, token, deepwiki_tool_calls)


if __name__ == "__main__":
    asyncio.run(main())
