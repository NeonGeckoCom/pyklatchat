import itertools

from chat_server.server_utils.db_utils import DbUtils


class PopularityCounter:

    __DATA = None

    @classmethod
    def get_data(cls):
        if cls.__DATA is None:
            cls.__DATA = cls.init_data()
        return cls.__DATA

    @classmethod
    def init_data(cls):
        data = {'cid': {'popularity': 0, 'conversation_name': ''}}
        return data

    @classmethod
    def increment_cid_popularity(cls, cid):
        if cls.__DATA is None:
            cls.get_data()
        cls.__DATA.setdefault(cid, 0)
        cls.__DATA[cid] += 1

    @classmethod
    def get_first_items(cls, search_str, limit: int = 10):
        data = {k: v for k, v in cls.__DATA.items() if search_str.lower() in v['conversation_name'].lower()}
        return dict(itertools.islice(sorted(data.items(), key=lambda k, v: v['popularity']), limit))
