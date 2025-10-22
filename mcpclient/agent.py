# agent.py
import asyncio
from fastmcp.client import Client

async def main():
    """
    An example AI agent that connects to and interacts with an MCP server.
    """
    server_url = "http://localhost:9000"
    print(f"🤖 Agent starting up and connecting to {server_url}...")
    
    # Initialize the client, pointing to our server's address
    client = Client(server_url)

    try:
        # 1. Connect to the server
        await client.connect()
        print("✅ Connection successful!")

        # 2. Discover available resources
        print("\n🔍 Discovering resources...")
        resources = await client.resources.list()
        for res in resources:
            print(f"  - Found resource: '{res.name}' ({res.uri})")

        # 3. Read the content of the first resource found
        if resources:
            resource_uri = resources[0].uri
            print(f"\n📖 Reading content from '{resource_uri}'...")
            content = await client.resources.read(resource_uri)
            print(f"  - Content: '{content}'")

        # 4. Discover available tools
        print("\n🛠️ Discovering tools...")
        tools = await client.tools.list()
        for tool in tools:
            print(f"  - Found tool: '{tool.name}' - {tool.description}")

        # 5. Call a specific tool with parameters
        if tools:
            tool_name = "greet"
            print(f"\n▶️ Calling tool '{tool_name}' with parameter 'World'...")
            result = await client.tools.call(tool_name, params={"name": "World"})
            print(f"  - Result from tool: '{result}'")

    except Exception as e:
        print(f"❌ An error occurred: {e}")
    finally:
        # 6. Always close the connection
        await client.close()
        print("\n🔌 Connection closed. Agent shutting down.")

if __name__ == "__main__":
    asyncio.run(main())
