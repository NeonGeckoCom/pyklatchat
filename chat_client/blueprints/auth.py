import jwt
import requests

from time import time
from uuid import uuid4
from fastapi import APIRouter, Request, status, Form, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder
from neon_utils import LOG

router = APIRouter(
    prefix="/auth",
    responses={'404': {"description": "Unknown endpoint"}},
)


@router.post("/login", response_class=JSONResponse)
async def login(username: str = Form(...),
                password: str = Form(...)):

    data = dict(username=username,
                password=password)

    post_response = requests.post(f'http://127.0.0.1:8000/auth/login', data=data)

    json_data = post_response.json()

    response = JSONResponse(content=json_data, status_code=post_response.status_code)

    if post_response.status_code == 200:

        for cookie in post_response.cookies:

            response.delete_cookie('session')

            response.set_cookie(key=cookie.name, value=cookie.value, httponly=True)

        LOG.info(f'{username}: {json_data}')

    return response


@router.post("/signup", response_class=JSONResponse)
async def signup(nickname: str = Form(...),
                 first_name: str = Form(...),
                 last_name: str = Form(...),
                 password: str = Form(...)):

    data = dict(nickname=nickname,
                first_name=first_name,
                last_name=last_name,
                password=password)

    post_response = requests.post(f'http://127.0.0.1:8000/auth/signup', data=data)

    json_data = post_response.json()

    response = JSONResponse(content=json_data, status_code=post_response.status_code)

    if post_response.status_code == 200:

        response.delete_cookie('session')

        for cookie in post_response.cookies:
            response.set_cookie(key=cookie.name, value=cookie.value, httponly=True)

    LOG.info(f'{nickname}: {json_data}')

    return response


@router.get("/logout", response_class=JSONResponse)
async def logout():

    logout_response = requests.get(f'http://127.0.0.1:8000/auth/logout')

    json_data = logout_response.json()

    response = JSONResponse(content=json_data, status_code=logout_response.status_code)

    if logout_response.status_code == 200:

        response.delete_cookie('session')

        for cookie in logout_response.cookies:
            response.set_cookie(key=cookie.name, value=cookie.value, httponly=True)

    LOG.info(f'{json_data}')

    return response
