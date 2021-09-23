from neon_utils import LOG


def get_existing_nicks_to_id(mongo_controller) -> dict:
    """
        Gets existing nicknames to id mapping from provided mongo db

        :param mongo_controller: controller to active mongo collection

        :returns List of dict containing filtered items
    """
    retrieved_data = mongo_controller.exec_query(query=dict(document='users', command='find'))
    LOG.info(f'Retrieved {len(list(retrieved_data))} existing nicknames from new db')
    return {record['nick']: record['_id'] for record in retrieved_data}
