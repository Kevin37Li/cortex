# Task: Implement Processing Status WebSocket Endpoint

## Summary

Create a WebSocket endpoint that streams real-time processing status updates to the frontend. When items are being processed, the frontend receives events for each stage transition (parse, chunk, extract metadata, validate, persist, complete/failed) so UI progress indicators can update live.

## Acceptance Criteria

- [x] `WS /api/ws/processing` exists and streams processing events (`python-backend/src/api/routes/ws.py:16`, `python-backend/src/main.py:112`)
- [x] Event payloads are validated against a typed `ProcessingUpdate` model before sending (`python-backend/src/api/websocket/manager.py:92`)
- [x] Event JSON shape: `{"type":"processing_update","item_id":"...","status":"...","step":"...","progress":0.0-1.0,"message":"..."}` (`python-backend/src/db/models.py:163`, `python-backend/src/api/websocket/manager.py:133`)
- [x] Status values use existing item status contract: `pending`, `processing`, `completed`, `failed` (`python-backend/src/db/models.py:141`)
- [x] Step values: `classify`, `parsing`, `chunking`, `extracting`, `validating`, `storing`, `completed`, `failed` (`python-backend/src/db/models.py:150`)
- [x] Supports multiple concurrent WebSocket connections (broadcast to all subscribers) (`python-backend/src/api/websocket/manager.py:89`, `python-backend/tests/test_api_ws_processing.py:47`)
- [x] Closed/broken connections are removed during send attempts (no leaked stale sockets) (`python-backend/src/api/websocket/manager.py:137`, `python-backend/tests/test_api_ws_processing.py:132`)
- [x] Fanout delivery is non-blocking for queue/workflow producers (slow WebSocket clients cannot stall processing workers) (`python-backend/src/services/processing.py:61`, `python-backend/src/api/websocket/manager.py:105`)
- [x] Backpressure policy is explicit and bounded (per-connection queue or bounded send task strategy with drop/disconnect cleanup) (`python-backend/src/api/websocket/manager.py:49`, `python-backend/src/api/websocket/manager.py:106`, `python-backend/tests/test_api_ws_processing.py:144`)
- [x] Processing workflow emits step-level events, queue/service relays them (queue does not own DB status transitions) (`python-backend/src/workflows/processing.py:120`, `python-backend/src/services/processing.py:101`)
- [x] Optional: client can subscribe to a specific `item_id` via `{"subscribe":"item_id"}`; default is all items (`python-backend/src/api/routes/ws.py:30`, `python-backend/src/api/websocket/manager.py:83`, `python-backend/tests/test_api_ws_processing.py:67`)

## Dependencies

- Task 8: Processing queue service (event relay integration)
- Task 9: Processing API endpoints (existing queue service surface)
- Task 7: Processing workflow nodes (source of per-step events)
- Task 11: Backend tests (WebSocket endpoint and event relay coverage)

## Technical Notes

- Keep route canonical as `/api/ws/processing` to match frontend task 17
- Per `docs/developer/architecture/python-sidecar.md`: use WebSocket for real-time streaming updates
- Use a lightweight internal pub/sub channel (for example, `asyncio.Queue` fanout or callback registry) so workflow event production is decoupled from WebSocket I/O
- Recommended pattern: producer -> internal broadcast hub -> per-connection bounded queue + sender task
- Do not `await send_json()` inline in queue/workflow producer paths for all connections
- Define behavior for slow consumers when queue is full (drop oldest/newest event or disconnect), and clean up connection state deterministically
- Workflow node execution should emit progress events; WebSocket layer should only handle subscription/filtering/delivery
- Keep implementation simple: localhost-only, no auth, no complex routing
- Use `fastapi.WebSocket` with `WebSocketDisconnect` handling

## Event Contract

```json
{
  "type": "processing_update",
  "item_id": "abc-123",
  "status": "processing",
  "step": "extracting",
  "progress": 0.75,
  "message": "Extracting summary and concepts"
}
```

### Step-to-Progress Mapping

Use deterministic progress values for consistent UI:

- `classify` -> `0.05`
- `parsing` -> `0.20`
- `chunking` -> `0.40`
- `extracting` -> `0.65`
- `validating` -> `0.85`
- `storing` -> `0.95`
- `completed` -> `1.0`
- `failed` -> keep last known progress (or `1.0` if failure occurs at terminal step)

### Workflow Node Mapping

Map existing workflow nodes in `src/workflows/processing.py` to websocket event steps:

- `classify` node -> `classify`
- `parse` node -> `parsing`
- `chunk` node -> `chunking`
- `extract_metadata` node -> `extracting`
- `validate` node -> `validating`
- `persist` node -> `storing`
- `complete` node -> `completed`
- `handle_error` node -> `failed`

## Connection Manager Pattern

```python
import asyncio
from contextlib import suppress
from dataclasses import dataclass


@dataclass
class ClientConnection:
    websocket: WebSocket
    send_queue: asyncio.Queue[dict]
    sender_task: asyncio.Task[None]


class ProcessingConnectionManager:
    def __init__(self, max_client_queue: int = 100) -> None:
        self.max_client_queue = max_client_queue
        self.active_connections: list[ClientConnection] = []

    async def connect(self, websocket: WebSocket) -> ClientConnection:
        await websocket.accept()
        send_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=self.max_client_queue)
        sender_task = asyncio.create_task(self._sender_loop(websocket, send_queue))
        connection = ClientConnection(
            websocket=websocket,
            send_queue=send_queue,
            sender_task=sender_task,
        )
        self.active_connections.append(connection)
        return connection

    async def disconnect(self, connection: ClientConnection) -> None:
        if connection not in self.active_connections:
            return
        self.active_connections.remove(connection)
        connection.sender_task.cancel()
        with suppress(Exception):
            await connection.sender_task

    async def _sender_loop(
        self,
        websocket: WebSocket,
        send_queue: asyncio.Queue[dict],
    ) -> None:
        while True:
            message = await send_queue.get()
            try:
                await websocket.send_json(message)
            except Exception:
                break
            finally:
                send_queue.task_done()

    async def broadcast(self, message: dict) -> None:
        stale: list[ClientConnection] = []
        for connection in list(self.active_connections):
            try:
                connection.send_queue.put_nowait(message)
            except asyncio.QueueFull:
                # Backpressure policy: disconnect slow consumers
                stale.append(connection)
        for connection in stale:
            await self.disconnect(connection)
```

## Files to Create/Modify

**Create:**

- `python-backend/src/api/routes/ws.py` — Processing websocket endpoint and subscribe message handling
- `python-backend/src/api/websocket/manager.py` — Connection manager with bounded queue fanout and cleanup
- `python-backend/tests/test_api_ws_processing.py` — WebSocket endpoint tests (broadcast, disconnect cleanup, optional subscription filter)

**Modify:**

- `python-backend/src/main.py` — Register WebSocket router
- `python-backend/src/services/processing.py` — Add internal event relay/pub-sub integration
- `python-backend/src/workflows/processing.py` — Emit step-level events from workflow nodes
- `python-backend/tests/services/test_processing.py` — Add queue/workflow relay tests
- `docs/developer/python-backend/architecture.md` — Align processing websocket route and event contract docs

## Verification

```bash
bun run python:lint
bun run python:test

# Manual test with websocat or similar:
# websocat ws://localhost:8742/api/ws/processing
# Then create an item in another terminal and watch for step events
```

---

## Implementation Details

_Tracked: 2026-02-09_

### Files Changed

| File                                               | Change   | Description                                                                                                               |
| -------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------- |
| `python-backend/src/api/routes/ws.py`              | Created  | Added `WS /api/ws/processing` endpoint and optional subscribe message handling.                                           |
| `python-backend/src/api/websocket/manager.py`      | Created  | Added connection manager with bounded per-client queues, fanout, subscription filters, and stale-client cleanup.          |
| `python-backend/src/api/websocket/__init__.py`     | Created  | Exported websocket manager types.                                                                                         |
| `python-backend/src/api/dependencies.py`           | Created  | Added `get_processing_ws_manager` dependency for websocket routes.                                                        |
| `python-backend/src/api/routes/__init__.py`        | Created  | Added route module exports including websocket routes.                                                                    |
| `python-backend/src/db/models.py`                  | Modified | Added typed `ProcessingStatus`, `ProcessingStep`, and `ProcessingUpdate` models for event contract validation.            |
| `python-backend/src/services/processing.py`        | Modified | Added processing update listener pub/sub, relay emission, and workflow callback wiring.                                   |
| `python-backend/src/workflows/processing.py`       | Modified | Emitted typed step-level updates with deterministic progress/message mapping from each workflow stage.                    |
| `python-backend/src/main.py`                       | Modified | Registered websocket router and connected queue update relay to websocket manager at app startup/shutdown.                |
| `python-backend/tests/test_api_ws_processing.py`   | Created  | Added websocket endpoint and connection manager tests for broadcast, filter, stale cleanup, and slow-client backpressure. |
| `python-backend/tests/services/test_processing.py` | Modified | Added queue relay tests for callback wiring, unsubscribe behavior, and failing-listener cleanup.                          |
| `docs/developer/python-backend/architecture.md`    | Modified | Updated backend architecture docs for route layout and processing websocket contract.                                     |

### Dependencies Added

- None.

### Acceptance Criteria Status

- [x] Endpoint implemented in `python-backend/src/api/routes/ws.py:16` and mounted in `python-backend/src/main.py:112`.
- [x] Typed payload validation enforced in `python-backend/src/api/websocket/manager.py:92`.
- [x] Event payload schema defined in `python-backend/src/db/models.py:163` and serialized in `python-backend/src/api/websocket/manager.py:133`.
- [x] Status contract encoded in `python-backend/src/db/models.py:141`.
- [x] Step contract encoded in `python-backend/src/db/models.py:150`.
- [x] Multi-client fanout implemented in `python-backend/src/api/websocket/manager.py:89` and verified in `python-backend/tests/test_api_ws_processing.py:47`.
- [x] Broken connection cleanup implemented in `python-backend/src/api/websocket/manager.py:137` and verified in `python-backend/tests/test_api_ws_processing.py:132`.
- [x] Non-blocking producer path implemented by sync relay + `put_nowait` in `python-backend/src/services/processing.py:61` and `python-backend/src/api/websocket/manager.py:105`.
- [x] Explicit bounded backpressure policy implemented in `python-backend/src/api/websocket/manager.py:49` and `python-backend/src/api/websocket/manager.py:106`, verified in `python-backend/tests/test_api_ws_processing.py:144`.
- [x] Workflow emits step updates while queue relays only in `python-backend/src/workflows/processing.py:120` and `python-backend/src/services/processing.py:101`.
- [x] Optional `item_id` subscriptions implemented in `python-backend/src/api/routes/ws.py:30` and `python-backend/src/api/websocket/manager.py:83`, verified in `python-backend/tests/test_api_ws_processing.py:67`.

---

## Learning Report

_Generated: 2026-02-09_

### Summary

Processing status streaming now uses a decoupled event flow: workflow nodes emit typed updates, queue/service relays updates synchronously, and websocket delivery is handled through per-connection bounded queues and sender tasks.

### Patterns and Decisions

- Chose typed `ProcessingUpdate` events (`src/db/models.py`) as the single contract across workflow, queue relay, and websocket layers.
- Used producer->listener relay (`ProcessingQueue.subscribe_processing_updates`) instead of direct websocket calls from workflow/queue code to keep delivery concerns isolated.
- Used per-connection bounded queues with disconnect-on-full to keep producers non-blocking and make backpressure behavior deterministic.
- Added optional per-connection `item_id` subscriptions as a lightweight filter without changing the producer contract.

### Challenges and Solutions

- Challenge: Avoid stalling workflow/queue producers while still fanning out to many websocket clients.
  - Solution: Relay updates synchronously to `manager.broadcast()`, which uses `put_nowait` and async cleanup tasks.
- Challenge: Keep stale sockets from leaking after send failures.
  - Solution: Sender loop schedules deterministic disconnect on send errors and removes the connection from the manager map.
- Challenge: Keep progress semantics consistent for frontend UX.
  - Solution: Centralized step->progress/message mapping in workflow with explicit failed-step behavior.

### Lessons Learned

- A typed internal event model simplifies both runtime validation and testability across async boundaries.
- Separating event production from transport delivery keeps the queue/service layer focused on orchestration and reliability.
- Backpressure must be explicit in realtime APIs; bounded queues plus clear drop/disconnect behavior are easier to reason about than implicit buffering.

### Documentation Impact

- Reviewed and updated `docs/developer/python-backend/architecture.md` to reflect:
  - the `api/routes` and `api/websocket` module layout,
  - canonical `WS /api/ws/processing` route,
  - processing update event contract and optional subscription payload.
- Docs reviewer check (targeted to this task scope) found no additional required doc updates beyond the architecture changes above.
