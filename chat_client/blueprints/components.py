# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2025 Neongecko.com Inc.
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
from fastapi import APIRouter
from starlette.requests import Request

from chat_client.client_config import client_config
from chat_client.client_utils.template_utils import callback_template
from klatchat_utils.http_utils import respond

router = APIRouter(
    prefix="/components",
    responses={"404": {"description": "Unknown endpoint"}},
)


@router.get("/profile")
async def get_profile_modal(request: Request, user_id: str = "", edit: str = "0"):
    """Callbacks template with matching modal populated with user's data"""
    auth_header = "Authorization"
    headers = {auth_header: request.headers.get(auth_header, "")}
    if edit == "1":
        resp = requests.get(
            f'{client_config["SERVER_URL"]}/users_api/', headers=headers
        )
        if resp.ok:
            user = resp.json()["data"]
        else:
            return respond("Server was not able to process the request", 422)
        template_name = "edit_profile_modal"
    else:
        if not user_id:
            return respond("No user_id provided", 422)
        resp = requests.get(
            f'{client_config["SERVER_URL"]}/users_api?user_id={user_id}',
            headers=headers,
        )
        if resp.ok:
            if not (user := resp.json().get("data")):
                return respond(f"User with {user_id=} not found", 404)
        else:
            return respond("Server was not able to process the request", 422)
        template_name = "profile_modal"
    context = {
        "server_url": client_config["SERVER_URL"],
        "user_id": user["_id"],
        "nickname": user["nickname"],
        "first_name": user.get("first_name", "Klat"),
        "last_name": user.get("last_name", "User"),
        "bio": user.get("bio", f'No information about {user["nickname"]}'),
    }
    return callback_template(
        request=request, template_name=template_name, context=context
    )


@router.get("/conversation")
async def render_conversation(request: Request, skin: str = "base"):
    """
    Base renderer by the provided HTML template name

    :param request: FastAPI request object
    :param skin: conversation skin to render (defaults to 'base')

    :returns chats conversation response
    """
    folder = "conversation_skins"
    return callback_template(request=request, template_name=f"{folder}/{skin}")


@router.get("/{template_name}")
async def render_template(request: Request, template_name: str):
    """
    Base renderer by the provided HTML template name

    :param request: FastAPI request object
    :param template_name: name of template to fetch

    :returns chats conversation response
    """
    return callback_template(request=request, template_name=template_name)
