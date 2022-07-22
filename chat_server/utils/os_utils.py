import os


def remove_if_exists(file_path):
    """ Removes file if exists"""
    try:
        os.remove(file_path)
    except OSError:
        pass
