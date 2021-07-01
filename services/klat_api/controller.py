from connector import MQConnector


class KlatConnector(MQConnector):
    def __init__(self, config: dict):
        super().__init__(config)

