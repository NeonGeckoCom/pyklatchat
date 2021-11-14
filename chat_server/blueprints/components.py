from fastapi import APIRouter
from starlette.requests import Request
from starlette.templating import Jinja2Templates

router = APIRouter(
    prefix="/components",
    responses={'404': {"description": "Unknown endpoint"}},
)

component_templates = Jinja2Templates(directory="chat_server/templates")


@router.get('/{template_name}')
async def chats(request: Request, template_name: str):
    """
        Renders chats page HTML as a response related to the input request
        :returns chats conversation response
    """

    return component_templates.TemplateResponse(f"components/{template_name}.html", {"request": request})
