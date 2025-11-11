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
    port = os.getenv("WS_PORT", "8765")
    uri = f"ws://{host}:{port}"

    transcripts = [
        {
            "speaker": "counselor",
            "text": "Thanks for being here today. How have you been feeling lately?",
        },
        {
            "speaker": "patient",
            "text": "It's been rough. I've been trying to cut back on using, but I keep slipping. I feel like I'm losing control.",
        },
        {
            "speaker": "counselor",
            "text": "That sounds like a heavy burden to carry. Can you tell me more about what happens before you use?",
        },
        {
            "speaker": "patient",
            "text": "Usually when I'm stressed or alone. It's like my head won't quiet down, and using is the only thing that feels like relief.",
        },
        {
            "speaker": "counselor",
            "text": "It makes sense that you'd look for something to calm that overwhelming stress. You're not alone in this, and there are ways we can work through those moments together.",
        },
    ]

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to Counselor Agent WebSocket Server\n")
            await websocket.recv()  # Welcome message

            for i in range(len(transcripts)):
                current_transcripts = transcripts[: i + 1]
                last_transcript = current_transcripts[-1]

                print(f"\n--- Step {i + 1}: {last_transcript['speaker']} ---")
                print(f"  {last_transcript['text']}")

                message = {"type": "transcript", "transcripts": current_transcripts}
                await websocket.send(json.dumps(message))
                response = await websocket.recv()
                data = json.loads(response)

                if data.get("type") == "analysis":
                    print("\n" + "=" * 60)
                    print("ANALYSIS RESULTS:")
                    print("=" * 60)
                    print("\nPROBLEMS:")
                    for problem in data.get("problems", []):
                        print(f"  - {problem}")
                    print("\nNUDGES:")
                    for nudge in data.get("nudges", []):
                        print(f"  - {nudge}")
                    print("\nSENTIMENT:")
                    print(f"  {', '.join(data.get('sentiment', ['neutral']))}")
                    print("=" * 60)
                elif data.get("type") == "acknowledged":
                    print(f"✓ {data.get('message', 'Received')}")

    except (ConnectionRefusedError, OSError):
        print("Error: Could not connect to server.")
        print("Make sure the WebSocket server is running: python websocket_server.py")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_counselor_agent())
