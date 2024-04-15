# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2022 Neongecko.com Inc.
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# BSD-3 License
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
from io import BytesIO

import aiofiles
from fastapi import UploadFile, Request
from starlette.responses import FileResponse, StreamingResponse

from chat_server.server_config import server_config
from chat_server.server_utils.enums import DataSources
from utils.common import generate_uuid
from utils.http_utils import respond
from utils.logging_utils import LOG


class KlatAPIResponse:
    OK = respond("OK")
    BAD_REQUEST = respond("Bad Request")
    UNAUTHORIZED = respond("Unauthorized", status_code=401)
    FORBIDDEN = respond("Permission Denied", status_code=403)
    NOT_FOUND = respond("NOT_FOUND", status_code=404)
    INTERNAL_SERVER_ERROR = respond("INTERNAL_SERVER_ERROR", status_code=500)


def get_file_response(
    filename,
    location_prefix: str = "",
    media_type: str = None,
    data_source: DataSources = DataSources.SFTP,
) -> FileResponse:
    """
    Gets starlette file response based on provided location

    :param location_prefix: subdirectory for file to get
    :param filename: name of the file to get
    :param media_type: type of file to send
    :param data_source: source of the data from DataSources

    :returns FileResponse in case file is present under specified location
    """
    # TODO: potentially support different ways to access files (e.g. local, S3, remote server, etc..)
    LOG.debug(f"Getting file based on filename: {filename}, media type: {media_type}")
    if data_source == DataSources.SFTP:
        sftp_data = server_config.sftp_connector.get_file_object(
            get_from=f"{location_prefix}/{filename}"
        )
        file_response_args = dict(
            content=sftp_data,
        )
        response_class = StreamingResponse
    elif data_source == DataSources.LOCAL:
        path = os.path.join(
            server_config["FILE_STORING_LOCATION"], location_prefix, filename
        )
        LOG.debug(f"path: {path}")
        if os.path.exists(os.path.expanduser(path)):
            file_response_args = dict(path=path, filename=filename)
        else:
            LOG.error(f"{path} not found")
            return respond("File not found", 404)
        response_class = FileResponse
    else:
        LOG.error(f"Data source does not exists - {data_source}")
        return respond("Unable to fetch relevant data source", 403)
    if media_type:
        file_response_args["media_type"] = media_type
    return response_class(**file_response_args)


async def save_file(
    file: UploadFile,
    location_prefix: str = "",
    data_source: DataSources = DataSources.SFTP,
) -> str:
    """
    Saves file in the file system

    :param file: file to save
    :param location_prefix: subdirectory for file to get
    :param data_source: source of the data from DataSources

    :returns generated location for the provided file
    """
    new_name = f'{generate_uuid(length=12)}.{file.filename.split(".")[-1]}'
    if data_source == DataSources.LOCAL:
        storing_path = os.path.expanduser(
            os.path.join(server_config["FILE_STORING_LOCATION"], location_prefix)
        )
        os.makedirs(storing_path, exist_ok=True)
        async with aiofiles.open(
            os.path.join(storing_path, new_name), "wb"
        ) as out_file:
            content = file.file.read()  # async read
            await out_file.write(content)
    elif data_source == DataSources.SFTP:
        content = BytesIO(file.file.read())
        try:
            server_config.sftp_connector.put_file_object(
                file_object=content, save_to=f"{location_prefix}/{new_name}"
            )
        except Exception as ex:
            LOG.error(f"failed to save file: {file.filename}- {ex}")
            return respond("Failed to save attachment due to unexpected error", 422)
    else:
        LOG.error(f"Data source does not exists - {data_source}")
        return respond(f"Unable to fetch relevant data source", 403)
    return new_name


def get_request_path_string(request: Request) -> str:
    return f"[{request.method}] {request.url.path} "
