# agent.py
import asyncio
from fastmcp.client import Client

async def main():
    """
    An example AI agent that connects to and interacts with an MCP server.
    """
    server_url = "http://localhost:9000/mcp"
    print(f"🤖 Agent starting up and connecting to {server_url}...")
    
    # Initialize the client, pointing to our server's address
    client = Client(server_url)

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
