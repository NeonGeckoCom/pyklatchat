import os
from io import BytesIO

import aiofiles
from fastapi import UploadFile, HTTPException
from neon_utils import LOG
from starlette import status
from starlette.responses import FileResponse, StreamingResponse

from chat_server.server_config import app_config, sftp_connector
from chat_server.server_utils.enums import DataSources
from utils.common import generate_uuid
from utils.http_utils import respond


def get_file_response(filename, location_prefix: str = "", media_type: str = None,
                      data_source: DataSources = DataSources.SFTP) -> FileResponse:
    """
        Gets starlette file response based on provided location

        :param location_prefix: subdirectory for file to get
        :param filename: name of the file to get
        :param media_type: type of file to send
        :param data_source: source of the data from DataSources

        :returns FileResponse in case file is present under specified location
    """
    # TODO: potentially support different ways to access files (e.g. local, S3, remote server, etc..)
    LOG.debug(f'Getting file based on filename: {filename}, media type: {media_type}')
    if data_source == DataSources.SFTP:
        sftp_data = sftp_connector.get_file_object(get_from=f'{location_prefix}/{filename}')
        file_response_args = dict(content=sftp_data,)
        response_class = StreamingResponse
    elif data_source == DataSources.LOCAL:
        path = os.path.join(app_config['FILE_STORING_LOCATION'], location_prefix, filename)
        LOG.debug(f'path: {path}')
        if os.path.exists(os.path.expanduser(path)):
            file_response_args = dict(path=path,
                                      filename=filename)
        else:
            LOG.error(f'{path} not found')
            return respond("File not found", 404)
        response_class = FileResponse
    else:
        LOG.error(f'Data source does not exists - {data_source}')
        return respond("Unable to fetch relevant data source", 403)
    if media_type:
        file_response_args['media_type'] = media_type
    return response_class(**file_response_args)


async def save_file(file: UploadFile, location_prefix: str = '',
                    data_source: DataSources = DataSources.SFTP) -> str:
    """
        Saves file in the file system

        :param file: file to save
        :param location_prefix: subdirectory for file to get
        :param data_source: source of the data from DataSources

        :returns generated location for the provided file
    """
    new_name = f'{generate_uuid(length=12)}.{file.filename.split(".")[-1]}'
    if data_source == DataSources.LOCAL:
        storing_path = os.path.expanduser(os.path.join(app_config['FILE_STORING_LOCATION'], location_prefix))
        os.makedirs(storing_path, exist_ok=True)
        async with aiofiles.open(os.path.join(storing_path, new_name), 'wb') as out_file:
            content = file.file.read()  # async read
            await out_file.write(content)
    elif data_source == DataSources.SFTP:
        content = BytesIO(file.file.read())
        try:
            sftp_connector.put_file_object(file_object=content, save_to=f'{location_prefix}/{new_name}')
        except Exception as ex:
            LOG.error(f'failed to save file: {file.filename}- {ex}')
            return respond('Failed to save attachment due to unexpected error', 422)
    else:
        LOG.error(f'Data source does not exists - {data_source}')
        return respond(f"Unable to fetch relevant data source", 403)
    return new_name
