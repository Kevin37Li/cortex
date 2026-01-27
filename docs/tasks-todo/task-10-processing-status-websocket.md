# Task: Implement Processing Status WebSocket Endpoint

## Summary

Create a WebSocket endpoint that streams real-time processing status updates to the frontend. When items are being processed, the frontend receives events for each stage transition (parsing, chunking, embedding, extracting, completed, failed) enabling live progress indicators.

## Acceptance Criteria

- [ ] `WS /api/ws/processing` — WebSocket endpoint that streams processing events
- [ ] Events sent as JSON with structure: `{"type": "processing_update", "item_id": "...", "status": "...", "step": "...", "progress": 0.0-1.0}`
- [ ] Status values: `queued`, `processing`, `completed`, `failed`
- [ ] Step values: `parsing`, `chunking`, `embedding`, `extracting`, `validating`, `storing`
- [ ] Supports multiple concurrent WebSocket connections (broadcast to all)
- [ ] Processing queue emits events that the WebSocket endpoint relays
- [ ] Connection cleanup on disconnect (no resource leaks)
- [ ] Optional: client can subscribe to specific item_id updates by sending `{"subscribe": "item_id"}`

## Dependencies

- Task 8: Processing queue service (source of events)
- Phase 1: FastAPI WebSocket pattern from `docs/developer/python-backend/architecture.md`

## Technical Notes

- Per `docs/developer/architecture/python-sidecar.md`: WebSocket for real-time streaming updates
- Use `asyncio.Event` or a simple pub/sub pattern within the ProcessingQueue to broadcast status changes
- Each processing workflow step should emit a status update via a callback or event
- Keep the WebSocket implementation simple: no authentication (localhost only), no complex routing
- Use `fastapi.WebSocket` with `WebSocketDisconnect` exception handling
- Consider using a simple `ConnectionManager` class to track active WebSocket connections

## Event Format

```json
{
  "type": "processing_update",
  "item_id": "abc-123",
  "status": "processing",
  "step": "embedding",
  "progress": 0.6,
  "message": "Generating embeddings for 12 chunks"
}
```

## Connection Manager Pattern

```python
class ProcessingConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass  # Connection already closed
```

## Files to Create/Modify

**Create:**

- `python-backend/src/api/ws.py` — WebSocket endpoints and connection manager

**Modify:**

- `python-backend/src/main.py` — Register WebSocket routes
- `python-backend/src/services/processing.py` — Add event emission to queue worker
- `python-backend/src/workflows/processing.py` — Add progress callbacks to workflow nodes

## Verification

```bash
cd python-backend
uv run ruff check src/

# Manual test with websocat or similar:
# websocat ws://localhost:8742/api/ws/processing
# Then create an item in another terminal and watch for events
```
