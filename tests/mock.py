from neon_mq_connector.connector import MQConnector


class MQConnectorChild(MQConnector):

    def __init__(self, config: dict = None, service_name: str = 'test'):
        super().__init__(config=config, service_name=service_name)
