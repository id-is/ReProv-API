from io import BytesIO
import requests
from ruamel.yaml import YAML

yaml = YAML(typ='safe', pure=True)


def add_resource_monitoring(spec_file):
    """Wrap each step's command with Python resource monitoring.

    For each step, replaces the original command with a Python wrapper that:
    1. Runs the original command via subprocess
    2. Captures peak memory, CPU time, disk I/O via getrusage
    3. Prints metrics as a tagged JSON line to stderr (parsed from REANA logs)
    """
    data = yaml.load(spec_file)

    for step_name in list(data['steps']):
        run = data['steps'][step_name]['run']
        original_base = run['baseCommand']
        original_args = run.get('arguments', [])

        # Reconstruct original command parts as a flat list
        if isinstance(original_base, list):
            cmd_parts = list(original_base)
        else:
            cmd_parts = [original_base]
        cmd_parts.extend(original_args)

        # Build wrapper: python -c <script> <original_cmd_parts...>
        # Prints metrics to stderr with a known prefix so we can parse from logs
        wrapper_script = (
            "import resource,subprocess,json,time,sys; "
            "start=time.time(); "
            "r=subprocess.run(sys.argv[1:]); "
            "u=resource.getrusage(resource.RUSAGE_CHILDREN); "
            "sys.stderr.write('REPROV_METRICS:'+json.dumps({"
            "'wall_time':time.time()-start,"
            "'user_cpu':u.ru_utime,"
            "'sys_cpu':u.ru_stime,"
            "'max_rss_kb':u.ru_maxrss,"
            "'io_in':u.ru_inblock,"
            "'io_out':u.ru_oublock,"
            "'exit_code':r.returncode"
            "})+'\\n'); "
            "sys.exit(r.returncode)"
        )

        run['baseCommand'] = 'python'
        run['arguments'] = ['-c', wrapper_script] + cmd_parts

    with BytesIO() as output_yaml:
        yaml.dump(data, output_yaml)
        return output_yaml.getvalue()


def add_mapping_step(spec_file):
    data = yaml.load(spec_file)

    steps_file_outputs = {}
    for s in data['steps']:
        file_ouputs = {}
        outputs = data['steps'][s]['run']['outputs']
        for o in outputs:
            if o['type'] == 'File':
                file_ouputs[o['id']] = o['outputBinding']['glob']

        steps_file_outputs.update(file_ouputs)

    # Build map step inputs: string params for the echo + File dependencies
    # to force CWL to run the map step AFTER all real steps complete
    map_step_in = {}
    map_step_run_inputs = {}

    # Track which output IDs have dynamic (CWL expression) vs static globs
    # Dynamic: $(inputs.model_name) → needs a string input to resolve the filename
    # Static: validation_report.txt → literal filename, no input needed
    output_to_value = {}  # output_id → either "$(inputs.X)" or literal string

    for s in steps_file_outputs:
        glob = steps_file_outputs[s]
        if '$(inputs.' in glob:
            # Dynamic glob — extract the input name and pass it through
            input_name = glob.split('.')[-1].rstrip(')')
            map_step_in[input_name] = input_name
            map_step_run_inputs[input_name] = 'string'
            output_to_value[s] = f"$(inputs.{input_name})"
        else:
            # Static glob — use the literal filename directly
            output_to_value[s] = glob

    # Add File inputs from each step's outputs to create a data dependency
    # This ensures CWL won't schedule map until all steps have completed
    dep_counter = 0
    for step_name in data['steps']:
        step_outputs = data['steps'][step_name]['run']['outputs']
        for o in step_outputs:
            if o['type'] == 'File':
                dep_key = f"_dep_{dep_counter}"
                map_step_in[dep_key] = f"{step_name}/{o['id']}"
                map_step_run_inputs[dep_key] = 'File'
                dep_counter += 1

    map_step_out = ['mapping']

    map_step = {}
    map_step['in'] = map_step_in
    map_step['out'] = map_step_out
    map_step['run'] = {}
    map_step['run']['inputs'] = map_step_run_inputs
    map_step['run']['outputs'] = [
        {
            'id': 'mapping', 'outputBinding': {'glob': 'map.txt'},
            'type': 'File'
        }
    ]
    map_step['run']['class'] = 'CommandLineTool'
    map_step['run']['baseCommand'] = 'sh'

    args = ''
    for output_id, value in output_to_value.items():
        args += f"\n        echo {output_id},{value} >> map.txt\n        "

    map_step['run']['arguments'] = ["-c"] + [args]
    data['steps']['map'] = map_step

    data['outputs'] += [
        {
            'id': 'mapping',
            'outputSource': 'map/mapping',
            'type': 'File',
        }
    ]
    if 'requirements' not in data.keys():
        data['requirements'] = {}
    data['requirements']['InlineJavascriptRequirement'] = {}

    with BytesIO() as output_yaml:
        yaml.dump(data, output_yaml)
        return output_yaml.getvalue()


# function that replaces placeholders in the specification file.
# returns the new specification file and the entities that need to be retrieved
def replace_placeholders(spec_file):
    entities = []
    spec_file_yaml = yaml.load(spec_file)
    for i in spec_file_yaml['inputs']:
        if 'valueFromPlatform' in i.keys():

            dataset_url = i['valueFromPlatform'].strip('{}')
            url = f"{dataset_url}?schema=aiod"
            headers = {'accept': 'application/json'}
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return None, None

            data = response.json()
            entities.append(
                {
                    'id': i['id'],
                    'type': 'aiod-platform',
                    'data': data
                }
            )
            del i['valueFromPlatform']  # delete it from cwl

            for s in spec_file_yaml['steps']:
                spec_file_yaml['steps'][s]['requirements'] = {}
                spec_file_yaml['steps'][s]['requirements'] = {
                    "InitialWorkDirRequirement": {
                        "listing": []
                    }
                }
                if i['id'] in spec_file_yaml['steps'][s]['in']:
                    spec_file_yaml['steps'][s]['requirements']['InitialWorkDirRequirement']['listing'].append(f"$(inputs.{i['id']})")

    with BytesIO() as output_yaml:
        yaml.dump(spec_file_yaml, output_yaml)
        return output_yaml.getvalue(), entities