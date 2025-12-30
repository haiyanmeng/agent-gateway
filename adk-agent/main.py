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

# This file sets up the FastAPI application using get_fast_api_app() from ADK

import logging
import os

# Add these lines to configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from contextlib import asynccontextmanager
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Import the objects from your agent.py
from mcp_agent.agent import my_ssl_context, reload_certificates

# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Example session service URI (e.g., SQLite)
SESSION_SERVICE_URI = "sqlite:///./sessions.db"
# Example allowed origins for CORS
ALLOWED_ORIGINS = ["http://localhost", "http://localhost:8080", "*"]
# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = True

# --- Watchdog Logic ---
class CertRotationHandler(FileSystemEventHandler):
    def on_modified(self, event):
        # Trigger reload if the cert or key files are modified
        if event.src_path in [os.environ.get("CLIENT_CERT_FILE"), os.environ.get("CLIENT_KEY_FILE")]:
            logger.info(f"Change detected in {event.src_path}. Rotating SSL context...")
            reload_certificates(my_ssl_context)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    cert_dir = os.path.dirname(os.environ.get("CLIENT_CERT_FILE", "/var/run/secrets/spiffe.io/"))

    observer = Observer()
    observer.schedule(CertRotationHandler(), path=cert_dir, recursive=False)
    observer.start()
    logger.info(f"mTLS Rotation Watcher started for directory: {cert_dir}")

    yield  # Agent is now serving requests

    # --- SHUTDOWN ---
    observer.stop()
    observer.join()

# Call the function to get the FastAPI app instance
# Ensure the agent directory name ('capital_agent') matches your agent folder
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri=SESSION_SERVICE_URI,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

# Inject the lifespan into the ADK-provided FastAPI app
app.router.lifespan_context = lifespan

# You can add more FastAPI routes or configurations below if needed
# Example:
# @app.get("/hello")
# async def read_root():
#     return {"Hello": "World"}

if __name__ == "__main__":
    logger.info("Starting uvicorn server.")
    # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
