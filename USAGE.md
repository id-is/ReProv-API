# Usage

A short end-to-end walkthrough of the ReProv workflow lifecycle:
**authenticate → register → execute → monitor → capture provenance → export**.

It assumes the stack is running (`docker-compose up -d`, see [README](README.md))
with the API on `http://localhost:9090` and Keycloak on `http://localhost:8080`.
Example workflows live in [`examples/`](examples/README.md).

## 1. Authenticate

All endpoints require a Keycloak bearer token. With the bundled realm, log in as
`user1` / `password1` (client `api`):

```bash
TOKEN=$(curl -s -X POST \
  http://localhost:8080/realms/prov/protocol/openid-connect/token \
  -d client_id=api -d grant_type=password \
  -d username=user1 -d password=password1 | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
AUTH="Authorization: Bearer $TOKEN"
```

You can also authenticate interactively via the Swagger UI at
`http://localhost:9090/docs` (Authorize → client_id `api`).

## 2. Register a workflow

Upload a CWL spec (and optional input YAML). `name`+`version` must be unique.

```bash
curl -s -X POST "http://localhost:9090/workflow_registry/register/?name=mnist&version=1.0" \
  -H "$AUTH" \
  -F "spec_file=@examples/workflows/mnist/mnist.cwl" \
  -F "input_file=@examples/workflows/mnist/mnist.yaml"
# -> { "success": true, "data": { "registry_id": 1, ... } }
```

List / inspect / delete:

```bash
curl -s "http://localhost:9090/workflow_registry/"       -H "$AUTH"
curl -s "http://localhost:9090/workflow_registry/1"      -H "$AUTH"
curl -s -X DELETE "http://localhost:9090/workflow_registry/delete/1" -H "$AUTH"
```

## 3. Execute

```bash
curl -s -X POST "http://localhost:9090/workflow_execution/execute/1" -H "$AUTH"
# -> { "success": true, "data": { "execution_id": 1, "reana_id": "...", ... } }
```

## 4. Monitor

Step status, exit codes, and per-step resource usage are captured automatically
in the background:

```bash
curl -s "http://localhost:9090/workflow_execution/1"        -H "$AUTH"   # status + steps
curl -s "http://localhost:9090/workflow_execution/1/logs"   -H "$AUTH"   # live per-step logs
```

Download artefacts once the run is finished:

```bash
curl -s "http://localhost:9090/workflow_execution/outputs/1" -H "$AUTH" -o outputs.zip
```

## 5. Capture and export provenance

Capture assembles the recorded run into a W3C PROV graph (works for both
finished and failed runs):

```bash
curl -s "http://localhost:9090/provenance/capture/1" -H "$AUTH"
curl -s "http://localhost:9090/provenance/json/1"    -H "$AUTH" -o provenance.json   # PROV-JSON
curl -s "http://localhost:9090/provenance/draw/1"    -H "$AUTH" -o provenance.png    # PNG graph
```

Failed steps are recorded with their status, exit code, and error message, and
are highlighted in red in the PNG.

## AIoD-linked inputs

A CWL input may reference a dataset in the [AI-on-Demand](https://aiod.eu)
catalogue instead of a literal value:

```yaml
inputs:
  - id: dataset
    type: File
    valueFromPlatform: "{{https://api.aiodp.eu/datasets/239}}"
```

On execution ReProv fetches the dataset's distribution `content_url`, stages it
into REANA, and records it in the provenance graph as an `external_file` entity
linked to the consuming step. See `examples/workflows/mnist-aiod`.

## Using the Python SDK

The [`sdk/`](sdk/README.md) package wraps the same REST API:

```python
from reprov import ReProvClient

client = ReProvClient.from_keycloak(
    base_url="http://localhost:9090",
    keycloak_token_url="http://localhost:8080/realms/prov/protocol/openid-connect/token",
    client_id="api", username="user1", password="password1",
)

rid = client.register_workflow("mnist", "1.0",
                               "examples/workflows/mnist/mnist.cwl",
                               "examples/workflows/mnist/mnist.yaml")["data"]["registry_id"]
eid = client.execute_workflow(rid)["data"]["execution_id"]

client.capture_provenance(eid)
client.draw_provenance(eid, "provenance.png")
prov = client.export_provenance_json(eid)
```

## Response shape

JSON endpoints return a uniform envelope:

```json
{ "success": true, "message": "...", "data": { }, "error_code": null }
```

On error, `success` is `false`, `error_code` carries an HTTP-style code, and
`message` explains the problem. The full endpoint reference is in the
[README](README.md#endpoints) and the live OpenAPI docs at `/docs`.
