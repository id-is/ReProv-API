class: Workflow
cwlVersion: v1.0

requirements:
  DockerRequirement:
    dockerPull:
      antganios/mnist-python-env:latest

inputs:
  - id: input_file
    type: File
    valueFromEntity: "{{5}}"
  - id: plot_name
    type: string
    default: "plot.png"

outputs:
  - id: plot_file
    type: File
    outputSource: plot/plot_file

steps:
  plot:
    in:
      input_file: input_file
      plot_name: plot_name
    out: [plot_file]
    run:
      class: CommandLineTool
      inputs:
        input_file: File
        plot_name: string
      outputs:
        - id: plot_file
          type: File
          outputBinding:
            glob: $(inputs.plot_name) 
      baseCommand: python
      arguments: ["/app/plot.py", $(inputs.input_file.path),$(inputs.plot_name)] 
 