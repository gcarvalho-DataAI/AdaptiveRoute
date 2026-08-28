# API Reference

Base URL for local development:

```text
http://127.0.0.1:8090
```

All JSON endpoints use `Content-Type: application/json`, except file upload.

List endpoints accept optional pagination query parameters:

```text
?skip=0&limit=100
```

`limit` is bounded to 1-500.

## Health

### `GET /health`

Returns service health.

```bash
curl -sS http://127.0.0.1:8090/health
```

## Conversations and Memory

### `POST /v1/conversations`

Create a conversation.

```json
{
  "title": "Route ROUTE-001 disruption",
  "scenario_id": "demo-cvrp-8",
  "metadata": {"route_id": "ROUTE-001"}
}
```

### `GET /v1/conversations`

List conversations.

### `GET /v1/conversations/{conversation_id}`

Get one conversation.

### `DELETE /v1/conversations/{conversation_id}`

Delete a conversation and associated records.

### `GET /v1/conversations/{conversation_id}/messages`

List messages for a conversation.

### `POST /v1/conversations/{conversation_id}/messages`

Append a message.

```json
{
  "role": "user",
  "content": "C3 to C5 is blocked. Should I replan?",
  "metadata": {"route_id": "ROUTE-001"}
}
```

### `GET /v1/conversations/{conversation_id}/agent-runs`

List stored agent runs/traces.

### `GET /v1/conversations/{conversation_id}/context`

Return the rolling context window.

## Agentic Replanning

### `POST /v1/agentic/replan`

Run the agentic route workflow from natural language.

```bash
curl -sS http://127.0.0.1:8090/v1/agentic/replan \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need you to replan my route ROUTE-001. C1 to C3 is blocked by an accident.",
    "conversation_id": "optional-conversation-id",
    "scenario_id": "demo-cvrp-8"
  }' | python3 -m json.tool
```

The response includes:

- extracted event;
- candidate plan;
- candidate validation;
- repaired candidate, if attempted;
- final plan;
- final validation;
- comparison against base plan;
- trace.

## Scenarios

### `POST /v1/scenarios/demo`

Seed the demo CVRP scenario.

```bash
curl -sS -X POST http://127.0.0.1:8090/v1/scenarios/demo
```

### `GET /v1/scenarios`

List scenarios.

### `GET /v1/scenarios/{scenario_id}`

Get one scenario.

### `PUT /v1/scenarios/{scenario_id}`

Create or replace a scenario.

### `DELETE /v1/scenarios/{scenario_id}`

Delete a scenario.

### `POST /v1/scenarios/from-orders`

Create a scenario from an order payload.

Main input fields:

- scenario id;
- depot address and coordinates;
- orders with delivery coordinates, weight and optional pickup/priority fields;
- vehicle count;
- vehicle capacity;
- road-distance flag.

### `POST /v1/scenarios/from-orders-file`

Create a scenario from uploaded CSV/XLSX.

Required form fields:

- `file`;
- `scenario_id`;
- `depot_address`;
- `depot_lat`;
- `depot_lng`;
- `vehicle_count`;
- `vehicle_capacity`;
- `use_road_distance`.

Required spreadsheet columns:

- delivery latitude;
- delivery longitude;
- weight.

Optional columns:

- order id;
- pickup address;
- pickup latitude;
- pickup longitude;
- delivery address;
- volume;
- priority.

## Operational Routes

### `POST /v1/operational-routes`

Create or reset an operational route record.

```json
{
  "id": "ROUTE-001",
  "driver_id": "DRV-QUEENS-01",
  "scenario_id": "demo-cvrp-8",
  "status": "assigned",
  "metadata": {}
}
```

### `GET /v1/operational-routes`

List operational routes.

### `GET /v1/operational-routes/{route_id}`

Get one operational route.

## Drivers

### `POST /v1/drivers`

Create a driver and associated vehicle/access metadata.

```json
{
  "id": "DRV-BROOKLYN-01",
  "name": "Sofia Ramirez",
  "vehicle_id": "VAN-BK-033",
  "capacity": 20,
  "status": "available",
  "region": "Brooklyn North",
  "shift_start": "08:00",
  "shift_end": "16:00",
  "metadata": {
    "username": "sofia.ramirez",
    "temporary_password": "route-demo-01"
  }
}
```

### `GET /v1/drivers`

List drivers.

### `GET /v1/drivers/{driver_id}`

Get one driver.

### `PUT /v1/drivers/{driver_id}`

Update driver profile, vehicle and access metadata.

### `DELETE /v1/drivers/{driver_id}`

Delete a driver. Existing routes assigned to that driver are retained but marked with a removed-driver reference.

## Driver Portal

### `POST /v1/driver-portal/login`

Authenticate a driver and return assigned routes.

```json
{
  "username": "sofia.ramirez",
  "password": "route-demo-01"
}
```

### `POST /v1/driver-portal/routes/{route_id}/status`

Update status of the authenticated driver's own route.

Preferred authentication is Bearer token:

```bash
curl -sS -X POST http://127.0.0.1:8090/v1/driver-portal/routes/ROUTE-002/status \
  -H "Authorization: Bearer $DRIVER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"in_progress"}'
```

Compatibility payload:

```json
{
  "username": "sofia.ramirez",
  "password": "route-demo-01",
  "status": "in_progress"
}
```

### `PUT /v1/driver-portal/profile`

Update authenticated driver's password and capacity.

Preferred authentication is Bearer token:

```bash
curl -sS -X PUT http://127.0.0.1:8090/v1/driver-portal/profile \
  -H "Authorization: Bearer $DRIVER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_password":"new-demo-pass","capacity":22}'
```

Compatibility payload:

```json
{
  "username": "sofia.ramirez",
  "password": "route-demo-01",
  "new_password": "new-demo-pass",
  "capacity": 22
}
```

## Planning Jobs

### `POST /v1/planning/daily`

Run daily planning synchronously.

### `POST /v1/planning/jobs`

Start an async planning job.

```json
{
  "scenario_id": "orders-nyc-demo",
  "route_prefix": "ROUTE",
  "include_demo_drivers": true
}
```

### `GET /v1/planning/jobs`

List planning jobs.

### `GET /v1/planning/jobs/{job_id}`

Get one planning job.

### `POST /v1/planning/jobs/{job_id}/cancel`

Request job cancellation.

### `DELETE /v1/planning/jobs/{job_id}`

Delete a planning job record.

## RAG

### `POST /v1/rag/ingest`

Ingest documentation into the RAG store.

```json
{
  "paths": ["README.md", "docs"]
}
```

### `GET /v1/rag/documents`

List ingested documents and chunk count.

### `POST /v1/rag/query`

Query the RAG store.

```json
{
  "query": "How does the routing policy model work?",
  "limit": 5
}
```

## Maps

### `POST /v1/maps/route-geometry`

Build route geometry for frontend visualization.

```json
{
  "plan": {
    "scenario_id": "demo-cvrp-8",
    "routes": [
      {"vehicle_id": "V1", "stops": ["D0", "C1", "C2", "D0"], "distance": 10.5, "load": 12}
    ],
    "total_distance": 10.5
  },
  "locations": {
    "D0": {"lat": 40.7431, "lng": -74.0106},
    "C1": {"lat": 40.7423, "lng": -74.0060},
    "C2": {"lat": 40.7410, "lng": -73.9900}
  },
  "overview": "full"
}
```
