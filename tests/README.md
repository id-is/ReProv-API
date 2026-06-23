# Tests

A small suite covering the most useful, self-contained logic. The tests do not
require MySQL, Keycloak, or REANA — external calls are mocked and the DB session
is stubbed. `conftest.py` sets dummy env vars and puts `src/` on the path.

## What's covered

**Unit**
- `test_cwl.py` — CWL transforms: resource-monitoring wrapper, mapping step, and
  AIoD `valueFromPlatform` resolution (success and HTTP-error paths).
- `test_prov_resolve.py` — `_resolve_cwl_files` input/output/final classification.
- `test_execution_helpers.py` — exit-code parsing, command cleaning, and AIoD
  content fetch over `file://` and `http(s)`.
- `test_auth_roles.py` — the `require_roles` dependency allows/denies correctly.

**Integration**
- `test_api_rbac.py` — drives the real FastAPI router to confirm RBAC: non-admin
  delete → 403, admin delete passes the gate, standard user can list.

## Running

The app dependencies (fastapi, ruamel, prov, …) are already in the API image, so
the simplest way is to run inside it:

```bash
docker run --rm -v "$PWD:/app" -w /app reprov-api-api \
  bash -c "pip install -q -r tests/requirements.txt && python -m pytest tests -q"
```

Or, in a local virtualenv with `requirements.txt` + `tests/requirements.txt`
installed:

```bash
python -m pytest tests -q
```
