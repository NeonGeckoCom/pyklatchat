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

from fastapi import APIRouter, status, UploadFile, File, Form

from chat_server.server_utils.api_dependencies.extractors.users import (
    CurrentUserSessionData,
    CurrentUserData,
)
from chat_server.server_utils.api_dependencies.validators.users import (
    get_authorized_user,
)
from chat_server.server_utils.auth import (
    check_password_strength,
)
from chat_server.server_utils.http_utils import save_file
from utils.common import get_hash
from utils.database_utils.mongo_utils import MongoFilter
from utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI
from utils.http_utils import respond
from utils.logging_utils import LOG

router = APIRouter(
    prefix="/users_api",
    responses={"404": {"description": "Unknown user"}},
)


@router.get("/")
async def get_user(
    session_data: CurrentUserSessionData,
    user_id: str | None = None,
):
    """
    Gets current user data from session cookies

    :param session_data: current user session data
    :param user_id: id of external user (optional, if not provided - current user is returned)

    :returns JSON response containing data of current user
    """
    session_token = ""
    if user_id:
        user = await MongoDocumentsAPI.USERS.get_user(user_id=user_id)
        user.pop("password", None)
        user.pop("date_created", None)
        user.pop("tokens", None)
        if session_data.user.user_id != user_id:
            user.pop("roles", None)
            user.pop("preferences", None)
        LOG.info(f"Fetched user data (id={user_id}): {user}")
    else:
        user = session_data.user
        session_token = session_data.session
    if not user:
        return respond("User not found", 404)
    return dict(data=user, token=session_token)


@router.post("/update")
async def update_profile(
    current_user: CurrentUserData = get_authorized_user,
    first_name: str = Form(""),
    last_name: str = Form(""),
    bio: str = Form(""),
    nickname: str = Form(""),
    password: str = Form(""),
    repeat_password: str = Form(""),
    avatar: UploadFile = File(None),
):
    """
    Gets file from the server

    :param current_user: current user data
    :param first_name: new first name value
    :param last_name: new last name value
    :param nickname: new nickname value
    :param bio: updated user's bio
    :param password: new password
    :param repeat_password: repeat new password
    :param avatar: new avatar image

    :returns status: 200 if data updated successfully, 403 if operation is on tmp user, 401 if something went wrong
    """
    update_dict = {
        "first_name": first_name,
        "last_name": last_name,
        "bio": bio,
        "nickname": nickname,
    }
    if password:
        if password != repeat_password:
            return respond(
                msg="Passwords do not match", status_code=status.HTTP_401_UNAUTHORIZED
            )
        password_check = check_password_strength(password)
        if password_check != "OK":
            return respond(msg=password_check, status_code=status.HTTP_401_UNAUTHORIZED)
        update_dict["password"] = get_hash(password)
    if avatar:
        update_dict["avatar"] = await save_file(location_prefix="avatars", file=avatar)
    try:
        filter_expression = MongoFilter(key="_id", value=current_user.user_id)
        update_dict = {k: v for k, v in update_dict.items() if v}
        await MongoDocumentsAPI.USERS.update_item(
            filters=(filter_expression,), data=update_dict
        )
        return respond(msg="OK")
    except Exception as ex:
        LOG.exception(
            "Unable to update user data", update_data=update_dict, exc_info=ex
        )
        return respond(
            msg="Unable to update user data at the moment",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
