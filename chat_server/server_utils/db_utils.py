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

from typing import List, Tuple

from bson import ObjectId
from neon_utils import LOG
from pymongo import UpdateOne

from chat_server.constants.users import UserPatterns
from chat_server.server_utils.factory_utils import Singleton
from chat_server.server_utils.user_utils import create_from_pattern
from utils.common import buffer_to_base64


class DbUtils(metaclass=Singleton):
    """ Singleton DB Utils class for convenience"""

    db_controller = None

    @classmethod
    def init(cls, db_controller):
        """ Inits Singleton with specified database controller """
        cls.db_controller = db_controller

    @classmethod
    def get_conversation_data(cls, search_str):
        """
            Gets matching conversation data
            :param search_str: search string to lookup
        """
        or_expression = [{'conversation_name': search_str}]
        if ObjectId.is_valid(search_str):
            search_str = ObjectId(search_str)
        or_expression.append({'_id': search_str})

        conversation_data = cls.db_controller.exec_query(query={'command': 'find_one',
                                                                'document': 'chats',
                                                                'data': {"$or": or_expression}})
        if not conversation_data:
            return f"Unable to get a chat by string: {search_str}", 404
        conversation_data['_id'] = str(conversation_data['_id'])
        return conversation_data, 200

    @classmethod
    def fetch_shout_data(cls, conversation_data: dict, start_idx: int = 0, limit: int = 100,
                         fetch_senders: bool = True, start_message_id: str = None):
        """
            Fetches shout data out of conversation data

            :param conversation_data: input conversation data
            :param start_idx: message index to start from (sorted by recency)
            :param limit: number of shouts to fetch
            :param fetch_senders: to fetch shout senders data
            :param start_message_id: message id to start from
        """
        if conversation_data.get('chat_flow', None):
            if start_message_id:
                try:
                    start_idx = len(conversation_data["chat_flow"]) - \
                                conversation_data["chat_flow"].index(start_message_id)
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
    def fetch_shouts(cls, shout_ids: List[str] = None, fetch_senders: bool = True) -> List[dict]:
        """
            Fetches shout data from provided shouts list
            :param shout_ids: list of shout ids to fetch
            :param fetch_senders: to fetch shout senders data

            :returns Data from requested shout ids along with matching user data
        """
        shouts = cls.db_controller.exec_query(query={'document': 'shouts',
                                                     'command': 'find',
                                                     'data': {'_id': {'$in': list(set(shout_ids))}}})
        shouts = list(shouts)
        result = list()

        if fetch_senders:
            user_ids = list(set([shout['user_id'] for shout in shouts]))

            users_from_shouts = cls.db_controller.exec_query(query={'document': 'users',
                                                                    'command': 'find',
                                                                    'data': {'_id': {'$in': user_ids}}})

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
        else:
            result = shouts
        return result

    @classmethod
    def get_translations(cls, translation_mapping: dict, user_id=None) -> Tuple[dict, dict]:
        """
            Gets translation from db based on provided mapping

            :param translation_mapping: mapping of cid to desired translation language
            :param user_id: id of the initiator user

            :return translations fetched from db
        """
        populated_translations = {}
        missing_translations = {}
        bulk_update_preferences = []
        prefs = cls.get_user_preferences(user_id=user_id, create_if_not_exists=True)
        if not prefs:
            LOG.warning('No preferences fetched, user data will not be updated')
        for cid, cid_data in translation_mapping.items():
            lang = cid_data.get('lang', 'en')
            if prefs:
                bulk_update_preferences.append(UpdateOne({'_id': user_id},
                                                         {'$set': {f'chat_languages.{cid}': lang}}))
            conversation_data, status_code = cls.get_conversation_data(search_str=cid)
            if status_code != 200:
                LOG.error(f'Failed to fetch conversation data - {conversation_data} (status={status_code})')
                continue
            shout_data = cls.fetch_shout_data(conversation_data=conversation_data, fetch_senders=False)
            for shout in shout_data:
                message_text = shout.get('message_text')
                if lang == 'en':
                    shout_text = message_text
                else:
                    shout_text = shout.get('translations', {}).get(lang)
                if shout_text:
                    populated_translations.setdefault(cid, {}).setdefault('shouts', {})[shout['_id']] = shout_text
                elif message_text:
                    missing_translations.setdefault(cid, {}).setdefault('shouts', {})[shout['_id']] = message_text
            if missing_translations.get(cid):
                missing_translations[cid]['lang'] = lang
        if len(bulk_update_preferences) > 0:
            cls.db_controller.exec_query(query=dict(document='user_preferences',
                                                    command='bulk_write',
                                                    data=bulk_update_preferences))
        return populated_translations, missing_translations

    @classmethod
    def save_translations(cls, translation_mapping: dict) -> None:
        """
            Saves translations in DB
            :param translation_mapping: mapping of cid to desired translation language
        """
        for cid, shout_data in translation_mapping.items():
            translations = shout_data.get('shouts', {})
            if shout_data.get('lang', 'en') != 'en':
                bulk_update = []
                shouts = cls.db_controller.exec_query(query={'document': 'shouts',
                                                             'command': 'find',
                                                             'data': {'_id': {'$in': list(translations)}}})
                shouts = list(shouts)
                for shout_id, translation in translations.items():
                    matching_instance = None
                    for shout in shouts:
                        if shout['_id'] == shout_id:
                            matching_instance = shout
                            break
                    if not matching_instance.get('translations'):
                        filter_expression = {'_id': shout_id}
                        update_expression = {'$set': {'translations': {}}}
                        cls.db_controller.exec_query(query={'document': 'shouts',
                                                            'command': 'update',
                                                            'data': (filter_expression,
                                                                     update_expression,)})
                    bulk_update.append(UpdateOne({'_id': shout_id},
                                                 {'$set': {f'translations.{shout_data["lang"]}': translation}}))
                if len(bulk_update) > 0:
                    cls.db_controller.exec_query(query=dict(document='shouts',
                                                            command='bulk_write',
                                                            data=bulk_update))
            else:
                LOG.info('Apply translations skipped -> lang=en')

    @classmethod
    def get_user_preferences(cls, user_id, create_if_not_exists: bool = False):
        """ Gets preferences of specified user """
        prefs = {}
        if user_id:
            prefs = cls.db_controller.exec_query(query={'document': 'user_preferences',
                                                        'command': 'find_one',
                                                        'data': {'_id': user_id}}) or {}
            if not prefs and create_if_not_exists:
                prefs = {
                    '_id': user_id,
                    'tts': {},
                    'chat_languages': {}
                }
                cls.db_controller.exec_query(query=dict(document='user_preferences',
                                                        command='insert_one', data=prefs))
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
        update_expression = {'$set': {f'audio.{lang}.{gender}': audio_file_name}}
        try:
            sftp_connector.put_file_object(file_object=audio_data, save_to=f'audio/{audio_file_name}')
            cls.db_controller.exec_query(query={'document': 'shouts',
                                                'command': 'update',
                                                'data': (filter_expression,
                                                         update_expression,)})
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
        update_expression = {'$set': {f'transcripts.{lang}': message_text}}
        try:
            cls.db_controller.exec_query(query={'document': 'shouts',
                                                'command': 'update',
                                                'data': (filter_expression,
                                                         update_expression,)})
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
