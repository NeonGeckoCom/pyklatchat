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
        alert = post_response.text
        print(alert)

    print(post_response)

    return conversation_templates.TemplateResponse("new_conversation.html", {"request": request, "alert": alert})


@router.get("/{cid}", response_class=HTMLResponse)
async def get_chat(request: Request, cid: str):
    conversation_data = db_connector.exec_query(query={'command': 'find_one',
                                                       'document': 'chats',
                                                       'data': {'_id': cid}})
    if not conversation_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Unable to get a chat with id: {cid} "
        )
    return conversation_templates.TemplateResponse("get_conversation.html", {"request": request,
                                                                             "conversation": conversation_data})
