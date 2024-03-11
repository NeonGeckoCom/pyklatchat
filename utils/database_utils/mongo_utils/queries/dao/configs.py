from chat_server.server_utils.exceptions import ItemNotFoundException
from utils.database_utils.mongo_utils import MongoDocuments, MongoFilter
from utils.database_utils.mongo_utils.queries.dao.abc import MongoDocumentDAO
from utils.logging_utils import LOG


class ConfigsDAO(MongoDocumentDAO):
    @property
    def document(self):
        return MongoDocuments.CONFIGS

    def get_by_name(self, config_name: str, version: str = "latest"):
        filters = [
            MongoFilter(key="name", value=config_name),
            MongoFilter(key="version", value=version),
        ]
        item = self.get_item(filters=filters)
        if item:
            return item.get("value")
        else:
            LOG.error(f"Failed to get config by {config_name = }, {version = }")
            raise ItemNotFoundException

    def update_by_name(self, config_name: str, data: dict, version: str = "latest"):
        filters = [
            MongoFilter(key="name", value=config_name),
            MongoFilter(key="version", value=version),
        ]
        return self.update_item(filters=filters, data={"value": data})
