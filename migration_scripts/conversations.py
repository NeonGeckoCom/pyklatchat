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
from typing import List, Dict, Tuple

from neon_utils import LOG


def get_existing_nicks(mongo_controller, nicknames: List[str]) -> dict:
    """
        Gets nicknames from mongo db

        :param mongo_controller: controller to active mongo collection
        :param nicknames: received nicks from mysql controller

        :returns List of dict containing filtered items
    """
    retrieved_data = mongo_controller.exec_query(query=dict(document='users', command='find',
                                                 data={'nick': {'$in': nicknames}}))
    LOG.info(f'Retrieved {len(list(retrieved_data))} existing nicknames from new db')
    return {record['nick']: record['_id'] for record in retrieved_data}


def index_nicks(mongo_controller, received_nicks: List[str]) -> dict:
    """
        Assigns unique id to each nick that is not present in new db

        :param mongo_controller: controller to active mongo collection
        :param received_nicks: received nicks from mysql controller
    """

    # Excluding existing nicks from loop
    nicks_mapping = get_existing_nicks(mongo_controller, received_nicks)

    nicks_to_consider = list(set(received_nicks) - set(list(nicks_mapping)))

    # Generating UUID for each nick that is not present in new db
    if len(nicks_to_consider) > 0:
        for nick in nicks_to_consider:
            nicks_mapping[nick] = uuid.uuid4().hex

    LOG.info(f'Created nicks mapping for {len(list(nicks_mapping))} records')

    return nicks_mapping


def migrate_conversations(old_db_controller, new_db_controller,
                          time_since: int = 1577829600) -> Tuple[list, Dict[str, str]]:
    """
        Migrating conversations from old database to new one
        :param old_db_controller: old database connector
        :param new_db_controller: new database connector
        :param time_since: timestamp for conversation activity
    """
    LOG.info(f'Considered time since: {time_since}')

    # z = int(time.mktime(datetime.datetime.strptime('01/01/2020', "%d/%m/%Y")))

    get_cids_query = f""" 
                          select * from shoutbox_conversations where updated>{time_since};
                      """

    result = old_db_controller.exec_query(get_cids_query)

    existing_cids = new_db_controller.exec_query(query=dict(document='conversations', command='find', data={
        'cid': {'$in': [r['cid'] for r in result]}
    }))

    existing_cids = [r['cid'] for r in existing_cids]

    LOG.info(f'Found {len(existing_cids)} existing cids')

    if existing_cids:
        result = list(filter(lambda x: x['cid'] not in existing_cids, result))

    LOG.info(f'Received {len(result)} new cids')

    received_nicks = [record['creator'] for record in result]

    nicknames_mapping = index_nicks(mongo_controller=new_db_controller,
                                    received_nicks=received_nicks)

    new_cids_list = []

    if result:

        for record in result:
            record['creator'] = nicknames_mapping.get(record['creator'], record['creator'])

        new_db_controller.exec_query(query=dict(document='conversations', command='insert_many', data=result))

        new_cids_list = [str(x['cid']) for x in result]

    return new_cids_list, nicknames_mapping

