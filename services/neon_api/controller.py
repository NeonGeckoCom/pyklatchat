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
import socket
import pika

from neon_utils import LOG
from neon_utils.socket_utils import get_packet_data
from neon_mq_connector.connector import MQConnector, ConsumerThread


class NeonAPIMQConnector(MQConnector):
    """Adapter for establishing connection between Neon API and MQ broker"""

    def __init__(self, config: dict, service_name: str):
        """
            Additionally accepts message bus connection properties

            :param config: dictionary containing configuration data, required body:
            {
                NEON_API_PROXY:{
                    HOST:(socket address),
                    PORT: (socket port)
                }
            }
            :param service_name: name of the service instance
        """
        super().__init__(config, service_name)

        self.vhost = '/neon_api'
        self.tcp_credentials = (self.config['NEON_API_PROXY']['HOST'],
                                int(self.config['NEON_API_PROXY']['PORT']))
        self.register_consumer(name='neon_api_consumer',
                               vhost=self.vhost,
                               queue='neon_api_input',
                               callback=self.handle_api_input,
                               on_error=self.default_error_handler,
                               auto_ack=False)

    def handle_api_input(self,
                         channel: pika.channel.Channel,
                         method: pika.spec.Basic.Return,
                         properties: pika.spec.BasicProperties,
                         body: bytes):
        """
            Handles input requests from MQ to Neon API

            :param channel: MQ channel object (pika.channel.Channel)
            :param method: MQ return method (pika.spec.Basic.Return)
            :param properties: MQ properties (pika.spec.BasicProperties)
            :param body: request body (bytes)

        """
        if body and isinstance(body, bytes):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(self.tcp_credentials)
                s.sendall(body)
                data = get_packet_data(socket=s, sequentially=False)
                # queue declare is idempotent, just making sure queue exists
                channel.queue_declare(queue='neon_api_output')

                channel.basic_publish(exchange='',
                                      routing_key='neon_api_output',
                                      body=data,
                                      properties=pika.BasicProperties(expiration='1000')
                                      )
        else:
            raise TypeError(f'Invalid body received, expected: bytes string; got: {type(body)}')

    def run(self):
        self.run_consumers()
