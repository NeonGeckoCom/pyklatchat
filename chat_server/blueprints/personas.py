from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from chat_server.server_utils.auth import login_required
from chat_server.server_utils.models.endpoints.persona import AddPersonaModel
from utils.database_utils.mongo_utils import MongoFilter, MongoLogicalOperators
from utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI
from utils.http_utils import respond, response_ok

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
        filters.append(
            MongoFilter(
                key="supported_llms",
                value=llm,
                logical_operator=MongoLogicalOperators.ANY,
            )
        )
    if user_id:
        filters.append(MongoFilter(key="user_id", value=user_id))
    items = MongoDocumentsAPI.PERSONAS.list_items(
        filters=filters, result_as_cursor=False
    )
    return JSONResponse(content={"items": items})


@router.put("/add")
@login_required
async def add_persona(request: Request, model: AddPersonaModel):
    """Adds new persona"""
    filters = [
        MongoFilter(key=key, value=getattr(model, key))
        for key in (
            "user_id",
            "persona_name",
        )
        if getattr(model, key)
    ]
    existing_model = MongoDocumentsAPI.PERSONAS.get_item(filters=filters)
    if existing_model:
        return respond("Requested persona name already exists", status_code=400)
    MongoDocumentsAPI.PERSONAS.add_item(data=model.model_dump())
    return response_ok
