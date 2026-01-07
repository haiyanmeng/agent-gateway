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

# Add these lines to configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

envoy_service = os.environ.get("ENVOY_SERVICE")

try:
    local_mcp = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=f"http://{envoy_service}/mcp-server1/mcp",
            # The default timeout is 5s, and is not long enough
            # to create a MCP session when an envoy sidecar is used
            # for mTLS authentication.
            timeout=20,
        ),
    )
    logger.info("McpToolset local_mcp initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing McpToolset local_mcp: {e}")

try:
    remote_mcp = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=f"http://{envoy_service}/mcp-server2/mcp",
            timeout=20,
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
