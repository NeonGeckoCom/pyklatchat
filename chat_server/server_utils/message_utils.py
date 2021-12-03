from typing import List

from chat_server.constants.users import UserPatterns
from chat_server.server_config import db_controller
from chat_server.server_utils.user_utils import create_from_pattern


def fetch_shouts(shout_ids: List[str] = None):
    """
        Fetches shout data from provided shouts list
        :param shout_ids: list of shout ids to fetch
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
