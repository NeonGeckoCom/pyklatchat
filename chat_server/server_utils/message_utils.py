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

from typing import List

from chat_server.constants.users import UserPatterns
from chat_server.server_config import db_controller
from chat_server.server_utils.user_utils import create_from_pattern


def fetch_shouts(shout_ids: List[str] = None) -> List[dict]:
    """
        Fetches shout data from provided shouts list
        :param shout_ids: list of shout ids to fetch

        :returns Data from requested shout ids along with matching user data
    """
    shouts = db_controller.exec_query(query={'document': 'shouts',
                                             'command': 'find',
                                             'data': {'_id': {'$in': list(set(shout_ids))}}})
    shouts = list(shouts)

    user_ids = list(set([shout['user_id'] for shout in shouts]))

    users_from_shouts = db_controller.exec_query(query={'document': 'users',
                                                        'command': 'find',
                                                        'data': {'_id': {'$in': user_ids}}})

    formatted_users = dict()
    for users_from_shout in users_from_shouts:
        user_id = users_from_shout.pop('_id', None)
        formatted_users[user_id] = users_from_shout

    result = list()

    for shout in shouts:
        matching_user = formatted_users.get(shout['user_id'], {})
        if not matching_user:
            matching_user = create_from_pattern(UserPatterns.UNRECOGNIZED_USER)

        matching_user.pop('password', None)
        matching_user.pop('is_tmp', None)
        shout['message_id'] = shout['_id']
        shout_data = {**shout, **matching_user}
        result.append(shout_data)
    return result
