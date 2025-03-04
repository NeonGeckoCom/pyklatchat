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

from time import time

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse

from klatchat_utils.common import get_hash, generate_uuid
from chat_server.server_utils.auth import (
    check_password_strength,
    generate_session_token,
    create_unauthorized_user,
)
from klatchat_utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI
from klatchat_utils.http_utils import respond

router = APIRouter(
    prefix="/auth",
    responses={"404": {"description": "Unknown authorization endpoint"}},
)


@router.post("/signup")
async def signup(
    first_name: str = Form(...),
    last_name: str = Form(...),
    nickname: str = Form(...),
    password: str = Form(...),
):
    """
    Creates new user based on received form data

    :param first_name: new user first name
    :param last_name: new user last name
    :param nickname: new user nickname (unique)
    :param password: new user password

    :returns JSON response with status corresponding to the new user creation status,
             sets session cookies if creation is successful
    """
    existing_user = MongoDocumentsAPI.USERS.get_user(nickname=nickname)
    if existing_user:
        return respond("Nickname is already in use", 400)
    password_check = check_password_strength(password)
    if password_check != "OK":
        return respond(password_check, 400)
    new_user_record = dict(
        _id=generate_uuid(length=20),
        first_name=first_name,
        last_name=last_name,
        password=get_hash(password),
        nickname=nickname,
        date_created=int(time()),
        is_tmp=False,
    )
    MongoDocumentsAPI.USERS.add_item(data=new_user_record)

    token = generate_session_token(user_id=new_user_record["_id"])

    return JSONResponse(content=dict(token=token))


@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """
    Logs In user based on provided credentials

    :param username: provided username (nickname)
    :param password: provided password matching username

    :returns JSON response with status corresponding to authorization status, sets session cookie with response
    """
    user = MongoDocumentsAPI.USERS.get_user(nickname=username)
    if not user or user.get("is_tmp", False):
        return respond("Invalid username or password", 400)
    db_password = user["password"]
    if get_hash(password) != db_password:
        return respond("Invalid username or password", 400)
    token = generate_session_token(user_id=user["_id"])
    response = JSONResponse(content=dict(token=token))

    return response


@router.get("/logout")
async def logout():
    """
    Creates temporary user and returns its credentials
    :returns response with temporal cookie
    """
    # TODO: store session tokens in runtime
    user_data = create_unauthorized_user()
    response = JSONResponse(content=dict(token=user_data.session))
    return response
