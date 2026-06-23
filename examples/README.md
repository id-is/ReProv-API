# Examples

Example CWL workflows for ReProv-API, copied from
[id-is/provenance-examples](https://github.com/id-is/provenance-examples/).

Each workflow's `.cwl` file is the `spec_file` and the accompanying `.yaml` file
(where present) is the optional `input_file` used when registering a workflow via
`POST /workflow_registry/register/`.

## Workflows

| Folder | Spec file | Input file | Notes |
|--------|-----------|------------|-------|
| `workflows/mnist` | `mnist.cwl` | `mnist.yaml` | MNIST training/evaluation pipeline. |
| `workflows/mnist-aiod` | `mnist-aiod.cwl` | `mnist-aiod.yaml` | MNIST variant using the `valueFromPlatform` keyword to pull an input dataset from the AIoD platform. |
| `workflows/mnist-fail` | `mnist_fail.cwl` | `mnist.yaml` | A deliberately failing run, useful for testing failed-step provenance. |
| `workflows/heatwave` | `heatwave.cwl` | `heatwave.yaml` | Heatwave analysis pipeline. |
| `workflows/hist` | `hist.cwl` | — | Histogram workflow (no input file). |

Some folders include a `results/prov.png` showing the provenance graph produced by
`GET /provenance/draw/{execution_id}`.

## Supporting files

The workflows run inside the Docker image referenced by each CWL's
`DockerRequirement` (e.g. `antganios/mnist-python-env`). That image is built from:

- `python-tools/` — the Python scripts invoked by the workflow steps.
- `Dockerfile` / `requirements.txt` — recipe for the execution-environment image.

These are included so the examples are reproducible; you do not need them to
register or execute the workflows if the referenced image is already published.
