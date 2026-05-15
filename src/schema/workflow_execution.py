from sqlalchemy import Column, Integer, BigInteger, Float, String, Text, DateTime, ForeignKey
from datetime import datetime
from .init_db import Base


class WorkflowExecution(Base):
    __tablename__ = "workflow_execution"

    id = Column(Integer, primary_key=True, index=True)
    start_time = Column(DateTime, default=datetime.utcnow,)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(255), default="queued")
    reana_id = Column(String(255), nullable=True)
    reana_name = Column(String(255), nullable=True)
    reana_run_number = Column(String(255), nullable=True)

    registry_id = Column(Integer, ForeignKey("workflow_registry.id"))

    # Add username/group here as well because user A from group G can register a workflow but user B from group G can execute it
    username = Column(String(255), nullable=False)
    group = Column(String(255), nullable=False)


class WorkflowExecutionStep(Base):
    __tablename__ = "workflow_execution_step"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(255), default="running")
    start_time = Column(DateTime, default=datetime.utcnow,)
    end_time = Column(DateTime, nullable=True)

    # Crash detection fields
    exit_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    command = Column(Text, nullable=True)

    workflow_execution_id = Column(Integer, ForeignKey("workflow_execution.id"))


class StepResourceUsage(Base):
    __tablename__ = "step_resource_usage"

    id = Column(Integer, primary_key=True, index=True)
    step_id = Column(Integer, ForeignKey("workflow_execution_step.id"), nullable=False)

    cpu_time_seconds = Column(Float, nullable=True)
    memory_peak_mb = Column(Float, nullable=True)
    disk_read_bytes = Column(BigInteger, nullable=True)
    disk_write_bytes = Column(BigInteger, nullable=True)
    backend_job_id = Column(String(255), nullable=True)


class ExecutionEnvironment(Base):
    __tablename__ = "execution_environment"

    id = Column(Integer, primary_key=True, index=True)
    workflow_execution_id = Column(Integer, ForeignKey("workflow_execution.id"), nullable=False)

    # REANA instance
    reana_server_url = Column(String(512), nullable=True)
    reana_workflow_url = Column(String(512), nullable=True)

    # Cluster info (from REANA /info endpoint)
    compute_backend = Column(String(255), nullable=True)
    kubernetes_memory_limit = Column(String(255), nullable=True)
    kubernetes_max_concurrent_jobs = Column(Integer, nullable=True)

    # Container image (from CWL spec)
    docker_image = Column(String(512), nullable=True)
