# agent.py
import asyncio
import os
from fastmcp.client import Client

server_url = os.environ.get("MCP_SERVER_URL", "http://server1-svc:9000/mcp")

# The standard path where the service account token is mounted.
TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"

def get_sa_token():
    """Reads the service account token from the default location."""
    try:
        with open(TOKEN_PATH, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Service account token file not found at {TOKEN_PATH}.")
        print("This script is likely not running inside a Kubernetes pod.")
        return None
    except Exception as e:
        print(f"An error occurred while reading the token: {e}")
        return None

async def main():
    """
    An example AI agent that connects to and interacts with an MCP server.
    """
    print(f"🤖 Agent starting up and connecting to {server_url}...")

    token = get_sa_token()
    if not token:
        print("Could not obtain a service account token. Exiting.")
        return

    # For security, only print a portion of the token in logs.
    print(f"Successfully read the service account token (first 8 chars): {token[:8]}...")

    # 1. Define custom headers to pass the service account token.
    # The key "x-user-role" is what the Envoy RBAC filter is configured to check.
    my_headers = {
        "x-user-role": token
    }

    # Initialize the client, pointing to our server's address
    client = Client(server_url)
    # Set the custom headers on the client instance
    client.headers = my_headers

    try:
        async with client:
            print("✅ Connection successful!")

            # 2. Discover available resources
            print("\n🔍 Discovering resources...")
            resources = await client.list_resources()
            for res in resources:
                print(f"  - Found resource: '{res.name}' ({res.uri})")

            # 3. Read the content of the first resource found
            if resources:
                resource_uri = resources[0].uri
                print(f"\n📖 Reading content from '{resource_uri}'...")
                content = await client.read_resource(resource_uri)
                print(f"  - Content: '{content}'")

            # 4. Discover available tools
            print("\n🛠️ Discovering tools...")
            tools = await client.list_tools()
            for tool in tools:
                print(f"  - Found tool: '{tool.name}' - {tool.description}")

            # 5. Call a specific tool with parameters
            if tools:
                            tool_name = "add"
                            print(f"\n▶️ Calling tool '{tool_name}' with parameters 'a=5, b=3'...")
                            result = await client.call_tool(tool_name, arguments={"a": 5, "b": 3})
            print(f"  - Result from tool: '{result}'")

    except Exception as e:
        print(f"❌ An error occurred: {e}")
    finally:
        print("\n🔌 Connection closed. Agent shutting down.")

if __name__ == "__main__":
    asyncio.run(main())
