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
from typing import List, Dict, Tuple

from pymongo import ReplaceOne

from migration_scripts.utils.conversation_utils import (
    clean_conversation_name,
    index_nicks,
)
from klatchat_utils.logging_utils import LOG


def migrate_conversations(
    old_db_controller, new_db_controller, time_since: int = 1577829600
) -> Tuple[List[str], Dict[str, str], List[str]]:
    """
    Migrating conversations from old database to new one
    :param old_db_controller: old database connector
    :param new_db_controller: new database connector
    :param time_since: timestamp for conversation activity
    """
    LOG.info(f"Starting chats migration")

    get_cids_query = f"""
                          select * from shoutbox_conversations where updated>{time_since};
                      """

    result = old_db_controller.exec_query(get_cids_query)

    result_cids = [str(r["cid"]) for r in result]

    existing_cids = list(
        new_db_controller.exec_query(
            query=dict(
                document="chats", command="find", data={"_id": {"$in": result_cids}}
            )
        )
    )

    existing_cids = [r["_id"] for r in existing_cids]

    all_cids_in_scope = list(set(existing_cids + result_cids))

    LOG.info(f"Found {len(existing_cids)} existing cids")

    if existing_cids:
        result = list(filter(lambda x: str(x["cid"]) not in existing_cids, result))

    LOG.info(f"Received {len(result)} new cids")

    received_nicks = [
        record["creator"] for record in result if record["creator"] is not None
    ]

    nicknames_mapping, nicks_to_consider = index_nicks(
        mongo_controller=new_db_controller, received_nicks=received_nicks
    )

    LOG.debug(f"Records to process: {len(result)}")

    formed_result = [
        ReplaceOne(
            {"_id": str(record["cid"])},
            {
                "_id": str(record["cid"]),
                "is_private": int(record["private"]) == 1,
                "domain": record["domain"],
                "image": record["image_url"],
                "password": record["password"],
                "conversation_name": f"{clean_conversation_name(record['title'])}_{record['cid']}",
                "chat_flow": [],
                "creator": nicknames_mapping.get(record["creator"], record["creator"]),
                "created_on": int(record["created"]),
            },
            upsert=True,
        )
        for record in result
    ]

    if len(formed_result) > 0:
        new_db_controller.exec_query(
            query=dict(document="chats", command="bulk_write", data=formed_result)
        )
    else:
        LOG.info("All chats are already in new deb, skipping chat migration")

    return all_cids_in_scope, nicknames_mapping, nicks_to_consider
