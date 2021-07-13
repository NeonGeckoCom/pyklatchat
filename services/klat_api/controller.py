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

from mycroft_bus_client import MessageBusClient, Message
from neon_utils import LOG
from neon_mq_connector.connector import MQConnector


class NeonMQConnector(MQConnector):
    """Adapter for establishing connection between Neon MessageBus and Klatchat Message Broker"""
    def __init__(self, config: dict, service_name: str):
        """Additionally accepts message bus connection properties"""
        super().__init__(config, service_name)

        self.message_bus = MessageBusClient(host=self.config['MESSAGEBUS'].get('host', '0.0.0.0'),
                                            port=int(self.config['MESSAGEBUS'].get('port', '8181')),
                                            route=self.config['MESSAGEBUS'].get('route', '/klat'),
                                            ssl=self.config['MESSAGEBUS'].get('ssl', False))

    @staticmethod
    def print_utterance(message):
        """Default method for testing message bus channel correctness"""
        LOG.debug('Mycroft said "{}"'.format(message.data.get('utterance')))

    def _setup_bus_listeners(self):
        """
            Sets up neon message bus listeners according to agreed specifications
        """
        #  TODO: setup specification document

        self.message_bus.on('neon.get_profile', self.print_utterance)
        self.message_bus.on('neon.get_klat_data', self.print_utterance)
        self.message_bus.on('neon.ai_response', self.print_utterance)
        self.message_bus.on('klat.audio_source_update', self.print_utterance)
        self.message_bus.on('klat.audio_too_quiet', self.print_utterance)

    def run(self):
        self.run_consumers()
        self._setup_bus_listeners()
