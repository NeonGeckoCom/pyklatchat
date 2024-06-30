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

from typing import Type
from cachetools import Cache


# TODO: consider storing cached values in Redis (Kirill)


class CacheFactory:
    """Cache creation factory"""

    __active_caches = {}

    @classmethod
    def get(cls, name: str, cache_type: Type[Cache] = None, **kwargs) -> Cache:
        """
        Get cache instance based on name and type

        :param name: name of the cache to retrieve
        :param cache_type: type of the cache to create if not found
        :param kwargs: keyword args to provide along with cache instance creation
        """
        if not cls.__active_caches.get(name):
            if cache_type:
                kwargs.setdefault("maxsize", 124)
                cls.__active_caches[name] = cache_type(**kwargs)
            else:
                raise KeyError(f"Missing cache instance under {name}")
        return cls.__active_caches[name]


class SubmindsState:
    items = {}

    @classmethod
    def update(cls, data: dict):
        cls.items["proctored_conversations"] = cls._get_proctored_conversations(data)

    @classmethod
    def _get_proctored_conversations(cls, data):
        proctored_conversations = []
        for cid, subminds in data.get("subminds_per_cid", {}).items():
            for submind in subminds:
                if (
                    cls._is_proctor(submind["submind_id"])
                    and submind["status"] != "banned"
                ):
                    proctored_conversations.append(cid)
                    break
        return proctored_conversations

    @classmethod
    def _is_proctor(cls, submind_id: str) -> bool:
        return submind_id.startswith("proctor")

    @classmethod
    def is_proctored_conversation(cls, cid: str) -> bool:
        return cid in cls.items.get("proctored_conversations", [])
