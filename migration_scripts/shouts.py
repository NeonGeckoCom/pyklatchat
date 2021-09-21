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
import copy
import datetime
import time
from decimal import Decimal

from neon_utils import LOG


def migrate_shouts(old_db_controller, new_db_controller, nick_to_uuid_mapping: dict):
    """
        Migrating users from old database to new one
        :param old_db_controller: old database connector
        :param new_db_controller: new database connector
        :param nick_to_uuid_mapping: mapping of nicks to uuid
    """

    # nick_to_uuid_mapping = {k.lower(): v for k, v in nick_to_uuid_mapping.items() if k}
    nick_to_uuid_mapping_copy = copy.deepcopy(nick_to_uuid_mapping)

    nick_to_uuid_mapping = {}

    for key, value in nick_to_uuid_mapping_copy.items():
        if key and value not in nick_to_uuid_mapping.values():
            nick_to_uuid_mapping[key.lower()] = value

    LOG.info('Starting shouts migration')

    # last_timestamp = time.mktime(datetime.datetime.strptime('01/01/2020', "%d/%m/%Y").timetuple())

    users = ', '.join(["'"+nick.split("'")[0]+"'" for nick in list(nick_to_uuid_mapping)])

    get_shouts_query = f""" SELECT * FROM shoutbox WHERE nick IN ({users}); """

    result = old_db_controller.exec_query(get_shouts_query)

    for record in result:
        try:
            record['_id'] = nick_to_uuid_mapping[str(record['nick']).strip().lower()]
            for key, value in record.items():
                if isinstance(value, Decimal):
                    record[key] = int(value)
        except Exception as ex:
            LOG.error(f'Resolving of record {record} failed: {ex}')
            continue

    if result:
        new_db_controller.exec_query(query=dict(document='shouts', command='insert_many', data=result))

    LOG.info(f'Received {len(list(result))} new shouts')
