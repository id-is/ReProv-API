import asyncio
import json
import os
import re
from fastapi.responses import FileResponse
from fastapi import APIRouter, BackgroundTasks, Depends
from starlette.background import BackgroundTask
from schema.workflow_execution import WorkflowExecution, WorkflowExecutionStep, StepResourceUsage, ExecutionEnvironment
from schema.workflow_registry import WorkflowRegistry
from schema.init_db import session
from authentication.auth import authenticate_user
from models.user import User
from utils.cwl import add_resource_monitoring, add_mapping_step, replace_placeholders
from reana_client.api import client
import tempfile
from datetime import datetime
import urllib3
from models.response import Response
from sqlalchemy.exc import SQLAlchemyError

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

router = APIRouter()


@router.get(
    "/",
    description="List all workflows that have been executed",
)
async def list_executed_workflows(
    user: User = Depends(authenticate_user)
):
    try:
        workflow_executions = session.query(WorkflowExecution).filter(
            WorkflowExecution.group == user.group
        ).all()
    except SQLAlchemyError as e:
        session.rollback()
        return Response(
            success=False,
            message=f"Database error: {str(e)}",
            error_code=500,
            data={}
        )

    data = {}
    for workflow_execution in workflow_executions:
        workflow_data = {
            'username': user.username,
            'group': user.group,
            'execution_id': workflow_execution.id,
            'start_time': workflow_execution.start_time,
            'end_time': workflow_execution.end_time,
            'status': workflow_execution.status,
            'reana_name': workflow_execution.reana_name,
            'reana_run_number': workflow_execution.reana_run_number,
            'registry_id': workflow_execution.registry_id,
            'steps': []
        }
        try:
            workflow_execution_steps = session.query(WorkflowExecutionStep).filter(
                WorkflowExecutionStep.workflow_execution_id == workflow_execution.id
            ).all()
        except SQLAlchemyError as e:
            session.rollback()
            return Response(
                success=False,
                message=f"Database error: {str(e)}",
                error_code=500,
                data={}
            )
        for step in workflow_execution_steps:
            if step.name == 'map':
                continue
            step_data = {
                'step_id': step.id,
                'name': step.name,
                'status': step.status,
                'start_time': step.start_time,
                'end_time': step.end_time,
                'exit_code': step.exit_code,
                'command': step.command,
            }
            if step.status == 'failed':
                step_data['error_message'] = step.error_message
            workflow_data['steps'].append(step_data)
        name = f"{workflow_execution.reana_name}:{workflow_execution.reana_run_number}"
        data[name] = workflow_data
    return Response(
        success=True,
        message='Workflow executions retrieved successfully',
        data=data
    )


@router.get(
    "/{execution_id}",
    description="Get details of a specific workflow that was executed by its execution ID.",
)
async def get_workflow_execution_by_id(
    execution_id: int,
    user: User = Depends(authenticate_user)
):
    try:
        workflow_execution = session.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id,
            WorkflowExecution.group == user.group
        ).first()
    except SQLAlchemyError as e:
        session.rollback()
        return Response(
            success=False,
            message=f"Database error: {str(e)}",
            error_code=500,
            data={}
        )
    if workflow_execution is None:
        return Response(
            success=False,
            message="Invalid execution_id",
            error_code=404,
            data={}
        )
    data = {
        'username': user.username,
        'group': user.group,
        'execution_id': workflow_execution.id,
        'start_time': workflow_execution.start_time,
        'end_time': workflow_execution.end_time,
        'status': workflow_execution.status,
        'reana_name': workflow_execution.reana_name,
        'reana_run_number': workflow_execution.reana_run_number,
        'registry_id': workflow_execution.registry_id,
        'steps': []
    }
    try:
        workflow_execution_steps = session.query(WorkflowExecutionStep).filter(
            WorkflowExecutionStep.workflow_execution_id == workflow_execution.id
        ).all()
    except SQLAlchemyError as e:
        session.rollback()
        return Response(
            success=False,
            message=f"Database error: {str(e)}",
            error_code=500,
            data={}
        )
    for step in workflow_execution_steps:
        # Skip internal map step — it's infrastructure, not a user step
        if step.name == 'map':
            continue

        # Calculate duration in seconds
        duration = None
        if step.start_time and step.end_time:
            duration = round((step.end_time - step.start_time).total_seconds(), 1)

        step_data = {
            'step_id': step.id,
            'name': step.name,
            'status': step.status,
            'start_time': step.start_time,
            'end_time': step.end_time,
            'duration_seconds': duration,
            'exit_code': step.exit_code,
            'command': step.command,
        }
        if step.status == 'failed':
            step_data['error_message'] = step.error_message

        # Include resource usage if available
        try:
            resource_rec = session.query(StepResourceUsage).filter(
                StepResourceUsage.step_id == step.id
            ).first()
        except SQLAlchemyError:
            session.rollback()
            resource_rec = None
        if resource_rec:
            step_data['resource_usage'] = {
                'cpu_time_seconds': resource_rec.cpu_time_seconds,
                'memory_peak_mb': round(resource_rec.memory_peak_mb, 2) if resource_rec.memory_peak_mb else None,
                'disk_read_bytes': resource_rec.disk_read_bytes,
                'disk_write_bytes': resource_rec.disk_write_bytes,
                'backend_job_id': resource_rec.backend_job_id,
            }
        data['steps'].append(step_data)

    # Include execution environment
    try:
        env = session.query(ExecutionEnvironment).filter(
            ExecutionEnvironment.workflow_execution_id == workflow_execution.id
        ).first()
    except SQLAlchemyError:
        session.rollback()
        env = None
    if env:
        data['environment'] = {
            'reana_server_url': env.reana_server_url,
            'reana_workflow_url': env.reana_workflow_url,
            'compute_backend': env.compute_backend,
            'kubernetes_memory_limit': env.kubernetes_memory_limit,
            'docker_image': env.docker_image,
        }

    return {
        "success": True,
        "message": "Workflow execution successfully retrieved",
        "data": data
    }


@router.get(
    "/{execution_id}/logs",
    description="Get logs for each step of a specific workflow execution",
)
async def get_execution_logs(
    execution_id: int,
    user: User = Depends(authenticate_user)
):
    try:
        workflow_execution = session.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id,
            WorkflowExecution.group == user.group
        ).first()
    except SQLAlchemyError as e:
        session.rollback()
        return Response(
            success=False,
            message=f"Database error: {str(e)}",
            error_code=500,
            data={}
        )
    if workflow_execution is None:
        return Response(
            success=False,
            message="Invalid execution_id",
            error_code=404,
            data={}
        )

    # Fetch live logs from REANA
    try:
        logs_response = client.get_workflow_logs(
            workflow=workflow_execution.reana_id,
            access_token=os.environ['REANA_ACCESS_TOKEN']
        )
        logs_data = json.loads(logs_response.get('logs', '{}'))
        job_logs = logs_data.get('job_logs', {})
    except Exception as e:
        return Response(
            success=False,
            message=f"Failed to fetch logs from REANA: {str(e)}",
            error_code=503,
            data={}
        )

    # Also get stored step info from DB
    try:
        steps = session.query(WorkflowExecutionStep).filter(
            WorkflowExecutionStep.workflow_execution_id == workflow_execution.id
        ).all()
    except SQLAlchemyError as e:
        session.rollback()
        return Response(
            success=False,
            message=f"Database error: {str(e)}",
            error_code=500,
            data={}
        )

    step_names = {s.name for s in steps}
    data = {}
    for job_id, job_info in job_logs.items():
        if not isinstance(job_info, dict):
            continue
        job_name = job_info.get('job_name', job_id)
        step_entry = {
            'backend_job_id': job_id,
            'status': job_info.get('status', ''),
            'logs': job_info.get('logs', ''),
            'compute_backend': job_info.get('compute_backend'),
            'docker_img': job_info.get('docker_img'),
            'started_at': job_info.get('started_at'),
            'finished_at': job_info.get('finished_at'),
        }
        # Enrich with DB data if available
        matching_step = next((s for s in steps if s.name == job_name), None)
        if matching_step:
            step_entry['exit_code'] = matching_step.exit_code
            step_entry['error_message'] = matching_step.error_message
            step_entry['command'] = matching_step.command
        data[job_name] = step_entry

    return Response(
        success=True,
        message="Logs retrieved successfully",
        data=data
    )


@router.post(
    "/execute/{registry_id}",
    description="Execute workflow by invoking REANA system"
)
async def execute_workflow(
    registry_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(authenticate_user)
):
    try:
        workflow_registry = session.query(WorkflowRegistry).filter(
            WorkflowRegistry.id == registry_id,
            WorkflowRegistry.group == user.group
        ).first()
    except SQLAlchemyError as e:
        session.rollback()
        return Response(
            success=False,
            message=f"Database error: {str(e)}",
            error_code=500,
            data={}
        )

    if workflow_registry is None:
        return Response(
            success=False,
            message="Invalid registry_id",
            error_code=404,
            data={}
        )
    with tempfile.NamedTemporaryFile(dir=os.getcwd(), suffix='.cwl', delete=False) as spec_temp_file:
        spec_file_with_monitoring = add_resource_monitoring(workflow_registry.spec_file_content.encode('utf-8'))
        spec_file_with_mapping_step = add_mapping_step(spec_file_with_monitoring)
        spec_file_without_placeholders, needed_entities = replace_placeholders(spec_file_with_mapping_step)
        if spec_file_without_placeholders is None and needed_entities is None:
            return Response(
                success=False,
                message="Invalid entity id in placeholder",
                error_code=404,
                data={}
            )

        spec_temp_file.write(spec_file_without_placeholders)

    inputs = {"parameters": {}}
    if workflow_registry.input_file_content:
        with tempfile.NamedTemporaryFile(dir=os.getcwd(), suffix='.yaml', delete=False) as input_temp_file:
            input_temp_file.write(workflow_registry.input_file_content.encode('utf-8'))
        with open(os.path.join(os.getcwd(), input_temp_file.name)) as f:
            for line in f:
                k, v = line.strip().split(": ")
                inputs["parameters"][k] = v

    for entity in needed_entities:
        if entity['type'] == 'aiod-platform':
            content_url = entity['data']['distribution'][0]['content_url']
            path = content_url[len('file://'):]

            inputs['parameters'][entity['id']] = {
                'class': 'File',
                'path': content_url.split('/')[-1],
            }

    try:
        reana_workflow = client.create_workflow_from_json(
            name=f"{workflow_registry.name}:{workflow_registry.version}",
            access_token=os.environ['REANA_ACCESS_TOKEN'],
            workflow_file=os.path.join(os.getcwd(), spec_temp_file.name),
            parameters=inputs,
            workflow_engine='cwl'
        )
    except Exception as e:
        os.remove(os.path.join(os.getcwd(), spec_temp_file.name))
        if workflow_registry.input_file_content:
            os.remove(os.path.join(os.getcwd(), input_temp_file.name))
        return Response(
            success=False,
            message="Problem while creating REANA workflow: " + str(e),
            error_code=503,
            data={}
        )

    try:
        for entity in needed_entities:
            if entity['type'] == 'valueFromEntity':
                try:
                    prev_execution = session.query(WorkflowExecution.reana_id).filter(WorkflowExecution.id == entity['data'].workflow_execution_id).first()
                except SQLAlchemyError as e:
                    session.rollback()
                    return Response(
                        success=False,
                        message=f"Database error: {str(e)}",
                        error_code=500,
                        data={}
                    )
                file_name = entity['data'].path
                downloaded_entity = client.download_file(
                    workflow=prev_execution.reana_id,
                    file_name=file_name,
                    access_token=os.environ['REANA_ACCESS_TOKEN'],
                )

                client.upload_file(
                    workflow=reana_workflow['workflow_id'],
                    file_=downloaded_entity[0],
                    file_name=entity['data'].name,
                    access_token=os.environ['REANA_ACCESS_TOKEN']
                )
            elif entity['type'] == 'aiod-platform':
                content_url = entity['data']['distribution'][0]['content_url']
                path = content_url[len('file://'):]
                with open(path, "rb") as f:
                    file_content = f.read()
                client.upload_file(
                    workflow=reana_workflow['workflow_id'],
                    file_=file_content,
                    file_name=content_url.split('/')[-1],
                    access_token=os.environ['REANA_ACCESS_TOKEN']
                )

        workflow_run = client.start_workflow(
            workflow=reana_workflow['workflow_id'],
            access_token=os.environ['REANA_ACCESS_TOKEN'],
            parameters={}
        )
        workflow_execution = WorkflowExecution(
            username=user.username,
            group=user.group,
            registry_id=registry_id,
            reana_id=workflow_run['workflow_id'],
            reana_name=workflow_run['workflow_name'],
            reana_run_number=workflow_run['run_number'],
        )
        background_tasks.add_task(monitor_execution, workflow_execution.reana_id)
        session.add(workflow_execution)
        session.commit()
        session.refresh(workflow_execution)

        # Capture execution environment
        _capture_environment(workflow_execution, workflow_registry)
    except Exception as e:
        session.rollback()
        return Response(
            success=False,
            message="Problem while starting REANA workflow: " + str(e),
            error_code=503,
            data={}
        )
    finally:
        os.remove(os.path.join(os.getcwd(), spec_temp_file.name))
        if workflow_registry.input_file_content:
            os.remove(os.path.join(os.getcwd(), input_temp_file.name))

    data = {
        "username": user.username,
        "group": user.group,
        "execution_id": workflow_execution.id,
        "name": workflow_registry.name,
        "version": workflow_registry.version,
        "reana_name": workflow_execution.reana_name,
        "reana_id": workflow_execution.reana_id,
        "run_number": workflow_execution.reana_run_number,
    }
    return Response(
        success=True,
        message="New workflow started",
        data=data
    )


def _capture_environment(workflow_execution, workflow_registry):
    """Capture execution environment info: REANA instance, cluster config, Docker image."""
    from ruamel.yaml import YAML
    from io import BytesIO

    reana_url = os.environ.get('REANA_SERVER_URL', '')
    reana_workflow_url = f"{reana_url}/api/workflows/{workflow_execution.reana_id}" if reana_url else None

    # Extract docker image from CWL spec
    docker_image = None
    try:
        yaml = YAML(typ='safe', pure=True)
        spec = yaml.load(workflow_registry.spec_file_content)
        reqs = spec.get('requirements', {})
        if 'DockerRequirement' in reqs:
            docker_image = reqs['DockerRequirement'].get('dockerPull')
    except Exception:
        pass

    # Query REANA cluster info
    compute_backend = None
    k8s_memory_limit = None
    k8s_max_jobs = None
    try:
        info = client.info(access_token=os.environ['REANA_ACCESS_TOKEN'])
        if isinstance(info, dict):
            cb = info.get('compute_backends')
            if cb:
                compute_backend = cb.get('value', str(cb))
            mem = info.get('default_kubernetes_memory_limit')
            if mem:
                k8s_memory_limit = mem.get('value', str(mem))
            jobs = info.get('maximum_kubernetes_jobs_count') or info.get('max_concurrent_batch_workflows')
            if jobs:
                k8s_max_jobs = jobs.get('value') if isinstance(jobs, dict) else jobs
    except Exception:
        pass

    env = ExecutionEnvironment(
        workflow_execution_id=workflow_execution.id,
        reana_server_url=reana_url,
        reana_workflow_url=reana_workflow_url,
        compute_backend=compute_backend,
        kubernetes_memory_limit=k8s_memory_limit,
        kubernetes_max_concurrent_jobs=k8s_max_jobs,
        docker_image=docker_image,
    )
    session.add(env)
    session.commit()


def _fetch_step_logs(reana_id, step_name):
    """Fetch and parse logs for a specific step from REANA."""
    try:
        logs_response = client.get_workflow_logs(
            workflow=reana_id,
            access_token=os.environ['REANA_ACCESS_TOKEN'],
            steps=[step_name]
        )
        logs_data = json.loads(logs_response.get('logs', '{}'))
        job_logs = logs_data.get('job_logs', {})

        for job_id, job_info in job_logs.items():
            if not isinstance(job_info, dict):
                continue
            log_content = job_info.get('logs', '')
            status = job_info.get('status', '')
            started_at = job_info.get('started_at')
            finished_at = job_info.get('finished_at')

            exit_code = _parse_exit_code(log_content, status)

            # Only store error message for failed steps
            error_message = None
            if status == 'failed':
                error_message = log_content[-5000:] if len(log_content) > 5000 else log_content

            # Compute wall-clock duration if timestamps available
            cpu_time = None
            if started_at and finished_at:
                try:
                    t_start = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    t_end = datetime.fromisoformat(finished_at.replace('Z', '+00:00'))
                    cpu_time = (t_end - t_start).total_seconds()
                except (ValueError, TypeError):
                    pass

            # Parse resource metrics from wrapper output (REPROV_METRICS:{...})
            resource_metrics = None
            metrics_match = re.search(r'REPROV_METRICS:(\{.*\})', log_content)
            if metrics_match:
                try:
                    resource_metrics = json.loads(metrics_match.group(1))
                except (json.JSONDecodeError, ValueError):
                    pass

            return {
                'exit_code': exit_code,
                'error_message': error_message,
                'log_content': log_content,
                'backend_job_id': job_id,
                'started_at': started_at,
                'finished_at': finished_at,
                'cpu_time_seconds': cpu_time,
                'resource_metrics': resource_metrics,
            }
    except Exception:
        return None
    return None


def _parse_exit_code(log_content, status):
    """Extract exit code from log content or infer from status."""
    if status == 'finished':
        return 0
    if status == 'failed':
        patterns = [
            r'exit code[:\s]+(\d+)',
            r'exited with code (\d+)',
            r'return code[:\s]+(\d+)',
            r'Exit code: (\d+)',
            r'ExitCode:\s*(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, log_content, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 1  # default non-zero for failed
    return None


def _finalize_step(reana_id, step_record, step_status):
    """Finalize a completed step: set status, fetch logs, capture resource usage."""
    step_record.end_time = datetime.utcnow()
    step_record.status = step_status

    step_logs = _fetch_step_logs(reana_id, step_record.name)
    if step_logs:
        step_record.exit_code = step_logs.get('exit_code')
        step_record.error_message = step_logs.get('error_message')

        session.add(step_record)
        session.flush()

        # Store resource usage from wrapper metrics + REANA metadata
        metrics = step_logs.get('resource_metrics') or {}
        resource_usage = StepResourceUsage(
            step_id=step_record.id,
            cpu_time_seconds=metrics.get('user_cpu', 0) + metrics.get('sys_cpu', 0) if metrics else step_logs.get('cpu_time_seconds'),
            memory_peak_mb=metrics.get('max_rss_kb', 0) / 1024.0 if metrics.get('max_rss_kb') else None,
            disk_read_bytes=metrics.get('io_in', 0) * 512 if metrics.get('io_in') is not None else None,
            disk_write_bytes=metrics.get('io_out', 0) * 512 if metrics.get('io_out') is not None else None,
            backend_job_id=step_logs.get('backend_job_id'),
        )
        session.add(resource_usage)
    else:
        session.add(step_record)

    session.commit()


def _clean_command(raw_command):
    """Extract the actual user command from REANA's verbose shell wrapper."""
    if not raw_command:
        return None

    cleaned = raw_command

    # Remove the CWL output copy at the end: '; cp -r <outdir>/* <final_outdir>'
    cp_idx = cleaned.rfind('; cp -r ')
    if cp_idx > 0:
        cleaned = cleaned[:cp_idx]

    # If our Python resource wrapper is present, extract the original command after it
    # The wrapper ends with: sys.exit(r.returncode)'"'"'  (shell-escaped closing quote)
    marker = 'sys.exit(r.returncode)'
    idx = cleaned.rfind(marker)
    if idx > 0:
        rest = cleaned[idx + len(marker):]
        # Remove shell quote escaping: '"'"' is how bash embeds ' inside '...'
        rest = rest.replace("'\"'\"'", "").strip()
        rest = rest.strip("' ")
        if rest:
            return rest

    # Fallback: extract command after last '&& cd ... && '
    parts = cleaned.split('&& ')
    if len(parts) > 1:
        return parts[-1].strip().rstrip("'")

    return raw_command


async def monitor_execution(reana_id):
    try:
        workflow_execution = session.query(WorkflowExecution).filter(WorkflowExecution.reana_id == reana_id).first()
    except SQLAlchemyError as e:
        session.rollback()
        return

    prev_step = None
    while True:
        workflow_status = client.get_workflow_status(
            workflow=reana_id,
            access_token=os.environ['REANA_ACCESS_TOKEN']
        )

        current_step = workflow_status['progress']['current_step_name']
        current_command = workflow_status['progress'].get('current_command')

        if current_step != prev_step:  # if a new step is running:
            if prev_step is not None:
                try:
                    prev_workflow_execution_step = session.query(WorkflowExecutionStep).filter(
                        WorkflowExecutionStep.workflow_execution_id == workflow_execution.id,
                        WorkflowExecutionStep.name == prev_step,
                    ).first()
                except SQLAlchemyError as e:
                    session.rollback()
                    return

                # Determine if the previous step failed (if workflow just failed, this step caused it)
                prev_step_status = 'failed' if workflow_status['status'] == 'failed' else 'finished'
                _finalize_step(reana_id, prev_workflow_execution_step, prev_step_status)

            current_workflow_execution_step = WorkflowExecutionStep(
                name=current_step,
                command=_clean_command(current_command),
                workflow_execution_id=workflow_execution.id
            )

            prev_step = current_step

            session.add(current_workflow_execution_step)
            session.commit()

        if workflow_status['status'] != workflow_execution.status:
            workflow_execution.status = workflow_status['status']
        if workflow_status['status'] == 'finished' or workflow_status['status'] == 'failed':
            break

        await asyncio.sleep(0.001)

    final_status = client.get_workflow_status(
        workflow=reana_id,
        access_token=os.environ['REANA_ACCESS_TOKEN']
    )

    try:
        last_workflow_execution_step = session.query(WorkflowExecutionStep).filter(
            WorkflowExecutionStep.workflow_execution_id == workflow_execution.id,
            WorkflowExecutionStep.name == current_step,
        ).first()
    except SQLAlchemyError as e:
        session.rollback()
        return

    if last_workflow_execution_step is not None:
        _finalize_step(reana_id, last_workflow_execution_step, final_status['status'])

    try:
        workflow_execution = session.query(WorkflowExecution).filter(WorkflowExecution.reana_id == reana_id).first()
    except SQLAlchemyError as e:
        session.rollback()
        return

    workflow_execution.end_time = datetime.utcnow()
    session.add(workflow_execution)
    session.commit()


@router.delete(
    "/delete/",
    description="Delete every workflow execution that was associated with a registry ID OR with a name provided by the execution system "
)
async def delete_workflow_execution(
    registry_id: int = None,
    reana_name: str = None,
    user: User = Depends(authenticate_user)
):
    if registry_id and reana_name:
        return Response(
            success=False,
            message="Either provide registry_id OR name but not both",
            error_code=403,
            data={}
        )

    deleted_workflows_id = []
    try:
        if registry_id:
            workflows = session.query(WorkflowExecution).filter(
                WorkflowExecution.registry_id == registry_id,
                WorkflowExecution.group == user.group
            ).all()
        else:
            workflows = session.query(WorkflowExecution).filter(
                WorkflowExecution.reana_name == reana_name,
                WorkflowExecution.group == user.group
            ).all()
    except SQLAlchemyError as e:
        session.rollback()
        return Response(
            success=False,
            message=f"Database error: {str(e)}",
            error_code=500,
            data={}
        )

    for w in workflows:
        try:
            deleted_workflows_id.append(
                client.delete_workflow(
                    workflow=w.reana_id if registry_id else reana_name,
                    access_token=os.environ['REANA_ACCESS_TOKEN'],
                    all_runs=True,
                    workspace=True
                )['workflow_id']
            )
            session.delete(w)
            session.commit()
        except Exception as e:
            session.rollback()
            return Response(
                success=False,
                message="Problem while deleting REANA workflow: " + str(e),
                error_code=503,
                data={}
            )

    if registry_id:
        message = f"Every workflow associated with registry_id:{registry_id} was successfully deleted"
    else:
        message = f"Every workflow associated with name:{reana_name} was successfully deleted"
    data = deleted_workflows_id
    return Response(
        success=True,
        message=message,
        data=data
    )


@router.get(
    "/outputs/{execution_id}",
    description="Download outputs of an executed workflow",
)
async def download_outputs(
    execution_id: int,
    user: User = Depends(authenticate_user)
):
    try:
        workflow_execution = session.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id
        ).first()
    except SQLAlchemyError as e:
        session.rollback()
        return Response(
            success=False,
            message=f"Database error: {str(e)}",
            error_code=500,
            data={}
        )

    if workflow_execution is None:
        return Response(
            success=False,
            message="Invalid execution_id",
            error_code=404,
            data={}
        )

    if workflow_execution.status != 'finished':
        return Response(
            success=False,
            message="Workflow must be finished in order to download output files",
            error_code=409,
            data={}
        )

    (output_content, file_name, is_zipped) = client.download_file(
        workflow=workflow_execution.reana_id,
        file_name='outputs',
        access_token=os.environ['REANA_ACCESS_TOKEN']
    )

    def _delete_tmp_file():
        os.unlink(temp_file.name)

    with tempfile.NamedTemporaryFile(dir=os.getcwd(), delete=False) as temp_file:
        temp_file.write(output_content)

        return FileResponse(
            temp_file.name,
            filename='outputs.zip',
            background=BackgroundTask(_delete_tmp_file),
        )


@router.get(
    "/inputs/{execution_id}",
    description="Download inputs of an executed workflow",
)
async def download_inputs(
    execution_id: int,
    user: User = Depends(authenticate_user)
):
    try:
        workflow_execution = session.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id
        ).first()
    except SQLAlchemyError as e:
        session.rollback()
        return Response(
            success=False,
            message=f"Database error: {str(e)}",
            error_code=500,
            data={}
        )

    if workflow_execution is None:
        return Response(
            success=False,
            message="Invalid execution_id",
            error_code=404,
            data={}
        )

    if workflow_execution.status != 'finished':
        return Response(
            success=False,
            message="Workflow must be finished in order to download input files",
            error_code=409,
            data={}
        )

    (input_content, file_name, _) = client.download_file(
        workflow=workflow_execution.reana_id,
        file_name='inputs.json',
        access_token=os.environ['REANA_ACCESS_TOKEN']
    )

    def _delete_tmp_file():
        os.unlink(temp_file.name)

    if input_content == b'{}':
        return Response(
            success=True,
            message="Workflow does not have any input values (default were used)",
            data={}
        )

    with tempfile.NamedTemporaryFile(dir=os.getcwd(), delete=False) as temp_file:
        temp_file.write(input_content)

        return FileResponse(
            temp_file.name,
            filename=file_name,
            background=BackgroundTask(_delete_tmp_file),
        )
