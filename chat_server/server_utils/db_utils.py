from typing import List, Tuple

from bson import ObjectId
from cachetools import cached, TTLCache
from neon_utils import LOG
from pymongo import UpdateOne

from chat_server.constants.users import UserPatterns
from chat_server.server_utils.factory_utils import Singleton
from chat_server.server_utils.user_utils import create_from_pattern


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
                         fetch_senders: bool = True):
        """
            Fetches shout data out of conversation data

            :param conversation_data: input conversation data
            :param start_idx: message index to start from (sorted by recency)
            :param limit: number of shouts to fetch
            :param fetch_senders: to fetch shout senders data
        """
        if conversation_data.get('chat_flow', None):
            if start_idx == 0:
                conversation_data['chat_flow'] = conversation_data['chat_flow'][start_idx - limit:]
            else:
                conversation_data['chat_flow'] = conversation_data['chat_flow'][start_idx - limit:
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
    def get_user_preferences(cls, user_id):
        """ Gets preferences of specified user """
        return cls.db_controller.exec_query(query={'document': 'user_preferences',
                                                   'command': 'find_one',
                                                   'data': {'_id': user_id}}) or {}
