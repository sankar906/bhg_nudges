# Counselor Agent - WebSocket Server

Real-time AI-powered counselor assistant that provides nudges, problem identification, and sentiment analysis during patient-counselor conversations.

## Quick Start

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1
WS_HOST=localhost
WS_PORT=8765
HEALTH_PORT=8766
```

### 3. Start Server

```bash
python websocket_server.py
```

Server starts on:
- **WebSocket**: `ws://localhost:3002`
- **Health Checks**: `http://localhost:3001`

## Connecting to WebSocket

### Python Example

```python
import asyncio
import json
import websockets

async def connect():
    uri = "ws://localhost:3002"
    async with websockets.connect(uri) as websocket:
        # Receive welcome message
        welcome = await websocket.recv()
        print(welcome)

        # Client maintains full conversation (array of {speaker, text})
        full_conversation = []

        # Step 1: Counselor speaks
        full_conversation.append({
            "speaker": "counselor",
            "text": "Hello, how are you feeling today?"
        })
        await websocket.send(json.dumps({
            "type": "transcript",
            "transcripts": full_conversation
        }))
        # Expect: acknowledged
        print(await websocket.recv())

        # Step 2: Patient responds
        full_conversation.append({
            "speaker": "patient",
            "text": "I've been feeling really anxious lately."
        })
        await websocket.send(json.dumps({
            "type": "transcript",
            "transcripts": full_conversation
        }))
        # Expect: analysis
        response = await websocket.recv()
        data = json.loads(response)
        print(data)

asyncio.run(connect())
```

### JavaScript Example

```javascript
const ws = new WebSocket('ws://localhost:3002');
let fullConversation = [];

ws.onopen = () => {
  // Step 1: Counselor speaks
  fullConversation.push({
    speaker: "counselor",
    text: "Hello, how are you feeling today?"
  });
  ws.send(JSON.stringify({
    type: "transcript",
    transcripts: fullConversation
  }));

  // Step 2: Patient responds
  fullConversation.push({
    speaker: "patient",
    text: "I've been feeling really anxious lately."
  });
  ws.send(JSON.stringify({
    type: "transcript",
    transcripts: fullConversation
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

## WebSocket Data I/O (Simple)

### Input (Client → Server)

Send the full conversation array every time. The server decides based on the last item.

can give 'plain text' or 'json' formate

json structure
```json
{
  "type": "transcript",
  "transcripts": [
    {"counselor": "Hello, how are you feeling today?"},
    {"patient": "I've been feeling really anxious lately."}
  ]
}
```


Optional ping:

```json
{ "type": "ping" }
```

### Output (Server → Client)

#### Connection Confirmation

```json
{
  "type": "connected",
  "message": "Connected to Counselor Agent. Send full transcripts array to get analysis."
}
```

#### Analysis Response (Patient Messages)

```json
{
  "type": "analysis",
  "message" : {
            "problems": ["problem1", "problem2" ],
            "nudges": ["nudge1", "nudge2", "nudge3"],
            "sentiment": ["word1", "word2"],
            "follow_up": ""
            "risk": ["low", "medium", "high"]
            }
}
```

Note: Previous nudges are considered to build on earlier suggestions.

#### Acknowledgment (Counselor Messages)

```json
{
  "type": "acknowledged",
  "message": "Transcript received"
}
```

#### Error Response

```json
{
  "type": "error",
  "message": "Speaker must be 'patient' or 'counselor'"
}
```

## Health Check Endpoints

- **`/health`**: `http://localhost:8766/health` - General health check
- **`/ready`**: `http://localhost:8766/ready` - Readiness probe
- **`/live`**: `http://localhost:8766/live` - Liveness probe

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `OPENAI_MODEL` | Model to use | `gpt-3.5-turbo` |
| `WS_HOST` | WebSocket server host | `localhost` |
| `WS_PORT` | WebSocket server port | `8765` |
| `HEALTH_PORT` | Health check server port | `8766` |

## Deployment

### For Production

1. **Change host binding** in `.env`:
   ```env
   WS_HOST=0.0.0.0
   ```

2. **Open firewall ports**:
   - Port `8765` (WebSocket)
   - Port `8766` (Health checks)

3. **Use reverse proxy** (recommended for SSL/TLS):
   ```nginx
   location /ws {
       proxy_pass http://localhost:8765;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
   }
   ```

### Docker Example

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV WS_HOST=0.0.0.0
EXPOSE 8765 8766
CMD ["python", "websocket_server.py"]
```

## Important Notes

- **Full Transcripts Array**: Client sends the complete conversation array each time (not incremental)
- **Client Maintains History**: The client maintains the full conversation and sends it on every update
- **Server Decision**: Server checks the **last transcript** in the array:
  - Last transcript is `"patient"` → Analyze full conversation with previous nudges
  - Last transcript is `"counselor"` → Return acknowledgment
- **No Server Storage**: Server does NOT maintain conversation history, only previous nudges per connection
- **Previous Nudges**: The system includes previous nudges in context, so new suggestions build upon earlier ones
- **Per Connection**: Each WebSocket connection maintains its own previous nudges context
- **No Persistence**: Previous nudges are cleared when connection closes

## Troubleshooting

- **Connection refused**: Check if server is running and port is correct
- **API key errors**: Verify `OPENAI_API_KEY` is set in `.env`
- **No analysis**: Only patient messages return analysis, counselor messages return acknowledgment
