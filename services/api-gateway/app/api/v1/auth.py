from fastapi import APIRouter

router = APIRouter()


@router.post("/exchange")
async def exchange_token():
    """Exchange a Clerk session token for a backend session."""
    ...


@router.get("/me")
async def get_current_user():
    ...
