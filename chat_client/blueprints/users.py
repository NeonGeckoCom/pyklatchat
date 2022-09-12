# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
#
# Copyright 2008-2021 Neongecko.com Inc. | All Rights Reserved
#
# Notice of License - Duplicating this Notice of License near the start of any file containing
# a derivative of this software is a condition of license for this software.
# Friendly Licensing:
# No charge, open source royalty free use of the Neon AI software source and object is offered for
# educational users, noncommercial enthusiasts, Public Benefit Corporations (and LLCs) and
# Social Purpose Corporations (and LLCs). Developers can contact developers@neon.ai
# For commercial licensing, distribution of derivative works or redistribution please contact licenses@neon.ai
# Distributed on an "AS IS” basis without warranties or conditions of any kind, either express or implied.
# Trademarks of Neongecko: Neon AI(TM), Neon Assist (TM), Neon Communicator(TM), Klat(TM)
# Authors: Guy Daniels, Daniel McKnight, Elon Gasper, Richard Leeds, Kirill Hrymailo
#
# Specialized conversational reconveyance options from Conversation Processing Intelligence Corp.
# US Patents 2008-2021: US7424516, US20140161250, US20140177813, US8638908, US8068604, US8553852, US10530923, US10530924
# China Patent: CN102017585  -  Europe Patent: EU2156652  -  Patents Pending


import requests

from neon_utils import LOG

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
def get_user(response: Response, request: Request, user_id: Optional[str] = None):
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
def update_user(request: Request,
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
