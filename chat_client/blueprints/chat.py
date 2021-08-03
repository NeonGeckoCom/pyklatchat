import jwt

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException
from fastapi.templating import Jinja2Templates

router = APIRouter(
    prefix="/chats",
    responses={'404': {"description": "Unknown endpoint"}},
)

chat_templates = Jinja2Templates(directory="chat_client/templates/chat")


@router.get("/new", response_class=HTMLResponse)
async def read_item(request: Request):
    return chat_templates.TemplateResponse("new_chat.html", {"request": request})


@router.get("/{chat_id}", response_class=HTMLResponse)
async def read_item(request: Request, chat_id: str):
    return chat_templates.TemplateResponse("item.html", {"request": request, "chat_id": chat_id})
