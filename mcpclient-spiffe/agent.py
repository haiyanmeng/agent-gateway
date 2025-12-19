# agent.py
import asyncio
import os
import aiohttp
import ssl
import httpx
from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport

server_url = os.environ.get("MCP_SERVER_URL", "https://envoy-service.envoy-gateway-system.svc.cluster.local:10001")

server_url_calculator = server_url + "/mcp-server1/mcp"

server_url_deepwiki = server_url + "/mcp-server2/mcp"

def create_tls_client(expected_spiffe_id=None, **kwargs):
    """
    Factory to create an httpx client with custom TLS/SSL settings for SPIFFE.
    """
    # Create a custom SSL context for client-side authentication
    ssl_context = ssl.create_default_context(
        purpose=ssl.Purpose.SERVER_AUTH,  # Explicitly state we're verifying the server
        cafile="/etc/ssl/certs/trust-bundle.pem"
    )
    # Load the client's certificate and private key provided by the SPIFFE CSI driver
    ssl_context.load_cert_chain(
        certfile="/var/run/secrets/spiffe.io/tls.crt",
        keyfile="/var/run/secrets/spiffe.io/tls.key"
    )
    
    # Disable default hostname checking because we will manually verify the SPIFFE ID
    ssl_context.check_hostname = False

    def custom_verifier(conn):
        """
        A callback to verify the server's SPIFFE ID from its certificate.
        This is called after the TLS handshake.
        """
        if not expected_spiffe_id:
            # If no SPIFFE ID is expected, we can't perform this check.
            # This branch should ideally not be taken in a secure setup.
            return

        peercert = conn.getpeercert()
        sans = peercert.get('subjectAltName', [])
        
        # Search for the expected SPIFFE ID in the URI SANs
        for san_type, san_value in sans:
            if san_type == 'URI' and san_value == expected_spiffe_id:
                # The server's SPIFFE ID matches the one we expect
                return
        
        # If the loop completes without finding a match, the verification fails
        raise ssl.SSLCertVerificationError(
            f"Expected SPIFFE ID '{expected_spiffe_id}' not found in server certificate SANs."
        )

    # Attach the custom verifier to the SSLContext's post-handshake verification
    if expected_spiffe_id:
        ssl_context.custom_verifier = custom_verifier

    # Return an AsyncClient configured with our custom SSL context
    return httpx.AsyncClient(verify=ssl_context, **kwargs)
   
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

async def interact_with_service(service_name, server_url, tool_calls):
    """
    Connects to a service, discovers tools, and executes a list of tool calls.
    """
    transport = StreamableHttpTransport(
        url=server_url,
        httpx_client_factory=create_tls_client,
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
    calculator_tool_calls = [
        {"name": "add", "args": {"a": 9, "b": 3}, "display_params": "'a=9, b=3'"},
        {"name": "subtract", "args": {"a": 8, "b": 3}, "display_params": "'a=8, b=3'"},
    ]
    await interact_with_service("Calculator", server_url_calculator, calculator_tool_calls)

    repo = "kubernetes/kubernetes"
    question = "how to contribute?"
    deepwiki_tool_calls = [
        {"name": "read_wiki_structure", "args": {"repoName": repo}, "display_params": f"repoName='{repo}'"},
        {"name": "read_wiki_contents", "args": {"repoName": repo}, "display_params": f"repoName='{repo}'"},
        {"name": "ask_question", "args": {"repoName": repo, "question": question}, "display_params": f"repoName='{repo}' question='{question}'"},
    ]
    await interact_with_service("DeepWiki", server_url_deepwiki, deepwiki_tool_calls)


if __name__ == "__main__":
    asyncio.run(main())
