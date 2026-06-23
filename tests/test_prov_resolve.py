"""Unit test for prov._resolve_cwl_files (CWL file-relationship resolution)."""
from crud.prov import _resolve_cwl_files


def test_resolve_cwl_files_classifies_inputs_outputs_and_final():
    spec = {
        "inputs": [{"id": "results_name", "default": "results.txt"}],
        "outputs": [{"id": "results", "type": "File",
                     "outputSource": "evaluate/results"}],
        "steps": {
            "download": {
                "in": {},
                "run": {"inputs": {}, "outputs": [
                    {"id": "train", "type": "File",
                     "outputBinding": {"glob": "train.pkl"}}]},
            },
            "evaluate": {
                "in": {"tr": "download/train", "results_name": "results_name"},
                "run": {"inputs": {"tr": "File", "results_name": "string"},
                        "outputs": [{"id": "results", "type": "File",
                                     "outputBinding": {"glob": "$(inputs.results_name)"}}]},
            },
        },
    }
    files, step_inputs, step_outputs = _resolve_cwl_files(spec)

    # intermediate output of the download step
    assert files.get("train.pkl") == "workflow_intermediate_result_file"
    # dynamic glob resolved via the top-level input default, marked as final
    assert files.get("results.txt") == "workflow_final_result_file"
    # per-step relationships
    assert "train.pkl" in step_outputs["download"]
    assert "train.pkl" in step_inputs["evaluate"]
