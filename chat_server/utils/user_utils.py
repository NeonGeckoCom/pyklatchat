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
import copy
from time import time

from chat_server.constants.users import UserPatterns
from utils.common import get_hash, generate_uuid
from utils.database_utils import DatabaseController


def create_from_pattern(source: UserPatterns, override_defaults: dict = None) -> dict:
    """
        Creates user record based on provided pattern from UserPatterns

        :param source: source pattern from UserPatterns
        :param override_defaults: to override default values (optional)
        :returns user data populated with default values where necessary
    """
    if not override_defaults:
        override_defaults = {}

    matching_data = {**copy.deepcopy(source.value), **override_defaults}

    matching_data.setdefault('_id', generate_uuid(length=20))
    matching_data.setdefault('password', get_hash(generate_uuid()))
    matching_data.setdefault('date_created', int(time()))
    matching_data.setdefault('is_tmp', True)

    return matching_data


def get_neon_data(db_controller: DatabaseController) -> dict:
    """
        Gets a user profile for the user 'Neon' and adds it to the users db if not already present

        :param db_controller: db controller instance

        :return Neon AI data
    """
    neon_data = db_controller.exec_query({'command': 'find_one', 'document': 'users',
                                         'data': {'nickname': 'neon'}})
    if not neon_data:
        neon_data = create_from_pattern(source=UserPatterns.NEON)
        db_controller.exec_query({'command': 'insert_one', 'document': 'users', 'data': neon_data})
    return neon_data


def get_bot_data(db_controller: DatabaseController, nickname: str, context: dict = None) -> dict:
    """
        Gets a user profile for the requested bot instance and adds it to the users db if not already present

        :param db_controller: db controller instance
        :param nickname: nickname of the bot provided
        :param context: context with additional bot information (optional)

        :return Matching bot data
    """
    if not context:
        context = {}
    full_nickname = nickname
    nickname = nickname.split('-')[0]
    bot_data = db_controller.exec_query({'command': 'find_one', 'document': 'users',
                                        'data': {'nickname': nickname}})
    if not bot_data:
        bot_data = dict(_id=generate_uuid(length=20),
                        first_name=context.get('first_name', nickname.capitalize()),
                        last_name=context.get('last_name', ''),
                        avatar=context.get('avatar', ''),
                        password=get_hash(generate_uuid()),
                        nickname=nickname,
                        full_nickname=full_nickname,
                        date_created=int(time()),
                        is_tmp=False)
        db_controller.exec_query({'command': 'insert_one', 'document': 'users', 'data': bot_data})
    return bot_data
