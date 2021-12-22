from collections import Iterable


def iterable_to_sql_array(i: Iterable) -> str:
    """Converts python iterable to SQL array"""
    return f'({str(list(i))[1:-1]})'


def sql_arr_is_null(sql_arr: str):
    """Checks if SQL array is null"""
    return sql_arr and sql_arr == '()'
