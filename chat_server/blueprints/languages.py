from fastapi import APIRouter, Request, Response
from starlette.responses import JSONResponse

from chat_server.constants.languages import LanguageSettings
from chat_server.server_utils.auth import get_current_user
from chat_server.server_utils.db_utils import DbUtils
from utils.http_utils import respond

router = APIRouter(
    prefix="/language_api",
    responses={'404': {"description": "Unknown endpoint"}},
)


@router.get("/settings")
async def supported_languages(request: Request, response: Response):
    """
        Stores received files in filesystem

        :param request: incoming FastAPI Request Object
        :param response: outgoing FastAPI Response Object

        :returns JSON-formatted response from server
    """
    return JSONResponse(content={'supported_languages': LanguageSettings.list()})
