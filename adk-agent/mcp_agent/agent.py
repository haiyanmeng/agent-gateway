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

import httpcore._backends.anyio


cert_file = os.environ.get("CLIENT_CERT_FILE")
key_file = os.environ.get("CLIENT_KEY_FILE")
ca_bundle_file = os.environ.get("SSL_CERT_FILE")


# # This globally overrides the match_hostname function to always return True
# # This is safe here because you are already verifying the CA bundle 
# # and using mTLS (Mutual trust).
# def match_hostname_patch(cert, hostname):
#     return

# ssl.match_hostname = match_hostname_patch

# Use SSLContext directly to avoid the "Default" presets that force hostname matching
my_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

# CRITICAL: Disable hostname check at the context level
my_ssl_context.check_hostname = False
my_ssl_context.verify_mode = ssl.CERT_REQUIRED

# Add these lines to configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

def reload_certificates(ctx):
    """Reloads the certificate chain and CA bundle into the provided context."""
    try:
        if all(os.path.exists(p) for p in [cert_file, key_file, ca_bundle_file]):
            # reload_cert_chain clears the old one and loads the new one
            ctx.load_cert_chain(certfile=cert_file, keyfile=key_file)
            # load_verify_locations appends/updates the CA bundle
            ctx.load_verify_locations(cafile=ca_bundle_file)
            logger.info("SSL Context successfully reloaded with new certificates.")
        else:
            logger.warning("Certificate files missing; skipping reload.")
    except Exception as e:
        logger.error(f"Failed to reload certificates: {e}")

# Initial Load
reload_certificates(my_ssl_context)

for path in ["/var/run/secrets/spiffe.io/tls.crt", "/var/run/secrets/spiffe.io/tls.key", "/etc/ssl/certs/trust-bundle.pem"]:
    if os.path.exists(path):
        size = os.path.getsize(path)
        logger.info(f"FILE CHECK: {path} exists, size: {size} bytes")
    else:
        logger.error(f"FILE CHECK: {path} MISSING!")

# Verify the context has the cert and the trust bundle
logger.debug(f"SSL Context loaded certs: {len(my_ssl_context.get_ca_certs())}")
logger.debug(f"SSL Context verify mode: {my_ssl_context.verify_mode}")

# Force the underlying library to ignore the hostname during the TLS handshake
original_start_tls = httpcore._backends.anyio.AnyIOStream.start_tls

async def patched_start_tls(self, ssl_context, server_hostname=None, timeout=None):
    # Log the hostname captured from the high-level request (e.g., Gemini or Envoy)
    logger.debug(f"DEBUG: patched_start_tls called for hostname: {server_hostname}")
    
    # Apply targeted logic
    if server_hostname and "envoy-service" in server_hostname:
        logger.debug("DEBUG: Custom Envoy context applied. Bypassing hostname check.")
        return await original_start_tls(self, my_ssl_context, server_hostname=None, timeout=timeout)
    
    # For Google Gemini or other public APIs, use the original context.
    # For example, generativelanguage.googleapis.com
    logger.debug(f"DEBUG: Using standard system context for {server_hostname}")
    return await original_start_tls(self, ssl_context, server_hostname=server_hostname, timeout=timeout)

httpcore._backends.anyio.AnyIOStream.start_tls = patched_start_tls

envoy_service = os.environ.get("ENVOY_SERVICE")

try:
    local_mcp = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=f"https://{envoy_service}/mcp-server1/mcp",
            # ssl_context=my_ssl_context,
            # server_hostname="spiffe://my.trust.domain/ns/envoy-gateway-system/sa/envoy-sa",
            # server_hostname=None, # Explicitly tell it there is no name to match
        ),
    )
    logger.info("McpToolset local_mcp initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing McpToolset local_mcp: {e}")

try:
    remote_mcp = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=f"https://{envoy_service}/mcp-server2/mcp",
            # ssl_context=my_ssl_context,
            # server_hostname="spiffe://my.trust.domain/ns/envoy-gateway-system/sa/envoy-sa",
            # server_hostname=None, # Explicitly tell it there is no name to match
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
