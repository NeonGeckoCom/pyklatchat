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

from typing import List, Optional
from fastapi import APIRouter, Response, status, Request, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.encoders import jsonable_encoder
from neon_utils import LOG

from chat_server.server_config import db_controller
from chat_server.server_utils.auth import get_current_user, check_password_strength, get_current_user_data, \
    login_required
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
@login_required
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
    if user['_id'] != user_id:
        return respond(msg='Cannot update data of unauthorized user', status_code=status.HTTP_403_FORBIDDEN)
    elif user.get('is_tmp'):
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
        filter_expression = {'_id': user_id}
        update_expression = {'$set': {k: v for k, v in update_dict.items() if v}}
        db_controller.exec_query(query={'document': 'users',
                                        'command': 'update',
                                        'data': (filter_expression,
                                                 update_expression,)})
        return respond(msg="OK")
    except Exception as ex:
        LOG.error(ex)
        return respond(msg='Unable to update user data at the moment', status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
