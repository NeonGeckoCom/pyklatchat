from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from chat_server.server_utils.auth import login_required
from utils.database_utils.mongo_utils import MongoFilter
from utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI

router = APIRouter(
    prefix="/personas",
    responses={"404": {"description": "Unknown endpoint"}},
)


@router.get("/list")
@login_required
async def list_personas(request: Request, llm: str = None, user_id: str = None):
    """Lists personas config matching query params"""
    filters = []
    if llm:
        filters.append(MongoFilter(key="llm", value=llm))
    if user_id:
        filters.append(MongoFilter(key="user_id", value=user_id))
    items = MongoDocumentsAPI.PERSONAS.list_items(
        filters=filters, result_as_cursor=False
    )
    return JSONResponse(content={"items": items})
