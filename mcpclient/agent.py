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
    
async def call_tool_with_timeout(client, tool_name, arguments, timeout=5.0):
    try:
        # Wrap the call with a timeout
        result = await asyncio.wait_for(
            client.call_tool(tool_name, arguments=arguments),
            timeout=timeout
        )
        print(f"DEBUG: Tool call result: {result}")
        return result
    except asyncio.TimeoutError:
        print(f"⌛️ Tool call to '{tool_name}' timed out after {timeout} seconds.")
        raise Exception(f"Tool call to '{tool_name}' timed out.")

async def main():
    """
    An example AI agent that connects to and interacts with an MCP server.
    """
    token = get_sa_token()
    if not token:
        print(f"Could not obtain a service account token. Exiting.")
    print(f"Successfully read the service account token (first 8 chars): {token[:8]}...  v16\n")

    # With custom headers for authentication
    transport_calculator = StreamableHttpTransport(
        url=server_url_calculator,
        headers={
            "x-k8s-sa-token": token,
        }
    )
    client_calculator = Client(transport_calculator)
    print(f"🤖 Agent starting up and connecting to {server_url_calculator}...\n")

    try:
        async with client_calculator:
            print(f"✅ Connection successful!\n")

            # # 2. Discover available resources
            # print("\n🔍 Discovering resources...")
            # resources = await client.list_resources()
            # for res in resources:
            #     print(f"  - Found resource: '{res.name}' ({res.uri})")

            # # 3. Read the content of the first resource found
            # if resources:
            #     resource_uri = resources[0].uri
            #     print(f"\n📖 Reading content from '{resource_uri}'...")
            #     content = await client.read_resource(resource_uri)
            #     print(f"  - Content: '{content}'")

            # 4. Discover available tools
            print(f"🛠️ Discovering tools...")
            tools = await client_calculator.list_tools()
            for tool in tools:
                print(f"  - Found tool: '{tool.name}' - {tool.description}")

            # 5. Call a specific tool with parameters
            if tools:
                # --- Call add ---
                try:
                    tool_name = "add"
                    print(f"\n▶️ Calling tool '{tool_name}' with parameters 'a=9, b=3'...")
                    result = await call_tool_with_timeout(client_calculator, tool_name, arguments={"a": 9, "b": 3})
                    print(f"  - Result from tool: '{result}'")
                except Exception as e:
                    print(f"    - ❌ Error calling tool '{tool_name}': {e}")

                # --- Call subtract ---
                try:
                    tool_name = "subtract"
                    print(f"\n▶️ Calling tool '{tool_name}' with parameters 'a=8, b=3'...")
                    result = await call_tool_with_timeout(client_calculator, tool_name, arguments={"a": 8, "b": 3})
                    print(f"  - Result from tool: '{result}'")
                except Exception as e:
                    print(f"    - ❌ Error calling tool '{tool_name}': {e}")

    except Exception as e:
        print(f"❌ An error occurred during the calculator client session: {e}")
    finally:
        print(f"\n🔌 Connection closed. Agent shutting down.\n\n")

    transport_deepwiki = StreamableHttpTransport(
        url=server_url_deepwiki,
        headers={
            "x-k8s-sa-token": token,
        }
    )
    client_deepwiki = Client(transport_deepwiki)
    print(f"🤖 Agent starting up and connecting to {server_url_deepwiki}...\n")

    try:
        async with client_deepwiki:
            print(f"✅ Connection successful!")

            # Discover available tools
            print(f"\n🛠️ Discovering tools...")
            tools = await client_deepwiki.list_tools()
            for tool in tools:
                print(f"  - Found tool: '{tool.name}' - {tool.description}")

            # Call a specific tool with parameters
            if tools:
                repo = "kubernetes/kubernetes"
                
                # --- Call read_wiki_structure ---
                try:
                    tool_name = "read_wiki_structure"
                    print(f"\n▶️ Calling tool '{tool_name}' with parameter repoName='{repo}'...")
                    result = await call_tool_with_timeout(client_deepwiki, tool_name, arguments={"repoName": repo})
                    print(f"  - Result from tool: '{result}'")
                except Exception as e:
                    print(f"    - ❌ Error calling tool '{tool_name}': {e}")

                # --- Call read_wiki_contents ---
                try:
                    tool_name = "read_wiki_contents"
                    print(f"\n▶️ Calling tool '{tool_name}' with parameter repoName='{repo}'...")
                    result = await call_tool_with_timeout(client_deepwiki, tool_name, arguments={"repoName": repo})
                    print(f"  - Result from tool: '{result}'")
                except Exception as e:
                    print(f"    - ❌ Error calling tool '{tool_name}': {e}")

                # --- Call ask_question ---
                try:
                    tool_name = "ask_question"
                    question = "how to contribute?"
                    print(f"\n▶️ Calling tool '{tool_name}' with parameter repoName='{repo}' question='{question}'...")
                    result = await call_tool_with_timeout(client_deepwiki, tool_name, arguments={"repoName": repo, "question": question})
                    print(f"  - Result from tool: '{result}'")
                except Exception as e:
                    print(f"    - ❌ Error calling tool '{tool_name}': {e}")

    except Exception as e:
        print(f"❌ An error occurred during the deepwiki client session: {e}")
    finally:
        print(f"\n🔌 Connection closed. Agent shutting down.")

if __name__ == "__main__":
    asyncio.run(main())
