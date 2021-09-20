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
import datetime
import time
import uuid
from typing import List

from neon_utils import LOG


def get_existing_nicks(mongo_controller, nicknames: List[str]) -> List[str]:
    """
        Gets nicknames from mongo db

        :param mongo_controller: controller to active mongo collection
        :param nicknames: received nicks from mysql controller

        :returns List of dict containing filtered items
    """
    retrieved_data = mongo_controller.exec_query(query=dict(document='conversations', command='find',
                                                 data={'nickname': {'$in': nicknames}}))
    LOG.info(f'Retrieved {len(list(retrieved_data))} existing nicknames from new db')
    return [record['nickname'] for record in retrieved_data]


def index_nicks(mongo_controller, received_nicks: List[str]) -> dict:
    """
        Assigns unique id to each nick that is not present in new db

        :param mongo_controller: controller to active mongo collection
        :param received_nicks: received nicks from mysql controller
    """
    nicks_mapping = {}

    # Excluding existing nicks from loop
    existing_nicks = get_existing_nicks(mongo_controller, received_nicks)
    nicks_to_consider = list(set(received_nicks) - set(existing_nicks))

    # Generating UUID for each nick that is not present in new db
    if len(nicks_to_consider) > 0:
        for nick in nicks_to_consider:
            nicks_mapping[nick] = uuid.uuid4().hex

    LOG.info(f'Created nicks mapping for {len(list(nicks_mapping))} records')

    return nicks_mapping


def migrate_conversations(old_db_controller, new_db_controller,
                          time_since: int = 1577829600):
    """
        Migrating conversations from old database to new one
        :param old_db_controller: old database connector
        :param new_db_controller: new database connector
        :param time_since: timestamp for conversation activity
    """
    LOG.info(f'Considered time since: {time_since}')

    # z = int(time.mktime(datetime.datetime.strptime('01/01/2020', "%d/%m/%Y")))

    get_user_columns = """ SELECT COLUMN_NAME FROM information_schema.columns 
                           WHERE TABLE_NAME = 'shoutbox_conversations'; """

    columns = old_db_controller.exec_query(get_user_columns, generator=True)

    columns = [c[0] for c in columns]

    LOG.debug(f'Received column names: {columns}')

    get_cids_query = f""" 
                          select * from shoutbox_conversations where updated>1577829600;
                      """

    result = old_db_controller.exec_query(get_cids_query)

    result_list = []
    for record in result:
        result_dict = {}
        for idx in range(len(columns[:-3])):
            result_dict[columns[idx]] = record[idx]
        result_list.append(result_dict)

    LOG.info(f'Received {len(result_list)} matching cids')

    received_nicks = [record['creator'] for record in result_list]

    nicknames_mapping = index_nicks(mongo_controller=new_db_controller,
                                    received_nicks=received_nicks)

    for record in result_list:
        record['creator'] = nicknames_mapping.get(record['creator'], record['creator'])

    new_db_controller.exec_query(query=dict(document='conversations', command='insert_many', data=result_list))

    return [str(x['cid']) for x in result_list], nicknames_mapping

