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
from chat_server.server_utils.auth import get_current_user, check_password_strength
from chat_server.server_utils.http_utils import save_file
from utils.common import get_hash

router = APIRouter(
    prefix="/users_api",
    responses={'404': {"description": "Unknown user"}},
)


@router.get("/", response_class=JSONResponse)
def get_user(response: Response,
             request: Request,
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
    if user_id:
        user = db_controller.exec_query(query={'document': 'users',
                                               'command': 'find_one',
                                               'data': {'_id': user_id}})
        user.pop('password', None)
        user.pop('date_created', None)
        user.pop('tokens', None)
        LOG.info(f'Fetched user data (id={user_id}): {user}')
    else:
        user = get_current_user(request=request, response=response, nano_token=nano_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='User not found'
        )
    return dict(data=user)


@router.get('/get_users', response_class=JSONResponse)
def fetch_received_user_ids(user_ids: List[str] = Query(None)):
    """
        Gets users data based on provided user ids

        :param user_ids: list of provided user ids

        :returns JSON response containing array of fetched user data
    """
    user_ids = user_ids[0].split(',')
    users = db_controller.exec_query(query={'document': 'users',
                                            'command': 'find',
                                            'data': {'_id': {'$in': list(set(user_ids))}}})
    users = list(users)

    formatted_users = dict()

    for user in users:
        formatted_users[user['_id']] = user

    result = list()

    for user_id in user_ids:
        desired_record = formatted_users.get(user_id, {})
        if len(list(desired_record)) > 0:
            desired_record.pop('password', None)
            desired_record.pop('is_tmp', None)
            desired_record.pop('tokens', None)
            desired_record.pop('date_created', None)
        result.append(desired_record)
    json_compatible_item_data = jsonable_encoder(result)
    return JSONResponse(content=json_compatible_item_data)


@router.post("/update")
async def update_profile(request: Request,
                   response: Response,
                   first_name: str = Form(...),
                   last_name: str = Form(...),
                   bio: str = Form(...),
                   nickname: str = Form(...),
                   password: str = Form(...),
                   repeat_password: str = Form(...),
                   avatar: UploadFile = File(...),):
    """
        Gets file from the server

        :param request: FastAPI Request Object
        :param response: FastAPI Response Object
        :param first_name: new first name value
        :param last_name: new last name value
        :param nickname: new nickname value
        :param bio: updated user's bio
        :param password: new password
        :param repeat_password: repeat new password
        :param avatar: new avatar image

        :returns status: 200 if data updated successfully, 403 if operation is on tmp user, 401 if something went wrong
    """
    user = get_current_user(request=request, response=response)
    if user.get('is_tmp'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Unable to update data of 'tmp' user"
        )
    update_dict = {'first_name': first_name,
                   'last_name': last_name,
                   'bio': bio,
                   'nickname': nickname}
    if password and password != repeat_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Passwords do not match'
        )
    password_check = check_password_strength(password)
    if password_check != 'OK':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=password_check
        )
    update_dict['password'] = get_hash(password)
    if avatar:
        await save_file(location_prefix='avatar', file=avatar)
