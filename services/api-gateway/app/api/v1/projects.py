from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_projects():
    ...


@router.post("")
async def create_project():
    ...


@router.get("/{project_id}")
async def get_project(project_id: str):
    ...


@router.post("/{project_id}/repositories")
async def attach_repository(project_id: str):
    ...


@router.post("/{project_id}/sync")
async def sync_project(project_id: str):
    ...
