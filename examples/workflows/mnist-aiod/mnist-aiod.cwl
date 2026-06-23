class: Workflow
cwlVersion: v1.0

requirements:
  DockerRequirement:
    dockerPull:
      antganios/mnist-python-env:latest

inputs:
  - id: dataset
    type: File
    valueFromPlatform: "{{http://localhost:8000/datasets/v1/239}}"
  - id: train_dataset_name
    type: string
    default: "mnist_train.pkl"
  - id: test_dataset_name
    type: string
    default: "mnist_test.pkl"
  - id: model_name
    type: string
    default: "mnist_model.keras"
  - id: results_name
    type: string
    default: "results.txt"

outputs:
  - id: results
    type: File
    outputSource: evaluate/results

steps:
  split:
    in:
      dataset: dataset
      train_dataset_name: train_dataset_name
      test_dataset_name: test_dataset_name
    out: [train_dataset, test_dataset]
    run:
      class: CommandLineTool
      inputs:
        dataset: File
        train_dataset_name: string
        test_dataset_name: string
      outputs:
        - id: train_dataset
          type: File
          outputBinding:
            glob: $(inputs.train_dataset_name)
        - id: test_dataset
          type: File
          outputBinding:
            glob: $(inputs.test_dataset_name)
      baseCommand: python
      arguments: ["/app/split.py", $(inputs.dataset.path),$(inputs.train_dataset_name),$(inputs.test_dataset_name) ] 
  train:
    in:
      train_dataset: split/train_dataset
      model_name: model_name  
    out: [model]
    run:
      class: CommandLineTool
      inputs:
        train_dataset: File
        model_name: string
     
      outputs:
        - id: model
          type: File
          outputBinding:
            glob: $(inputs.model_name)
      baseCommand: python
      arguments: ["/app/train.py", $(inputs.train_dataset.path),$(inputs.model_name)] 

  evaluate:
    in:
      test_dataset: split/test_dataset
      model: train/model
      results_name: results_name
    out: [results]
    run:
      class: CommandLineTool
      inputs:
        test_dataset: File
        model: File
        results_name: string
     
      outputs:
        - id: results
          type: File
          outputBinding:
            glob: $(inputs.results_name)
      baseCommand: python
      arguments: ["/app/evaluate.py", $(inputs.test_dataset.path), $(inputs.model.path), $(inputs.results_name)] 