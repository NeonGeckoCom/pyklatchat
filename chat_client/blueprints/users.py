# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2022 Neongecko.com Inc.
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# BSD-3 License
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import requests

from utils.logging_utils import LOG

from typing import Optional
from fastapi import Response, Request, status, APIRouter, Form, UploadFile, File
from fastapi.exceptions import HTTPException

from chat_client.client_config import app_config
from chat_client.client_utils.api_utils import call_server

router = APIRouter(
    prefix="/users",
    responses={'404': {"description": "Unknown user"}},
)


@router.get("/")
async def get_user(response: Response, request: Request, user_id: Optional[str] = None):
    """
        Forwards getting user by id to the server API and handles the response cookies

        :param request: input request object
        :param response: output response object with applied cookies from server response
        :param user_id: requested user id

        :returns JSON-formatted response from server
    """
    user_id = user_id or ''
    url = f'{app_config["SERVER_URL"]}/users_api?user_id={user_id}'
    LOG.info(f'Getting user from url = {url}')
    get_user_response = requests.get(url, cookies=request.cookies)
    if not get_user_response or get_user_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=get_user_response.json()
        )
    else:
        for cookie in get_user_response.cookies:
            response.set_cookie(key=cookie.name, value=cookie.value, httponly=True)
        return get_user_response.json()


@router.post("/update")
async def update_user(request: Request,
                user_id: str = Form(...),
                first_name: str = Form(""),
                last_name: str = Form(""),
                bio: str = Form(""),
                nickname: str = Form(""),
                password: str = Form(""),
                repeat_password: str = Form(""),
                avatar: UploadFile = File(None), ):
    """
        Forwards getting user by id to the server API and handles the response cookies

        :param request: input request object
        :param user_id: requested user id
        :param first_name: new first name value
        :param last_name: new last name value
        :param nickname: new nickname value
        :param bio: updated user's bio
        :param password: new password
        :param repeat_password: repeat new password
        :param avatar: new avatar image

        :returns JSON-formatted response from server
    """
    send_kwargs = {
        'data': {
            'user_id': user_id,
            'first_name': first_name,
            'last_name': last_name,
            'bio': bio,
            'nickname': nickname,
            'password': password,
            'repeat_password': repeat_password,
        }
    }
    if avatar and avatar.filename:
        send_kwargs['files'] = {'avatar': (avatar.filename, avatar.file.read(), avatar.content_type, )}

    return call_server(url_suffix='/users_api/update',
                       request_method='post',
                       request=request,
                       **send_kwargs)
