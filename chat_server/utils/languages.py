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
import requests
from bidict import bidict

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

    __neon_language_mapping__ = bidict({
        'en': 'en-us'
    })

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

    @classmethod
    def to_neon_lang(cls, lang):
        """ Maps provided language code to the Neon-supported language code """
        return cls.__neon_language_mapping__.get(lang, lang)

    @classmethod
    def to_system_lang(cls, neon_lang):
        """ Maps provided Neon-supported language code to system language code """
        return cls.__neon_language_mapping__.inverse.get(neon_lang, neon_lang)
