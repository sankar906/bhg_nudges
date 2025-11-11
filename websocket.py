"""
WebSocket Server for Counselor Agent
Receives transcripts and sends real-time analysis (problems, nudges, sentiment)
"""

import asyncio
import json
import logging
import os
from aiohttp import web
from dotenv import load_dotenv
from counselor_agent import CounselorAgent
import websockets

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class CounselorWebSocketServer:
    """WebSocket server for real-time counselor agent analysis."""

    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model
        self.active_connections = 0
        self.total_connections = 0

    async def handle_client(self, websocket):
        # Each connection gets its own agent and stores previous nudges
        agent = CounselorAgent(api_key=self.api_key, model=self.model)
        previous_nudges = []
        self.active_connections += 1
        self.total_connections += 1
        logger.info("Client connected: %s", websocket.remote_address)
        try:
            await websocket.send(
                json.dumps(
                    {
                        "type": "connected",
                        "message": "Connected to Counselor Agent. Send full transcripts array to get analysis.",
                    }
                )
            )

            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get("type") == "transcript":
                        transcripts = data.get("transcripts", [])

                        # Validate and get last transcript
                        last_transcript = transcripts[-1] if transcripts else None
                        if not last_transcript:
                            continue

                        speaker = last_transcript.get("speaker", "").lower()
                        text = last_transcript.get("text", "")

                        if speaker not in ["patient", "counselor"] or not text:
                            continue

                        logger.debug(
                            "Received %d transcripts, last speaker: %s",
                            len(transcripts),
                            speaker,
                        )

                        # Patient -> analyze, Counselor -> acknowledge
                        if speaker == "patient":
                            analysis = agent.analyze_conversation(
                                transcripts, previous_nudges=previous_nudges
                            )
                            previous_nudges = analysis.get("nudges", [])

                            logger.info(
                                "Analysis completed for patient message from %s",
                                websocket.remote_address,
                            )
                            await websocket.send(
                                json.dumps(
                                    {
                                        "type": "analysis",
                                        "problems": analysis.get("problems", []),
                                        "nudges": analysis.get("nudges", []),
                                        "sentiment": analysis.get(
                                            "sentiment", ["neutral"]
                                        ),
                                    }
                                )
                            )
                        else:
                            # Counselor message, just acknowledge
                            await websocket.send(
                                json.dumps(
                                    {
                                        "type": "acknowledged",
                                        "message": "Transcript received",
                                    }
                                )
                            )

                    elif data.get("type") == "ping":
                        await websocket.send(
                            json.dumps({"type": "pong", "message": "alive"})
                        )
                    else:
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "error",
                                    "message": f"Unknown message type: {data.get('type')}",
                                }
                            )
                        )
                except json.JSONDecodeError:
                    logger.warning(
                        "Invalid JSON received from %s", websocket.remote_address
                    )
                    await websocket.send(
                        json.dumps({"type": "error", "message": "Invalid JSON format"})
                    )
                except Exception as e:
                    logger.error(
                        "Error processing message from %s: %s",
                        websocket.remote_address,
                        str(e),
                        exc_info=True,
                    )
                    await websocket.send(
                        json.dumps({"type": "error", "message": f"Error: {str(e)}"})
                    )

        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected: %s", websocket.remote_address)
        except Exception as e:
            logger.error(
                "Error with client %s: %s",
                websocket.remote_address,
                str(e),
                exc_info=True,
            )
        finally:
            self.active_connections = max(0, self.active_connections - 1)
            logger.info("Connection closed: %s", websocket.remote_address)

    async def health_check(self, _request):
        """Health check endpoint."""
        return web.json_response(
            {
                "status": "healthy",
                "service": "counselor-agent",
                "active_connections": self.active_connections,
                "total_connections": self.total_connections,
            }
        )

    async def readiness_check(self, _request):
        """Readiness check endpoint - verifies service can accept requests."""
        try:
            if not self.api_key:
                return web.json_response(
                    {
                        "status": "not_ready",
                        "error": "API key not configured",
                    },
                    status=503,
                )
            CounselorAgent(api_key=self.api_key, model=self.model)
            return web.json_response(
                {
                    "status": "ready",
                    "service": "counselor-agent",
                }
            )
        except Exception as e:
            logger.error("Readiness check failed: %s", str(e))
            return web.json_response(
                {
                    "status": "not_ready",
                    "error": str(e),
                },
                status=503,
            )

    async def liveness_check(self, _request):
        """Liveness check endpoint - verifies service is running."""
        return web.json_response(
            {
                "status": "alive",
                "service": "counselor-agent",
            }
        )

    async def start_server(
        self, host: str = None, port: int = None, health_port: int = None
    ):
        host = host or os.getenv("WS_HOST", "localhost")
        port = port or int(os.getenv("WS_PORT", "8765"))
        health_port = health_port or int(os.getenv("HEALTH_PORT", "8767"))

        # Start HTTP server for health checks
        app = web.Application()
        app.router.add_get("/health", self.health_check)
        app.router.add_get("/ready", self.readiness_check)
        app.router.add_get("/live", self.liveness_check)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, health_port)
        await site.start()
        logger.info(
            "Health check endpoints available at http://%s:%s/health", host, health_port
        )

        # Start WebSocket server
        logger.info("Starting WebSocket server on ws://%s:%s", host, port)
        async with websockets.serve(self.handle_client, host, port):
            await asyncio.Future()


async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables")
        return
    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    server = CounselorWebSocketServer(api_key=api_key, model=model)
    await server.start_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
