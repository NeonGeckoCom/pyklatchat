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

from typing import List, Tuple, Union, Dict

import pymongo
from bson import ObjectId
from neon_utils import LOG
from pymongo import UpdateOne

from chat_server.constants.conversations import ConversationSkins
from chat_server.constants.users import UserPatterns
from chat_server.server_utils.factory_utils import Singleton
from chat_server.server_utils.user_utils import create_from_pattern
from utils.common import buffer_to_base64
from utils.database_utils.mongo_utils import *


class DbUtils(metaclass=Singleton):
    """ Singleton DB Utils class for convenience"""

    db_controller = None

    @classmethod
    def init(cls, db_controller):
        """ Inits Singleton with specified database controller """
        cls.db_controller = db_controller

    @classmethod
    def get_user(cls, user_id=None, nickname=None) -> Union[dict, None]:
        """
            Gets user data based on provided params
            :param user_id: target user id
            :param nickname: target user nickname
        """
        if not any(x for x in (user_id, nickname,)):
            LOG.warning('Neither user_id nor nickname was provided')
            return
        filter_data = {}
        if user_id:
            filter_data['_id'] = user_id
        if nickname:
            filter_data['nickname'] = nickname
        return cls.db_controller.exec_query(MongoQuery(command=MongoCommands.FIND_ONE,
                                                       document=MongoDocuments.USERS,
                                                       filters=filter_data))

    @classmethod
    def list_items(cls, document: MongoDocuments, source_set: list, key: str = 'id', value_keys: list = None) -> dict:
        """
            Lists items under provided document belonging to source set of provided column values

            :param document: source document to query
            :param key: document's key to check
            :param source_set: list of :param key values to check
            :param value_keys: list of value keys to return
            :returns results aggregated by :param column value
        """
        if not value_keys:
            value_keys = []
        if key == 'id':
            key = '_id'
        aggregated_data = {}
        if source_set:
            source_set = list(set(source_set))
            items = cls.db_controller.exec_query(MongoQuery(command=MongoCommands.FIND_ALL,
                                                            document=document,
                                                            filters=MongoFilter(key=key,
                                                                                value=source_set,
                                                                                logical_operator=MongoLogicalOperators.IN)))
            for item in items:
                items_key = item.pop(key, None)
                if items_key:
                    aggregated_data.setdefault(items_key, []).append({k: v for k, v in item.items() if k in value_keys
                                                                      or not value_keys})
        return aggregated_data

    @classmethod
    def get_conversation_data(cls, search_str: Union[list, str], column_identifiers: List[str] = None) -> Union[None,
                                                                                                                dict]:
        """
            Gets matching conversation data
            :param search_str: search string to lookup
            :param column_identifiers: desired column identifiers to lookup
        """
        if isinstance(search_str, str):
            search_str = [search_str]
        if not column_identifiers:
            column_identifiers = ['_id', 'conversation_name']
        or_expression = []
        for _keyword in [item for item in search_str if item is not None]:
            for identifier in column_identifiers:
                if identifier == '_id' and isinstance(_keyword, str):
                    or_expression.append({identifier: ObjectId(_keyword)})
                or_expression.append({identifier: _keyword})

        conversation_data = cls.db_controller.exec_query(MongoQuery(command=MongoCommands.FIND_ONE,
                                                                    document=MongoDocuments.CHATS,
                                                                    filters=MongoFilter(value=or_expression,
                                                                                        logical_operator=MongoLogicalOperators.OR)))
        if not conversation_data:
            return
        conversation_data['_id'] = str(conversation_data['_id'])
        return conversation_data

    @classmethod
    def fetch_shout_data(cls, conversation_data: dict, start_idx: int = 0, limit: int = 100,
                         fetch_senders: bool = True, id_from: str = None,
                         shout_ids: List[str] = None) -> List[dict]:
        """
            Fetches shout data out of conversation data

            :param conversation_data: input conversation data
            :param start_idx: message index to start from (sorted by recency)
            :param limit: number of shouts to fetch
            :param fetch_senders: to fetch shout senders data
            :param id_from: message id to start from
            :param shout_ids: list of shout ids to fetch
        """
        if not shout_ids and conversation_data.get('chat_flow', None):
            if id_from:
                try:
                    start_idx = len(conversation_data["chat_flow"]) - \
                                conversation_data["chat_flow"].index(id_from)
                except ValueError:
                    LOG.warning('Matching start message id not found')
                    return []
            if start_idx == 0:
                conversation_data['chat_flow'] = conversation_data['chat_flow'][start_idx - limit:]
            else:
                conversation_data['chat_flow'] = conversation_data['chat_flow'][-start_idx - limit:
                                                                                -start_idx]
            shout_ids = [str(msg_id) for msg_id in conversation_data["chat_flow"]]
        shouts_data = cls.fetch_shouts(shout_ids=shout_ids, fetch_senders=fetch_senders)
        return sorted(shouts_data, key=lambda user_shout: int(user_shout['created_on']))

    @classmethod
    def fetch_users_from_prompt(cls, prompt: dict):
        """ Fetches user ids detected in provided prompt """
        prompt_data = prompt['data']
        user_ids = prompt_data.get('participating_subminds', [])
        return cls.list_items(document=MongoDocuments.USERS, source_set=user_ids, value_keys=['first_name',
                                                                                              'last_name',
                                                                                              'nickname',
                                                                                              'avatar'])

    @classmethod
    def fetch_messages_from_prompt(cls, prompt: dict):
        """ Fetches message ids detected in provided prompt """
        prompt_data = prompt['data']
        message_ids = []
        for column in ('proposed_responses', 'submind_opinions', 'votes',):
            message_ids.extend(list(prompt_data.get(column, {}).values()))
        return cls.list_items(document=MongoDocuments.SHOUTS, source_set=message_ids)

    @classmethod
    def fetch_prompt_data(cls, cid: str, limit: int = 100, id_from: str = None,
                          prompt_id: str = None, fetch_user_data: bool = False) -> List[dict]:
        """
            Fetches prompt data out of conversation data

            :param cid: target conversation id
            :param limit: number of prompts to fetch
            :param id_from: prompt id to start from
            :param prompt_id: prompt id to fetch
            :param fetch_user_data: to fetch user data in the

            :returns list of matching prompt data along with matching messages and users
        """
        filters = [MongoFilter('cid', cid)]
        if id_from:
            checkpoint_prompt = cls.db_controller.exec_query(MongoQuery(document=MongoDocuments.PROMPTS,
                                                                        command=MongoCommands.FIND_ONE,
                                                                        filters=MongoFilter('_id', id_from)))
            if checkpoint_prompt:
                filters.append(MongoFilter('created_on', checkpoint_prompt['created_on'], MongoLogicalOperators.LT))
        if prompt_id:
            filters.append(MongoFilter('_id', prompt_id, MongoLogicalOperators.EQ))
        matching_prompts = cls.db_controller.exec_query(query=MongoQuery(document=MongoDocuments.PROMPTS,
                                                                         command=MongoCommands.FIND_ALL,
                                                                         filters=filters,
                                                                         result_filters={'sort': [('created_on',
                                                                                                   pymongo.DESCENDING)],
                                                                                         'limit': limit}),
                                                        as_cursor=False)
        for prompt in matching_prompts:
            prompt['user_mapping'] = cls.fetch_users_from_prompt(prompt)
            prompt['message_mapping'] = cls.fetch_messages_from_prompt(prompt)
            if fetch_user_data:
                for user in prompt.get('data', {}).get('participating_subminds', []):
                    try:
                        nick = prompt['user_mapping'][user][0]['nickname']
                    except KeyError:
                        LOG.warning(f'user_id - "{user}" was not detected setting it as nick')
                        nick = user
                    for k in ('proposed_responses', 'submind_opinions', 'votes',):
                        msg_id = prompt['data'][k].pop(user, '')
                        if msg_id:
                            prompt['data'][k][nick] = prompt['message_mapping'].get(msg_id, [{}])[0].get('message_text') or msg_id
                prompt['data']['participating_subminds'] = [prompt['user_mapping'][x][0]['nickname']
                                                            for x in prompt['data']['participating_subminds']]
        return sorted(matching_prompts, key=lambda _prompt: int(_prompt['created_on']))

    @classmethod
    def fetch_skin_message_data(cls, skin: ConversationSkins, conversation_data: dict, start_idx: int = 0,
                                limit: int = 100,
                                fetch_senders: bool = True, start_message_id: str = None):
        """ Fetches message data based on provided conversation skin """
        if skin == ConversationSkins.BASE:
            message_data = cls.fetch_shout_data(conversation_data=conversation_data,
                                                fetch_senders=fetch_senders,
                                                start_idx=start_idx,
                                                id_from=start_message_id,
                                                limit=limit)
        elif skin == ConversationSkins.PROMPTS:
            message_data = cls.fetch_prompt_data(cid=conversation_data['_id'],
                                                 id_from=start_message_id,
                                                 limit=limit)
        else:
            LOG.error(f'Failed to resolve skin={skin}')
            message_data = []
        return message_data

    @classmethod
    def fetch_shouts(cls, shout_ids: List[str] = None, fetch_senders: bool = True) -> List[dict]:
        """
            Fetches shout data from provided shouts list
            :param shout_ids: list of shout ids to fetch
            :param fetch_senders: to fetch shout senders data

            :returns Data from requested shout ids along with matching user data
        """
        if not shout_ids:
            return []
        shouts = cls.db_controller.exec_query(query=MongoQuery(command=MongoCommands.FIND_ALL,
                                                               document=MongoDocuments.SHOUTS,
                                                               filters=MongoFilter('_id', list(set(shout_ids)),
                                                                                   MongoLogicalOperators.IN)),
                                              as_cursor=False)
        result = list()

        if fetch_senders:
            user_ids = list(set([shout['user_id'] for shout in shouts]))

            users_from_shouts = cls.db_controller.exec_query(query=MongoQuery(command=MongoCommands.FIND_ALL,
                                                                              document=MongoDocuments.USERS,
                                                                              filters=MongoFilter('_id', user_ids,
                                                                                                  MongoLogicalOperators.IN)))

            formatted_users = dict()
            for users_from_shout in users_from_shouts:
                user_id = users_from_shout.pop('_id', None)
                formatted_users[user_id] = users_from_shout

            for shout in shouts:
                matching_user = formatted_users.get(shout['user_id'], {})
                if not matching_user:
                    matching_user = create_from_pattern(UserPatterns.UNRECOGNIZED_USER)

                matching_user.pop('password', None)
                matching_user.pop('is_tmp', None)
                shout['message_id'] = shout['_id']
                shout_data = {**shout, **matching_user}
                result.append(shout_data)
            shouts = result
        return shouts

    @classmethod
    def get_translations(cls, translation_mapping: dict) -> Tuple[dict, dict]:
        """
            Gets translation from db based on provided mapping

            :param translation_mapping: mapping of cid to desired translation language

            :return translations fetched from db
        """
        populated_translations = {}
        missing_translations = {}
        for cid, cid_data in translation_mapping.items():
            lang = cid_data.get('lang', 'en')
            shout_ids = cid_data.get('shouts', [])
            conversation_data = cls.get_conversation_data(search_str=cid)
            if not conversation_data:
                LOG.error(f'Failed to fetch conversation data - {cid}')
                continue
            shout_data = cls.fetch_shout_data(conversation_data=conversation_data,
                                              shout_ids=shout_ids,
                                              fetch_senders=False)
            shout_lang = 'en'
            if len(shout_data) == 1:
                shout_lang = shout_data[0].get('message_lang', 'en')
            for shout in shout_data:
                message_text = shout.get('message_text')
                if shout_lang != 'en' and lang == 'en':
                    shout_text = message_text
                else:
                    shout_text = shout.get('translations', {}).get(lang)
                if shout_text and lang != 'en':
                    populated_translations.setdefault(cid, {}).setdefault('shouts', {})[shout['_id']] = shout_text
                elif message_text:
                    missing_translations.setdefault(cid, {}).setdefault('shouts', {})[shout['_id']] = message_text
            if missing_translations.get(cid):
                missing_translations[cid]['lang'] = lang
                missing_translations[cid]['source_lang'] = shout_lang
        return populated_translations, missing_translations

    @classmethod
    def save_translations(cls, translation_mapping: dict) -> Dict[str, List[str]]:
        """
            Saves translations in DB
            :param translation_mapping: mapping of cid to desired translation language
            :returns dictionary containing updated shouts (those which were translated to English)
        """
        updated_shouts = {}
        for cid, shout_data in translation_mapping.items():
            translations = shout_data.get('shouts', {})
            bulk_update = []
            shouts = cls.db_controller.exec_query(query=MongoQuery(command=MongoCommands.FIND_ALL,
                                                                   document=MongoDocuments.SHOUTS,
                                                                   filters=MongoFilter('_id', list(translations),
                                                                                       MongoLogicalOperators.IN)),
                                                  as_cursor=False)
            for shout_id, translation in translations.items():
                matching_instance = None
                for shout in shouts:
                    if shout['_id'] == shout_id:
                        matching_instance = shout
                        break
                if not matching_instance.get('translations'):
                    filter_expression = {'_id': shout_id}
                    cls.db_controller.exec_query(query=MongoQuery(command=MongoCommands.UPDATE,
                                                                  document=MongoDocuments.SHOUTS,
                                                                  filters=filter_expression,
                                                                  data={'translations': {}},
                                                                  data_action='set'))
                # English is the default language, so it is treated as message text
                if shout_data.get('lang', 'en') == 'en':
                    updated_shouts.setdefault(cid, []).append(shout_id)
                    filter_expression = {'_id': shout_id}
                    update_expression = {'$set': {'message_lang': 'en'}}
                    cls.db_controller.exec_query(query={'document': 'shouts',
                                                        'command': 'update',
                                                        'data': (filter_expression,
                                                                 update_expression,)})
                    bulk_update_setter = {'message_text': translation,
                                          'message_lang': 'en'}
                else:
                    bulk_update_setter = {f'translations.{shout_data["lang"]}': translation}
                # TODO: make a convenience wrapper to make bulk insertion easier to follow
                bulk_update.append(UpdateOne({'_id': shout_id},
                                             {'$set': bulk_update_setter}))
            if len(bulk_update) > 0:
                cls.db_controller.exec_query(query=MongoQuery(command=MongoCommands.BULK_WRITE,
                                                              document=MongoDocuments.SHOUTS,
                                                              data=bulk_update))
        return updated_shouts

    @classmethod
    def get_user_preferences(cls, user_id, create_if_not_exists: bool = False):
        """ Gets preferences of specified user """
        prefs = {}
        if user_id:
            prefs = cls.db_controller.exec_query(MongoQuery(command=MongoCommands.FIND_ONE,
                                                            document=MongoDocuments.USER_PREFERENCES,
                                                            filters=MongoFilter('_id', user_id)))
            if not prefs and create_if_not_exists:
                prefs = {
                    '_id': user_id,
                    'tts': {},
                    'chat_language_mapping': {}
                }
                cls.db_controller.exec_query(MongoQuery(command=MongoCommands.INSERT_ONE,
                                                        document=MongoDocuments.USER_PREFERENCES,
                                                        data=prefs))
        else:
            LOG.warning('user_id is None')
        return prefs

    @classmethod
    def save_tts_response(cls, shout_id, audio_data: str, lang: str = 'en', gender: str = 'female') -> bool:
        """
            Saves TTS Response under corresponding shout id

            :param shout_id: message id to consider
            :param audio_data: base64 encoded audio data received
            :param lang: language of speech (defaults to English)
            :param gender: language gender (defaults to female)

            :return bool if saving was successful
        """
        from chat_server.server_config import sftp_connector

        audio_file_name = f'{shout_id}_{lang}_{gender}.wav'
        filter_expression = {'_id': shout_id}
        try:
            sftp_connector.put_file_object(file_object=audio_data, save_to=f'audio/{audio_file_name}')
            cls.db_controller.exec_query(query=MongoQuery(command=MongoCommands.UPDATE,
                                                          document=MongoDocuments.SHOUTS,
                                                          filters=filter_expression,
                                                          data={f'audio.{lang}.{gender}': audio_file_name},
                                                          data_action='set'))
            operation_success = True
        except Exception as ex:
            LOG.error(f'Failed to save TTS response to db - {ex}')
            operation_success = False
        return operation_success

    @classmethod
    def save_stt_response(cls, shout_id, message_text: str, lang: str = 'en'):
        """
            Saves STT Response under corresponding shout id

            :param shout_id: message id to consider
            :param message_text: STT result transcript
            :param lang: language of speech (defaults to English)
        """
        filter_expression = {'_id': shout_id}
        try:
            cls.db_controller.exec_query(query=MongoQuery(command=MongoCommands.UPDATE,
                                                          document=MongoDocuments.SHOUTS,
                                                          filters=filter_expression,
                                                          data={f'transcripts.{lang}': message_text},
                                                          data_action='set'))
        except Exception as ex:
            LOG.error(f'Failed to save STT response to db - {ex}')

    @classmethod
    def fetch_audio_data_from_message(cls, message_id: str) -> str:
        """
            Fetches audio data from message if any
            :param message_id: message id to fetch
        """
        shout_data = cls.fetch_shouts(shout_ids=[message_id])
        if not shout_data:
            LOG.warning('Requested shout does not exist')
        elif shout_data[0].get('is_audio') != '1':
            LOG.warning('Failed to fetch audio data from non-audio message')
        else:
            from chat_server.server_config import sftp_connector
            file_location = f'audio/{shout_data[0]["message_text"]}'
            LOG.info(f'Fetching existing file from: {file_location}')
            fo = sftp_connector.get_file_object(file_location)
            if fo.getbuffer().nbytes > 0:
                return buffer_to_base64(fo)
            else:
                LOG.error(f'Empty buffer received while fetching audio of message id = {message_id}')
            return ''
