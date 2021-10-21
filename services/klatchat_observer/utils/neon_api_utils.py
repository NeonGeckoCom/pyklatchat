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
from ..constants.neon_api_constants import NeonServices, neon_service_tokens


def resolve_neon_service(message_data: dict, bypass_threshold: float = 0.5) -> NeonServices:
    """
        Resolves desired neon service based on the data content from message

        :param message_data: dictionary containing data for message
        :param bypass_threshold: edge value to consider valid match

        :returns neon service from NeonServices
    """
    # TODO: parse message text into lexemes
    for neon_service, tokens in neon_service_tokens.items():
        match_percentage = len(set(list(message_data)) & set(tokens))/len(tokens)
        if match_percentage > bypass_threshold:
            return neon_service
    return NeonServices.WOLFRAM
