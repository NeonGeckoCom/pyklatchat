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

from neon_utils import LOG


def migrate_shouts(old_db_controller, new_db_controller, nick_to_uuid_mapping: dict, from_cids: list):
    """
        Migrating users from old database to new one
        :param old_db_controller: old database connector
        :param new_db_controller: new database connector
        :param nick_to_uuid_mapping: mapping of nicks to uuid
        :param from_cids: list of considered conversation ids
    """

    existing_shouts = new_db_controller.exec_query(query=dict(document='shouts', command='find', data={}))

    nick_to_uuid_mapping = {k.strip().lower(): v for k, v in copy.deepcopy(nick_to_uuid_mapping).items() if k}

    LOG.info('Starting shouts migration')

    users = ', '.join(["'" + nick.replace("'", "") + "'" for nick in list(nick_to_uuid_mapping)])

    existing_shout_ids = ', '.join(["'" + shout['_id'] + "'" for shout in list(existing_shouts)])

    considered_cids = ', '.join(["'" + cid + "'" for cid in from_cids])

    get_shouts_query = f""" SELECT * FROM shoutbox 
                            WHERE nick IN ({users}) 
                            AND shout_id NOT IN ({existing_shout_ids})
                            AND cid IN ( {considered_cids} ); """

    result = old_db_controller.exec_query(get_shouts_query)

    LOG.info(f'Received {len(list(result))} new shouts')

    for record in result:
        try:
            insertion_record = {
                '_id': record['shout_id'],
                'domain': record['domain'],
                'user_id': nick_to_uuid_mapping[str(record['nick']).strip().lower()],
                'created_on': int(record['created']),
                'shout': record['shout'],
                'language': record['language'],
                'cid': record['cid']  # for alignment recovery on order failure
            }

            new_db_controller.exec_query(query=dict(document='shouts',
                                                    command='update',
                                                    data=({'_id': insertion_record['_id']},
                                                          {"$set": insertion_record})),
                                         upsert=True)

            new_db_controller.exec_query(query=dict(document='chats',
                                                    command='update',
                                                    data=({'_id': record['cid']},
                                                          {'$push': {'chat_flow': record['shout_id']}})))

        except Exception as ex:
            LOG.error(f'Skipping processing of shout data "{record}" due to exception: {ex}')
            continue
