"""Unit tests for the CWL transforms in utils.cwl."""
from ruamel.yaml import YAML

from utils.cwl import add_resource_monitoring, add_mapping_step, replace_placeholders

_yaml = YAML(typ="safe", pure=True)

SIMPLE = b"""
class: Workflow
cwlVersion: v1.0
inputs: []
outputs: []
steps:
  hello:
    in: {}
    out: []
    run:
      class: CommandLineTool
      inputs: {}
      outputs:
        - id: out
          type: File
          outputBinding: {glob: out.txt}
      baseCommand: echo
"""


def test_add_resource_monitoring_wraps_command():
    d = _yaml.load(add_resource_monitoring(SIMPLE))
    run = d["steps"]["hello"]["run"]
    assert run["baseCommand"] == "python"
    # the original command is preserved and metrics are emitted
    assert "echo" in run["arguments"]
    assert any("REPROV_METRICS" in str(a) for a in run["arguments"])


def test_add_mapping_step_adds_map_and_output():
    d = _yaml.load(add_mapping_step(SIMPLE))
    assert "map" in d["steps"]
    assert any(o.get("id") == "mapping" for o in d["outputs"])


AIOD_SPEC = b"""
class: Workflow
cwlVersion: v1.0
inputs:
  - id: ds
    type: File
    valueFromPlatform: "{{http://aiod/datasets/1}}"
outputs: []
steps:
  s:
    in: {ds: ds}
    out: []
    run: {class: CommandLineTool, inputs: {ds: File}, outputs: [], baseCommand: cat}
"""


class _Resp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


def test_replace_placeholders_resolves_aiod(monkeypatch):
    payload = {"distribution": [{"name": "data.csv",
                                 "content_url": "http://aiod/content/data.csv"}]}
    monkeypatch.setattr("utils.cwl.requests.get",
                        lambda *a, **k: _Resp(200, payload))
    new_spec, entities = replace_placeholders(AIOD_SPEC)
    assert len(entities) == 1
    assert entities[0]["content_url"] == "http://aiod/content/data.csv"
    assert entities[0]["filename"] == "data.csv"
    # the placeholder keyword is removed from the rewritten spec
    d = _yaml.load(new_spec)
    assert "valueFromPlatform" not in d["inputs"][0]


def test_replace_placeholders_returns_none_on_http_error(monkeypatch):
    monkeypatch.setattr("utils.cwl.requests.get", lambda *a, **k: _Resp(500))
    assert replace_placeholders(AIOD_SPEC) == (None, None)
