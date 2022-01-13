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
from typing import List, Dict, Tuple

from neon_utils import LOG
from pymongo import ReplaceOne

from migration_scripts.utils.conversation_utils import clean_conversation_name, index_nicks


def migrate_conversations(old_db_controller, new_db_controller,
                          time_since: int = 1577829600) -> Tuple[List[str], Dict[str, str], List[str]]:
    """
        Migrating conversations from old database to new one
        :param old_db_controller: old database connector
        :param new_db_controller: new database connector
        :param time_since: timestamp for conversation activity
    """
    LOG.info(f'Starting chats migration')

    get_cids_query = f""" 
                          select * from shoutbox_conversations where updated>{time_since};
                      """

    result = old_db_controller.exec_query(get_cids_query)

    result_cids = [str(r['cid']) for r in result]

    existing_cids = list(new_db_controller.exec_query(query=dict(document='chats', command='find', data={
        '_id': {'$in': result_cids}
    })))

    existing_cids = [r['_id'] for r in existing_cids]

    all_cids_in_scope = list(set(existing_cids+result_cids))

    LOG.info(f'Found {len(existing_cids)} existing cids')

    if existing_cids:
        result = list(filter(lambda x: str(x['cid']) not in existing_cids, result))

    LOG.info(f'Received {len(result)} new cids')

    received_nicks = [record['creator'] for record in result if record['creator'] is not None]

    nicknames_mapping, nicks_to_consider = index_nicks(mongo_controller=new_db_controller,
                                                       received_nicks=received_nicks)

    LOG.debug(f'Records to process: {len(result)}')

    formed_result = [ReplaceOne({'_id': str(record['cid'])},
                                {
                                    '_id': str(record['cid']),
                                    'is_private': int(record['private']) == 1,
                                    'domain': record['domain'],
                                    'image': record['image_url'],
                                    'password': record['password'],
                                    'conversation_name': f"{clean_conversation_name(record['title'])}_{record['cid']}",
                                    'chat_flow': [],
                                    'creator': nicknames_mapping.get(record['creator'], record['creator']),
                                    'created_on': int(record['created'])
                                }, upsert=True) for record in result
                     ]

    if len(formed_result) > 0:

        new_db_controller.exec_query(query=dict(document='chats',
                                                command='bulk_write',
                                                data=formed_result))
    else:
        LOG.info('All chats are already in new deb, skipping chat migration')

    return all_cids_in_scope, nicknames_mapping, nicks_to_consider
