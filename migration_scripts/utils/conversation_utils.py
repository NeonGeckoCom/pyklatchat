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

import re
import uuid
from typing import List, Tuple


from pyklatchat_utils.database_utils.mongo_utils.user_utils import get_existing_nicks_to_id
from neon_utils.logger import LOG


def index_nicks(mongo_controller, received_nicks: List[str]) -> Tuple[dict, List[str]]:
    """
    Assigns unique id to each nick that is not present in new db

    :param mongo_controller: controller to active mongo collection
    :param received_nicks: received nicks from mysql controller
    """

    # Excluding existing nicks from loop
    nicks_mapping = get_existing_nicks_to_id(mongo_controller)

    nicks_to_consider = list(set(received_nicks) - set(list(nicks_mapping)))

    # Generating UUID for each nick that is not present in new db
    for nick in nicks_to_consider:
        nicks_mapping[nick] = uuid.uuid4().hex

    LOG.info(f"Created nicks mapping for {len(list(nicks_mapping))} records")

    return nicks_mapping, nicks_to_consider


def clean_conversation_name(conversation_title: str):
    """
    Cleans up conversation names excluding all the legacy special chars

    :param conversation_title: Conversation title to clean
    """
    regex = re.search("-\[(.*?)\](.*)$", conversation_title)
    if regex is not None:
        result = regex.group()
        clean_title = conversation_title.split(result)[0]
        return clean_title

    regex = re.search("^auto-create (.*) - (.*)-", conversation_title)
    if regex is not None:
        result = regex.group()
        clean_title = conversation_title.split(result)[1]
        return clean_title

    clean_title = conversation_title
    return clean_title
