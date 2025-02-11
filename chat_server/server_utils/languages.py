# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2025 Neongecko.com Inc.
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
import os

import requests
from bidict import bidict

from klatchat_utils.logging_utils import LOG
from chat_server.server_config import server_config


class LanguageSettings:
    """Language Settings controller"""

    __supported_languages__ = {}

    __default_languages__ = {
        "en": dict(name="English", icon="us"),
        "es": dict(name="Español", icon="es"),
    }

    __code_to_icon_mapping__ = {
        "en": "us",
        "hi": "in",
        "zh": "cn",
        "cs": "cz",
        "el": "gr",
        "ja": "jp",
        "ko": "kr",
        "fa": "ir",
        "uk": "ua",
        "ar": "sa",
        "da": "dk",
        "he": "il",
        "vi": "vn",
        "ga": "ie",
    }

    __included_language_codes = os.environ.get("INCLUDED_LANGUAGES", "")
    if __included_language_codes:
        __included_language_codes = __included_language_codes.split(",")

    __excluded_language_codes__ = ["ru", "eo"]

    __neon_language_mapping__ = bidict({"en": "en-us"})

    __default_libre_url__ = "https://libretranslate.com/"

    @classmethod
    def init_supported_languages(cls):
        """Inits supported languages from system configuration"""

        for url in {
            server_config.get("LIBRE_TRANSLATE_URL", cls.__default_libre_url__),
            cls.__default_libre_url__,
        }:
            try:
                res = requests.get(f"{url}/languages")
                if res.ok:
                    for item in res.json():
                        code = item["code"]
                        if code not in cls.__excluded_language_codes__ and (
                            not cls.__included_language_codes
                            or code in cls.__included_language_codes
                        ):
                            cls.__supported_languages__[code] = {
                                "name": item["name"],
                                "icon": cls.__code_to_icon_mapping__.get(code, code),
                            }
                    return 0
            except Exception as ex:
                LOG.error(f"Failed to get translations under URL - {url} (ex={ex})")
        return -1

    @classmethod
    def get(cls, lang) -> dict:
        """Gets properties based on provided language code"""
        if not cls.__supported_languages__:
            status = cls.init_supported_languages()
            if status == -1:
                LOG.warning("Rollback to default languages")
                return cls.__default_languages__.get(lang, {})
        return cls.__supported_languages__.get(lang, {})

    @classmethod
    def list(cls) -> dict:
        """Lists supported languages"""
        if not cls.__supported_languages__:
            status = cls.init_supported_languages()
            if status == -1:
                LOG.warning("Rollback to default languages")
                return copy.deepcopy(cls.__default_languages__)
        return copy.deepcopy(cls.__supported_languages__)

    @classmethod
    def to_neon_lang(cls, lang):
        """Maps provided language code to the Neon-supported language code"""
        return cls.__neon_language_mapping__.get(lang, lang)

    @classmethod
    def to_system_lang(cls, neon_lang):
        """Maps provided Neon-supported language code to system language code"""
        return cls.__neon_language_mapping__.inverse.get(neon_lang, neon_lang)
