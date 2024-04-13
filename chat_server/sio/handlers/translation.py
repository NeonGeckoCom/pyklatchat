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

from cachetools import LRUCache

from utils.common import generate_uuid, deep_merge
from utils.database_utils.mongo_utils.queries import mongo_queries
from utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI
from utils.logging_utils import LOG
from ..server import sio
from ...server_utils.cache_utils import CacheFactory


@sio.event
# @login_required
async def request_translate(sid, data):
    """
    Handles requesting for cid translation
    :param sid: client session id
    :param data: mapping of cid to desired translation language
    """
    if not data:
        LOG.warning("Missing request translate data, skipping...")
    else:
        input_type = data.get("inputType", "incoming")

        populated_translations, missing_translations = mongo_queries.get_translations(
            translation_mapping=data.get("chat_mapping", {})
        )
        if populated_translations and not missing_translations:
            await sio.emit(
                "translation_response",
                data={"translations": populated_translations, "input_type": input_type},
                to=sid,
            )
        else:
            LOG.info(
                "Not every translation is contained in db, sending out request to Neon"
            )
            request_id = generate_uuid()
            caching_instance = {
                "translations": populated_translations,
                "sid": sid,
                "input_type": input_type,
            }
            CacheFactory.get("translation_cache", cache_type=LRUCache)[
                request_id
            ] = caching_instance
            await sio.emit(
                "request_neon_translations",
                data={"request_id": request_id, "data": missing_translations},
            )


@sio.event
async def get_neon_translations(sid, data):
    """
    Handles received translations from Neon Translation Service
    :param sid: client session id
    :param data: received translations data
    Example of translations data:
    ```
        data = {
                'request_id': (emitted request id),
                'translations':(dictionary containing mapping of shout id to translations)
               }
    ```
    """
    request_id = data.get("request_id")
    if not request_id:
        LOG.error('Missing "request id" in response dict')
    else:
        try:
            cached_data = CacheFactory.get("translation_cache").get(key=request_id)
            if not cached_data:
                LOG.warning("Failed to get matching cached data")
                return
            sid = cached_data.get("sid")
            input_type = cached_data.get("input_type")
            updated_shouts = MongoDocumentsAPI.SHOUTS.save_translations(
                translation_mapping=data.get("translations", {})
            )
            populated_translations = deep_merge(
                data.get("translations", {}), cached_data.get("translations", {})
            )
            await sio.emit(
                "translation_response",
                data={"translations": populated_translations, "input_type": input_type},
                to=sid,
            )
            if updated_shouts:
                send_dict = {
                    "input_type": input_type,
                    "translations": updated_shouts,
                }
                await sio.emit("updated_shouts", data=send_dict, skip_sid=[sid])
        except KeyError as err:
            LOG.error(
                f"No translation cache detected under request_id={request_id} (err={err})"
            )
