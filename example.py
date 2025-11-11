"""
Example WebSocket Client for Counselor Agent
"""

import asyncio
import json
import os
from dotenv import load_dotenv
import websockets

load_dotenv()


async def test_counselor_agent():
    host = os.getenv("WS_HOST", "localhost")
    port = os.getenv("WS_PORT", "3002")
    uri = f"ws://{host}:{port}"

    transcripts = [
        {
            "counselor": "Thanks for being here today. How have you been feeling lately?",
        },
        {
            "patient": "It's been rough. I've been trying to cut back on using, but I keep slipping. I feel like I'm losing control.",
        },
        {
            "counselor": "That sounds like a heavy burden to carry. Can you tell me more about what happens before you use?",
        },
        {
            "patient": "Usually when I'm stressed or alone. It's like my head won't quiet down, and using is the only thing that feels like relief.",
        },
        {
            "counselor": "It makes sense that you'd look for something to calm that overwhelming stress. You're not alone in this, and there are ways we can work through those moments together.",
        },
    ]

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to Counselor Agent WebSocket Server\n")
            await websocket.recv()  # Welcome message

            for i in range(len(transcripts)):
                current_transcripts = transcripts[: i + 1]
                print(current_transcripts)
                print("\n" + "=" * 60)
                text = ""
                for docs in current_transcripts:
                    for k, v in docs.items():
                        text = text + f"{k}: {v} \n"

                message = {"type": "transcript", "transcripts": text}
                await websocket.send(json.dumps(message))
                response = await websocket.recv()
                data = json.loads(response)

                if data.get("type") == "analysis":
                    data = data.get("message", {})
                    for k, v in data.items():
                        print(f"--> {k}: {v}")
                elif data.get("type") == "acknowledged":
                    pass
                    # print(f"✓ {data.get('message', 'Received')}")

    except (ConnectionRefusedError, OSError):
        print("Error: Could not connect to server.")
        print("Make sure the WebSocket server is running: python websocket_server.py")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_counselor_agent())
