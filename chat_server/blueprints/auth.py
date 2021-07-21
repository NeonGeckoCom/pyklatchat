from fastapi import APIRouter

router = APIRouter(
    prefix="/auth",
    responses={404: {"description": "Unknown authorization endpoint"}},
)
