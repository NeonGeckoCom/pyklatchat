import os

import aiofiles
from fastapi import UploadFile
from neon_utils import LOG
from starlette.responses import FileResponse

from chat_server.server_config import app_config


def get_file_response(filename, location_prefix: str = "", media_type: str = None) -> FileResponse:
    """
        Gets starlette file response based on provided location

        :param location_prefix: subdirectory for file to get
        :param filename: name of the file to get
        :param media_type: type of file to send

        :returns FileResponse in case file is present under specified location
    """
    # TODO: potentially support different ways to access files (e.g. local, S3, remote server, etc..)
    LOG.debug(f'Getting file based on filename: {filename}, media type: {media_type}')
    path = os.path.join(app_config['FILE_STORING_LOCATION'], location_prefix, filename)
    LOG.debug(f'path: {path}')
    if os.path.exists(os.path.expanduser(path)):
        file_response_args = dict(path=path,
                                  filename=filename)
        if media_type:
            file_response_args['media_type'] = media_type
        return FileResponse(**file_response_args)
    LOG.error(f'Unrecognized path: {path}')


async def save_file(file: UploadFile, location_prefix: str = ''):
    """
        Saves file in the file system

        :param file: file to save
        :param location_prefix: subdirectory for file to get
    """
    async with aiofiles.open(os.path.join(app_config['FILE_STORING_LOCATION'], location_prefix, file.filename), 'wb') as out_file:
        content = file.file.read()  # async read
        await out_file.write(content)
