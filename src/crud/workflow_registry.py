from models.response import Response
from models.user import User
from fastapi import APIRouter, UploadFile, File, Depends
from schema.workflow_registry import WorkflowRegistry, WorkflowRegistryModel
from schema.init_db import session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from ruamel.yaml import YAML
from authentication.auth import authenticate_user

router = APIRouter()


@router.get(
    "/",
    description="List all workflows in the registry that belong to the same group as the authenticated user."
)
async def list_workflows(
    user: User = Depends(authenticate_user)
):
    yaml = YAML(typ='safe', pure=True)
    try:
        workflows = session.query(WorkflowRegistry).filter(
            WorkflowRegistry.group == user.group
        ).all()
    except SQLAlchemyError as e:
        session.rollback()
        return Response(
            success=False,
            message=f"Database error: {str(e)}",
            error_code=500,
            data={}
        )

    data = [
        {
            'group': user.group,
            'username': user.username,
            'registry_id': w.id,
            'name': w.name,
            'version': w.version,
            'spec_file_content': yaml.load(w.spec_file_content),
            'input_file_content': w.input_file_content,
        } for w in workflows
    ]
    return Response(
        success=True,
        message='Workflows successfully retrieved',
        data=data
    )


@router.get(
    "/{registry_id}",
    description="Get details of a specific workflow in the registry by its ID.",
)
async def get_workflow_details(
    registry_id: int,
    user: User = Depends(authenticate_user)
):
    yaml = YAML(typ='safe', pure=True)
    try:
        workflow = session.query(WorkflowRegistry).filter(
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

    if workflow is None:
        return Response(
            success=False,
            message="Invalid registry_id",
            error_code=404,
            data={}
        )
    data = {
        'group': user.group,
        'username': user.username,
        'registry_id': workflow.id,
        'name': workflow.name,
        'version': workflow.version,
        'spec_file_content': yaml.load(workflow.spec_file_content),
        'input_file_content': workflow.input_file_content,
    }
    return Response(
        success=True,
        message="Workflow was successfully retrieved",
        data=data
    )


@router.post(
    "/register/",
    description="Register a new workflow in the registry, providing metadata and configuration details for execution",

)
async def register_workflow(
    workflow: WorkflowRegistryModel = Depends(),
    spec_file: UploadFile = File(...),
    input_file: UploadFile = File(None),
    user: User = Depends(authenticate_user)
):
    spec_file_content = spec_file.file.read()
    input_file_content = input_file.file.read() if input_file else None

    workflow = WorkflowRegistry(
        name=workflow.name,
        version=workflow.version,
        spec_file_content=spec_file_content,
        input_file_content=input_file_content,
        username=user.username,
        group=user.group
    )
    try:
        session.add(workflow)
        session.commit()
        session.refresh(workflow)
    except IntegrityError:
        session.rollback()
        return Response(
            success=False,
            message="Integrity error. Duplicate name and version combination.",
            error_code=400,
            data={}
        )
    except SQLAlchemyError as e:
        session.rollback()
        return Response(
            success=False,
            message=f"Database error: {str(e)}",
            error_code=500,
            data={}
        )

    data = {
        'username': user.username,
        'group': user.group,
        'registry_id': workflow.id,
        'name': workflow.name,
        'version': workflow.version
    }
    return Response(
        success=True,
        message="New Workflow was successfully registered",
        data=data
    )


@router.put(
    "/update/{registry_id}",
    description="Modify an existing workflow's metadata, configuration, or steps to adapt to changing requirements.",
)
async def update_workflow(
    registry_id: int,
    name: str = None,
    version: str = None,
    spec_file: UploadFile = File(None),
    input_file: UploadFile = File(None),
    user: User = Depends(authenticate_user)
):
    try:
        workflow = session.query(WorkflowRegistry).filter(
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

    if workflow is None:
        return Response(
            success=False,
            message="Invalid registry_id",
            error_code=404,
            data={}
        )

    fields_to_update = {
        k: v for k, v in {
            'name': name,
            'version': version,
            'spec_file_content': spec_file.file.read() if spec_file else None,
            'input_file_content': input_file.file.read() if input_file else None
        }.items() if v is not None}

    try:
        wf_updated = session.query(WorkflowRegistry).filter(
            WorkflowRegistry.id == registry_id,
            WorkflowRegistry.group == user.group
        ).update(fields_to_update)
    except SQLAlchemyError as e:
        session.rollback()
        return Response(
            success=False,
            message=f"Database error: {str(e)}",
            error_code=500,
            data={}
        )

    if wf_updated == 0:
        return Response(
            success=True,
            message="No workflows were updated",
            data={}
        )

    session.commit()
    data = {
        'registry_id': registry_id
    }
    return Response(
        success=True,
        message="Workflow was succesfully updated",
        data=data
    )


@router.delete(
    "/delete/{registry_id}",
    description="Remove a workflow from the registry, making it unavailable for execution.",
)
async def delete_workflow(
    registry_id: int,
    user: User = Depends(authenticate_user)
):
    try:
        workflow = session.query(WorkflowRegistry).filter(
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

    if workflow is None:
        return Response(
            success=False,
            message="Invalid registry_id",
            error_code=404,
            data={}
        )

    try:
        session.delete(workflow)
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        return Response(
            success=False,
            message=f"Database error: {str(e)}",
            error_code=500,
            data={}
        )

    data = {
        'registry_id': registry_id
    }
    return Response(
        success=True,
        message="Workflow has been deleted",
        data=data
    )
