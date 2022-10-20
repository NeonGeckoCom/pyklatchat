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

from neon_utils import LOG
from pymongo import ReplaceOne, UpdateOne

from chat_server.server_utils.db_utils import DbUtils, MongoQuery, MongoCommands, MongoDocuments
from migration_scripts.utils.shout_utils import prepare_nicks_for_sql
from migration_scripts.utils.sql_utils import iterable_to_sql_array, sql_arr_is_null


def migrate_shouts(old_db_controller, new_db_controller, nick_to_uuid_mapping: dict, from_cids: list):
    """
        Migrating users from old database to new one
        :param old_db_controller: old database connector
        :param new_db_controller: new database connector
        :param nick_to_uuid_mapping: mapping of nicks to uuid
        :param from_cids: list of considered conversation ids
    """

    existing_shouts = list(new_db_controller.exec_query(query=dict(document='shouts', command='find', data={})))

    nick_to_uuid_mapping = {k.strip().lower(): v for k, v in copy.deepcopy(nick_to_uuid_mapping).items() if k}

    LOG.info('Starting shouts migration')

    users = iterable_to_sql_array(prepare_nicks_for_sql(list(nick_to_uuid_mapping)))
    filter_str = f"WHERE nick IN {users} "

    existing_shout_ids = iterable_to_sql_array([str(shout['_id']) for shout in list(existing_shouts)])
    if not sql_arr_is_null(existing_shout_ids):
        filter_str += f"AND shout_id NOT IN {existing_shout_ids}"

    considered_cids = iterable_to_sql_array([str(cid).strip() for cid in from_cids])
    if not sql_arr_is_null(considered_cids):
        filter_str += f"AND cid IN {considered_cids}"

    get_shouts_query = f""" SELECT * FROM shoutbox {filter_str};"""
    result = old_db_controller.exec_query(get_shouts_query)

    LOG.info(f'Received {len(list(result))} shouts')

    formed_result = []

    for record in result:

        for k in list(record):
            if isinstance(record[k], (bytearray, bytes)):
                record[k] = str(record[k].decode('utf-8'))

        formed_result.append(ReplaceOne({'_id': str(record['shout_id'])},
                                {
                                    '_id': str(record['shout_id']),
                                    'domain': record['domain'],
                                    'user_id': nick_to_uuid_mapping.get(record['nick'], 'undefined'),
                                    'created_on': int(record['created']),
                                    'message_text': record['shout'],
                                    'language': record['language'],
                                    'cid': str(record['cid'])
                                }, upsert=True))

    if len(formed_result) > 0:

        new_db_controller.exec_query(query=dict(document='shouts',
                                                command='bulk_write',
                                                data=formed_result))

    LOG.info('Starting inserting shouts in conversations')

    for record in result:

        try:
            new_db_controller.exec_query(query=dict(document='chats',
                                                    command='update',
                                                    data=({'_id': record['cid']},
                                                          {'$push': {'chat_flow': str(record['shout_id'])}})))
        except Exception as ex:
            LOG.error(f'Skipping processing of shout data "{record}" due to exception: {ex}')
            continue


def remap_creation_timestamp(db_controller):
    """ Remaps creation timestamp from millis to seconds """
    filter_stage = {
        '$match': {
            'created_on': {
                '$gte': 10 ** 12
            }
        }
    }
    bulk_update = []
    res = list(DbUtils.db_controller.connector.connection["shouts"].aggregate([filter_stage]))
    for item in res:
        bulk_update.append(UpdateOne({'_id': item['_id']},
                                     {'$set': {'created_on': item['created_on'] // 10 ** 3}}))
    db_controller.exec_query(query=MongoQuery(command=MongoCommands.BULK_WRITE,
                                              document=MongoDocuments.SHOUTS,
                                              data=bulk_update))


def set_cid_to_shouts(db_controller):
    """ Sets correspondent cid to new shouts """
    conversion_stage = {
        '$addFields': {'str_id': {'$toString': "$_id"}}
    }
    add_str_length = {
        '$addFields': {'length': {'$strLenCP': "$str_id"}}
    }
    filter_stage = {
        '$match': {
            'length': {
                '$gt': 5
            }
        }
    }
    bulk_update = []
    res = list(db_controller.connector.connection["chats"].aggregate([conversion_stage, add_str_length, filter_stage]))
    for item in res:
        for shout in item.get('chat_flow', []):
            bulk_update.append(UpdateOne({'_id': shout},
                                         {'$set': {'cid': item['_id']}}))
    DbUtils.db_controller.exec_query(query=MongoQuery(command=MongoCommands.BULK_WRITE,
                                     document=MongoDocuments.SHOUTS,
                                     data=bulk_update))
