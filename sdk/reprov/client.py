"""ReProv Python SDK client.

A high-level wrapper over the ReProv REST API that abstracts authentication and
the workflow registration, execution, and provenance endpoints into simple
Python method calls.

Example
-------
    from reprov import ReProvClient

    client = ReProvClient.from_keycloak(
        base_url="http://localhost:9090",
        keycloak_token_url="http://localhost:8080/realms/prov/protocol/openid-connect/token",
        client_id="api",
        username="user1",
        password="password1",
    )

    reg = client.register_workflow("mnist", "1.0", "mnist.cwl", "mnist.yaml")
    rid = reg["data"]["registry_id"]
    ex = client.execute_workflow(rid)
    eid = ex["data"]["execution_id"]
    client.capture_provenance(eid)
    client.draw_provenance(eid, "provenance.png")
    prov = client.export_provenance_json(eid)
"""
from __future__ import annotations

import requests


class ReProvError(Exception):
    """Raised when the ReProv API returns an unsuccessful response."""


class ReProvClient:
    def __init__(self, base_url: str, token: str, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    # ----------------------------------------------------------------- auth
    @classmethod
    def from_keycloak(cls, base_url, keycloak_token_url, client_id,
                      username, password, client_secret="", timeout=120):
        """Obtain a token via the Keycloak password grant and return a client."""
        data = {
            "client_id": client_id,
            "grant_type": "password",
            "username": username,
            "password": password,
        }
        if client_secret:
            data["client_secret"] = client_secret
        resp = requests.post(keycloak_token_url, data=data, timeout=timeout)
        resp.raise_for_status()
        token = resp.json()["access_token"]
        return cls(base_url, token, timeout=timeout)

    # -------------------------------------------------------------- helpers
    @property
    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        resp = requests.request(
            method, url, headers=self._headers, timeout=self.timeout, **kwargs
        )
        resp.raise_for_status()
        return resp

    def _json(self, method, path, **kwargs):
        data = self._request(method, path, **kwargs).json()
        # ReProv wraps responses as {success, message, data, error_code}
        if isinstance(data, dict) and data.get("success") is False:
            raise ReProvError(data.get("message", "request failed"))
        return data

    # ----------------------------------------------------- workflow registry
    def register_workflow(self, name, version, spec_file, input_file=None):
        files = {"spec_file": _open(spec_file)}
        if input_file is not None:
            files["input_file"] = _open(input_file)
        try:
            return self._json(
                "POST", "/workflow_registry/register/",
                params={"name": name, "version": version}, files=files,
            )
        finally:
            for f in files.values():
                f.close()

    def list_workflows(self):
        return self._json("GET", "/workflow_registry/")

    def get_workflow(self, registry_id):
        return self._json("GET", f"/workflow_registry/{registry_id}")

    def update_workflow(self, registry_id, name=None, version=None,
                        spec_file=None, input_file=None):
        params = {}
        if name is not None:
            params["name"] = name
        if version is not None:
            params["version"] = version
        files = {}
        if spec_file is not None:
            files["spec_file"] = _open(spec_file)
        if input_file is not None:
            files["input_file"] = _open(input_file)
        try:
            return self._json(
                "PUT", f"/workflow_registry/update/{registry_id}",
                params=params, files=files or None,
            )
        finally:
            for f in files.values():
                f.close()

    def delete_workflow(self, registry_id):
        return self._json("DELETE", f"/workflow_registry/delete/{registry_id}")

    # ---------------------------------------------------- workflow execution
    def execute_workflow(self, registry_id):
        return self._json("POST", f"/workflow_execution/execute/{registry_id}")

    def list_executions(self):
        return self._json("GET", "/workflow_execution/")

    def get_execution(self, execution_id):
        return self._json("GET", f"/workflow_execution/{execution_id}")

    def get_execution_logs(self, execution_id):
        return self._json("GET", f"/workflow_execution/{execution_id}/logs")

    def delete_executions(self, registry_id=None, reana_name=None):
        params = {}
        if registry_id is not None:
            params["registry_id"] = registry_id
        if reana_name is not None:
            params["reana_name"] = reana_name
        return self._json("DELETE", "/workflow_execution/delete/", params=params)

    def download_inputs(self, execution_id, out_path):
        return self._download(f"/workflow_execution/inputs/{execution_id}", out_path)

    def download_outputs(self, execution_id, out_path="outputs.zip"):
        return self._download(f"/workflow_execution/outputs/{execution_id}", out_path)

    # ------------------------------------------------------------ provenance
    def capture_provenance(self, execution_id):
        return self._json("GET", f"/provenance/capture/{execution_id}")

    def export_provenance_json(self, execution_id):
        return self._json("GET", f"/provenance/json/{execution_id}")

    def draw_provenance(self, execution_id, out_path):
        return self._download(f"/provenance/draw/{execution_id}", out_path)

    # ------------------------------------------------------------- internals
    def _download(self, path, out_path):
        resp = self._request("GET", path)
        ctype = resp.headers.get("content-type", "")
        # File endpoints return binary; error cases return JSON
        if "application/json" in ctype:
            data = resp.json()
            if isinstance(data, dict) and data.get("success") is False:
                raise ReProvError(data.get("message", "download failed"))
            return data
        with open(out_path, "wb") as f:
            f.write(resp.content)
        return out_path


def _open(path_or_file):
    """Accept a filesystem path or an already-open binary file object."""
    if hasattr(path_or_file, "read"):
        return path_or_file
    return open(path_or_file, "rb")
