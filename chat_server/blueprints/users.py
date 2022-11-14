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

from typing import Optional
from fastapi import APIRouter, Response, status, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from neon_utils import LOG

from chat_server.server_config import db_controller
from chat_server.server_utils.auth import get_current_user, check_password_strength, get_current_user_data, \
    login_required
from chat_server.server_utils.db_utils import DbUtils
from chat_server.server_utils.http_utils import save_file
from utils.common import get_hash
from utils.http_utils import respond

router = APIRouter(
    prefix="/users_api",
    responses={'404': {"description": "Unknown user"}},
)


@router.get("/")
async def get_user(request: Request,
             response: Response,
             nano_token: str = None,
             user_id: Optional[str] = None):
    """
        Gets current user data from session cookies

        :param request: active client session request
        :param response: response object to be returned to user
        :param nano_token: token from nano client (optional)
        :param user_id: id of external user (optional, if not provided - current user is returned)

        :returns JSON response containing data of current user
    """
    session_token = ''
    if user_id:
        user = db_controller.exec_query(query={'document': 'users',
                                               'command': 'find_one',
                                               'data': {'_id': user_id}})
        user.pop('password', None)
        user.pop('date_created', None)
        user.pop('tokens', None)
        LOG.info(f'Fetched user data (id={user_id}): {user}')
    else:
        current_user_data = get_current_user_data(request=request, nano_token=nano_token)
        user = current_user_data.user
        session_token = current_user_data.session
    if not user:
        return respond('User not found', 404)
    return dict(data=user, token=session_token)


@router.get('/get_users')
# @login_required
async def fetch_received_user_ids(request: Request, user_ids: str = None, nicknames: str = None):
    """
        Gets users data based on provided user ids

        :param request: Starlette Request Object
        :param user_ids: list of provided user ids
        :param nicknames: list of provided nicknames

        :returns JSON response containing array of fetched user data
    """
    filter_data = {}
    if not any(x for x in (user_ids, nicknames)):
        return respond('Either user_ids or nicknames should be provided', 422)
    if user_ids:
        filter_data['_id'] = {'$in': user_ids.split(',')}
    if nicknames:
        filter_data['nickname'] = {'$in': nicknames.split(',')}

    users = db_controller.exec_query(query={'document': 'users',
                                            'command': 'find',
                                            'data': filter_data},
                                     as_cursor=False)
    for user in users:
        user.pop('password', None)
        user.pop('is_tmp', None)
        user.pop('tokens', None)
        user.pop('date_created', None)

    return JSONResponse(content={'users': jsonable_encoder(users)})


@router.post("/update")
@login_required
async def update_profile(request: Request,
                         user_id: str = Form(...),
                         first_name: str = Form(""),
                         last_name: str = Form(""),
                         bio: str = Form(""),
                         nickname: str = Form(""),
                         password: str = Form(""),
                         repeat_password: str = Form(""),
                         avatar: UploadFile = File(None), ):
    """
        Gets file from the server

        :param request: FastAPI Request Object
        :param user_id: submitted user id
        :param first_name: new first name value
        :param last_name: new last name value
        :param nickname: new nickname value
        :param bio: updated user's bio
        :param password: new password
        :param repeat_password: repeat new password
        :param avatar: new avatar image

        :returns status: 200 if data updated successfully, 403 if operation is on tmp user, 401 if something went wrong
    """
    user = get_current_user(request=request)
    if user.get('is_tmp'):
        return respond(msg=f"Unable to update data of 'tmp' user", status_code=status.HTTP_403_FORBIDDEN)
    update_dict = {'first_name': first_name,
                   'last_name': last_name,
                   'bio': bio,
                   'nickname': nickname}
    if password:
        if password != repeat_password:
            return respond(msg='Passwords do not match', status_code=status.HTTP_401_UNAUTHORIZED)
        password_check = check_password_strength(password)
        if password_check != 'OK':
            return respond(msg=password_check, status_code=status.HTTP_401_UNAUTHORIZED)
        update_dict['password'] = get_hash(password)
    if avatar:
        update_dict['avatar'] = await save_file(location_prefix='avatars', file=avatar)
    try:
        filter_expression = {'_id': user['_id']}
        update_expression = {'$set': {k: v for k, v in update_dict.items() if v}}
        db_controller.exec_query(query={'document': 'users',
                                        'command': 'update',
                                        'data': (filter_expression,
                                                 update_expression,)})
        return respond(msg="OK")
    except Exception as ex:
        LOG.error(ex)
        return respond(msg='Unable to update user data at the moment', status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


@router.post("/settings/update")
@login_required
async def update_settings(request: Request,
                          minify_messages: str = Form("0"),):
    """
    Updates user settings with provided form data
    :param request: FastAPI Request Object
    :param minify_messages: "1" if user prefers to get minified messages
    :return: status 200 if OK, error code otherwise
    """
    user = get_current_user(request=request)
    preferences_mapping = {
        'minify_messages': minify_messages
    }
    DbUtils.set_user_preferences(user_id=user['_id'], preferences_mapping=preferences_mapping)
    return respond(msg='OK')
