# Copyright 2025 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
import ssl
import httpx

# This globally overrides the match_hostname function to always return True
# This is safe here because you are already verifying the CA bundle 
# and using mTLS (Mutual trust).
def match_hostname_patch(cert, hostname):
    return

ssl.match_hostname = match_hostname_patch

# Use SSLContext directly to avoid the "Default" presets that force hostname matching
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

# Load the Agent's identity
ssl_context.load_cert_chain(
    certfile="/var/run/secrets/spiffe.io/tls.crt", 
    keyfile="/var/run/secrets/spiffe.io/tls.key"
)

# Load the Trust Bundle
ssl_context.load_verify_locations(cafile="/etc/ssl/certs/trust-bundle.pem")

# CRITICAL: Disable hostname check at the context level
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_REQUIRED

# Add these lines to configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Verify the context has the cert and the trust bundle
logger.debug(f"SSL Context loaded certs: {ssl_context.get_ca_certs()}")
logger.debug(f"SSL Context verify mode: {ssl_context.verify_mode}")

envoy_service = os.environ.get("ENVOY_SERVICE")

# Standalone test inside your script
with httpx.Client(verify=ssl_context, cert=("/var/run/secrets/spiffe.io/tls.crt", "/var/run/secrets/spiffe.io/tls.key")) as client:
    try:
        test_res = client.get(f"https://{envoy_service}/")
        logger.info(f"Standalone HTTPX test successful: {test_res.status_code}")
    except Exception as e:
        logger.error(f"Standalone HTTPX test failed: {e}")

try:
    local_mcp = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=f"https://{envoy_service}/mcp-server1/mcp",
            ssl_context=ssl_context,
            server_hostname="spiffe://my.trust.domain/ns/envoy-gateway-system/sa/envoy-sa",
        ),
    )
    logger.info("McpToolset local_mcp initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing McpToolset local_mcp: {e}")

try:
    remote_mcp = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=f"https://{envoy_service}/mcp-server2/mcp",
            ssl_context=ssl_context,
            server_hostname="spiffe://my.trust.domain/ns/envoy-gateway-system/sa/envoy-sa",
        ),
    )
    logger.info("McpToolset remote_mcp initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing McpToolset remote_mcp: {e}")

root_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="github_assistant_agent",
    # instruction="""You are my GitHub repository assistant.
    # Use the provided tools to help me manage my GitHub repositories.
    # No need to ask permission from the user to use the tools. Just use them as needed.""",
    tools=[local_mcp, remote_mcp],
)
