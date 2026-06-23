class: Workflow
cwlVersion: v1.0

requirements:
  DockerRequirement:
    dockerPull: antganios/era5-heatwave-env:latest
  ScatterFeatureRequirement: {}
  InlineJavascriptRequirement: {}

inputs:
  - id: dataset_dir
    type: string
    default: "/var/reana/datasets/med"
  - id: slab_pattern
    type: string
    default: "era5_????_07_08.grib"
  - id: merged_name
    type: string
    default: "med_daily_summer.nc"
  - id: labeled_name
    type: string
    default: "med_daily_labeled.nc"
  - id: model_name
    type: string
    default: "heatwave_gbm.joblib"
  - id: results_name
    type: string
    default: "results.txt"

outputs:
  - id: results
    type: File
    outputSource: evaluate/results
  - id: model
    type: File
    outputSource: train/model
  - id: labeled
    type: File
    outputSource: label/labeled

steps:
  stage_slabs:
    in:
      dataset_dir: dataset_dir
      slab_pattern: slab_pattern
    out: [slab_paths]
    run:
      class: CommandLineTool
      inputs:
        dataset_dir: string
        slab_pattern: string
      outputs:
        - id: slab_paths
          type: string[]
          outputBinding:
            glob: "slab_list.txt"
            loadContents: true
            outputEval: $(self[0].contents.trim().split("\n"))
      baseCommand: bash
      arguments:
        - "-c"
        - "ls -1 $(inputs.dataset_dir)/$(inputs.slab_pattern) > slab_list.txt && cat slab_list.txt"

  preprocess:
    scatter: slab_path
    in:
      slab_path: stage_slabs/slab_paths
    out: [daily]
    run:
      class: CommandLineTool
      inputs:
        slab_path: string
      outputs:
        - id: daily
          type: File
          outputBinding:
            glob: $(inputs.slab_path.split('/').pop().replace('.grib', '.daily.nc'))
      baseCommand: python
      arguments:
        - /app/preprocess.py
        - $(inputs.slab_path)
        - $(inputs.slab_path.split('/').pop().replace('.grib', '.daily.nc'))

  merge:
    in:
      merged_name: merged_name
      daily_slabs: preprocess/daily
    out: [merged]
    run:
      class: CommandLineTool
      inputs:
        merged_name:
          type: string
          inputBinding:
            position: 1
        daily_slabs:
          type: File[]
          inputBinding:
            position: 2
      outputs:
        - id: merged
          type: File
          outputBinding:
            glob: $(inputs.merged_name)
      baseCommand: [python, /app/merge.py]

  label:
    in:
      merged: merge/merged
      labeled_name: labeled_name
    out: [labeled]
    run:
      class: CommandLineTool
      inputs:
        merged: File
        labeled_name: string
      outputs:
        - id: labeled
          type: File
          outputBinding:
            glob: $(inputs.labeled_name)
      baseCommand: python
      arguments:
        - /app/label.py
        - $(inputs.merged.path)
        - $(inputs.labeled_name)

  train:
    in:
      labeled: label/labeled
      model_name: model_name
    out: [model]
    run:
      class: CommandLineTool
      inputs:
        labeled: File
        model_name: string
      outputs:
        - id: model
          type: File
          outputBinding:
            glob: $(inputs.model_name)
      baseCommand: python
      arguments:
        - /app/train.py
        - $(inputs.labeled.path)
        - $(inputs.model_name)

  evaluate:
    in:
      labeled: label/labeled
      model: train/model
      results_name: results_name
    out: [results]
    run:
      class: CommandLineTool
      inputs:
        labeled: File
        model: File
        results_name: string
      outputs:
        - id: results
          type: File
          outputBinding:
            glob: $(inputs.results_name)
      baseCommand: python
      arguments:
        - /app/evaluate.py
        - $(inputs.labeled.path)
        - $(inputs.model.path)
        - $(inputs.results_name)
