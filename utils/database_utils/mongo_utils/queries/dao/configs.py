from utils.database_utils.mongo_utils import MongoDocuments, MongoFilter
from utils.database_utils.mongo_utils.queries.dao.abc import MongoDocumentDAO
from utils.logging_utils import LOG


class ConfigsDAO(MongoDocumentDAO):
    @property
    def document(self):
        return MongoDocuments.CONFIGS

    def get_by_name(self, config_name: str, version: str = "default") -> dict:
        filters = [
            MongoFilter(key="name", value=config_name),
            MongoFilter(key="version", value=version),
        ]
        item = self.get_item(filters=filters)
        if item:
            return item.get("value")
        else:
            LOG.error(f"Failed to get config by {config_name = }, {version = }")
