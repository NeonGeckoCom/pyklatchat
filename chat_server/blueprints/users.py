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
from fastapi import APIRouter, Response, status, Request, Query
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.encoders import jsonable_encoder
from neon_utils import LOG

from chat_server.server_config import db_controller
from chat_server.server_utils.auth import get_current_user
from chat_server.server_utils.http_utils import get_file_response

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
    LOG.debug(f"Getting user for {user_id}")
    if user_id:
        user = db_controller.exec_query(query={'document': 'users',
                                               'command': 'find_one',
                                               'data': {'_id': user_id}})
        user.pop('password', None)
        user.pop('date_created', None)
        user.pop('tokens', None)
    else:
        user = get_current_user(request=request,
                                response=response, nano_token=nano_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='User not found'
        )
    LOG.debug(f"Got user: {user}")
    return dict(data=user)


@router.get("/{user_id}/avatar")
def get_avatar(user_id: str):
    """
        Gets file from the server

        :param user_id: target user id
    """
    LOG.debug(f'Getting avatar of user id: {user_id}')
    user_data = db_controller.exec_query(query={'document': 'users',
                                                'command': 'find_one',
                                                'data': {'_id': user_id}})
    file_response = None
    if user_data and user_data.get('avatar', None):
        file_response = get_file_response(filename=user_data['avatar'], location_prefix='avatars')
    return file_response if file_response is not None else 'Failed to get avatar'


@router.get('/bulk_fetch/', response_class=JSONResponse)
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

