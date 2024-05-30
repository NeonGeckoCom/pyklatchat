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

from fastapi import APIRouter, Form

from chat_server.server_utils.api_dependencies import (
    CurrentUserData,
    SetPreferencesModel,
)
from chat_server.server_utils.api_dependencies.validators.users import (
    get_authorized_user,
)
from utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI
from utils.http_utils import respond

router = APIRouter(
    prefix="/preferences",
    responses={"404": {"description": "Unknown user"}},
)


@router.post("/update")
async def update_settings(
    model: SetPreferencesModel,
    current_user: CurrentUserData = get_authorized_user,
):
    """
    Updates user settings with provided form data
    :param current_user: current user data
    :param model: SetPreferencesModel instance containing user settings to set
    :return: status 200 if OK, error code otherwise
    """
    preferences_mapping = model.dict(exclude_unset=True)
    MongoDocumentsAPI.USERS.set_preferences(
        user_id=current_user.user_id, preferences_mapping=preferences_mapping
    )
    return respond(msg="OK")


@router.post("/update_language/{cid}/{input_type}")
async def update_language(
    cid: str,
    input_type: str,
    lang: str = Form(...),
    current_user: CurrentUserData = get_authorized_user,
):
    """Updates preferred language of user in conversation"""
    MongoDocumentsAPI.USERS.set_preferences(
        user_id=current_user.user_id,
        preferences_mapping={f"chat_language_mapping.{cid}.{input_type}": lang},
    )
    return respond(f"Updated cid={cid}, input_type={input_type} to language={lang}")
