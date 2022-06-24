import copy

import requests

from neon_utils import LOG


class LanguageSettings:
    """ Language Settings controller"""

    __supported_languages__ = {}

    __default_languages__ = {
        'en': dict(name='English', icon='us'),
        'es': dict(name='Español', icon='es'),
    }

    __code_to_icon_mapping__ = {
        'en': 'us',
        'hi': 'in',
        'zh': 'cn',
        'cs': 'cz',
        'el': 'gr',
        'ja': 'jp',
        'ko': 'kr',
        'fa': 'ir',
        'uk': 'ua',
        'ar': 'sa',
        'da': 'dk',
        'he': 'il',
        'vi': 'vn',
        'ga': 'ie'
    }

    __excluded_language_codes__ = ['ru', 'eo']

    __default_libre_url__ = 'https://libretranslate.com/'

    @classmethod
    def init_supported_languages(cls):
        """ Inits supported languages from system configuration"""
        from chat_server.server_config import app_config

        for url in {app_config.get('LIBRE_TRANSLATE_URL', cls.__default_libre_url__), cls.__default_libre_url__}:
            try:
                res = requests.get(f'{url}/languages')
                if res.ok:
                    for item in res.json():
                        if item['code'] not in cls.__excluded_language_codes__:
                            cls.__supported_languages__[item['code']] = {
                                'name': item['name'],
                                'icon': cls.__code_to_icon_mapping__.get(item['code'], item['code'])
                            }
                    return 0
            except Exception as ex:
                LOG.error(f'Failed to get translations under URL - {url} (ex={ex})')
        return -1

    @classmethod
    def get(cls, lang) -> dict:
        """ Gets properties based on provided language code"""
        if not cls.__supported_languages__:
            status = cls.init_supported_languages()
            if status == -1:
                LOG.warning('Rollback to default languages')
                return cls.__default_languages__.get(lang, {})
        return cls.__supported_languages__.get(lang, {})

    @classmethod
    def list(cls) -> dict:
        """ Lists supported languages """
        if not cls.__supported_languages__:
            status = cls.init_supported_languages()
            if status == -1:
                LOG.warning('Rollback to default languages')
                return copy.deepcopy(cls.__supported_languages__)
        return copy.deepcopy(cls.__supported_languages__)
