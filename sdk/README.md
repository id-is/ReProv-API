# ReProv Python SDK

A thin Python client over the ReProv REST API. It abstracts authentication and
the workflow registration, execution, and provenance endpoints into high-level
method calls.

## Install

The SDK only depends on `requests`:

```bash
pip install requests
```

Then make the package importable (e.g. run from this `sdk/` directory or add it
to your `PYTHONPATH`).

## Usage

```python
from reprov import ReProvClient

# Authenticate via Keycloak (password grant) ...
client = ReProvClient.from_keycloak(
    base_url="http://localhost:9090",
    keycloak_token_url="http://localhost:8080/realms/prov/protocol/openid-connect/token",
    client_id="api",
    username="user1",
    password="password1",
)

# ... or pass an existing bearer token directly:
# client = ReProvClient("http://localhost:9090", token="<JWT>")

# Register, execute, and capture provenance
reg = client.register_workflow("mnist", "1.0", "mnist.cwl", "mnist.yaml")
registry_id = reg["data"]["registry_id"]

ex = client.execute_workflow(registry_id)
execution_id = ex["data"]["execution_id"]

client.capture_provenance(execution_id)
prov = client.export_provenance_json(execution_id)   # W3C PROV-JSON dict
client.draw_provenance(execution_id, "provenance.png")
client.download_outputs(execution_id, "outputs.zip")
```

## Methods

| Area | Methods |
|------|---------|
| Registry | `register_workflow`, `list_workflows`, `get_workflow`, `update_workflow`, `delete_workflow` |
| Execution | `execute_workflow`, `list_executions`, `get_execution`, `get_execution_logs`, `delete_executions`, `download_inputs`, `download_outputs` |
| Provenance | `capture_provenance`, `export_provenance_json`, `draw_provenance` |

Unsuccessful API responses raise `reprov.client.ReProvError`.
