import jwt
import requests

from time import time
from uuid import uuid4
from fastapi import APIRouter, Request, status, Form
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException
from fastapi.templating import Jinja2Templates

router = APIRouter(
    prefix="/chats",
    responses={'404': {"description": "Unknown endpoint"}},
)

conversation_templates = Jinja2Templates(directory="chat_client/templates/conversation")


@router.get("/new", response_class=HTMLResponse)
async def create_chat(request: Request):
    return conversation_templates.TemplateResponse("new_conversation.html", {"request": request})


@router.post("/new", response_class=HTMLResponse)
async def create_chat(request: Request,
                      conversation_name: str = Form(...),
                      conversation_id: str = Form(None),
                      is_private: bool = Form(False)):
    alert = None

    new_conversation = dict(_id=conversation_id or uuid4().hex,
                            conversation_name=conversation_name,
                            is_private=is_private,
                            created_on=int(time()))

    post_response = requests.post(f'http://127.0.0.1:8000/chat_api/new', json=new_conversation)

    if post_response.status_code != 200:
        pass

    alert = post_response.json()['success']

    return conversation_templates.TemplateResponse("new_conversation.html", {"request": request, "alert": alert})


@router.get("/{cid}", response_class=HTMLResponse)
async def get_chat(request: Request, cid: str):
    get_response = requests.get(f'http://127.0.0.1:8000/chat_api/get/{cid}')
    if get_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"{get_response.json()['detail']} "
        )
    else:
        conversation_data = get_response.json()
    conversation_data['current_user'].pop('password')
    return conversation_templates.TemplateResponse("get_conversation.html",
                                                   {"request": request,
                                                    "current_user": conversation_data['current_user'],
                                                    "conversation": conversation_data['conversation_data']})
