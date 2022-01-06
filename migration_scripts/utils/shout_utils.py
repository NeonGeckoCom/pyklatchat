from typing import List


def prepare_nicks_for_sql(nicks: List[str]) -> list:
    """
        Prepares nicks to be used in SQL query

        :param nicks: list of nicks to be used
    """
    processed_nicks = nicks.copy()
    return [nick.replace("'", "") for nick in processed_nicks]
