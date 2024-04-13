#!/bin/bash
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

export DOCKER_BUILDKIT=1

while getopts v: opts; do
   case ${opts} in
      v) version=${OPTARG} ;;
   esac
done

readonly VERSION=${version:-dev}

echo "Build version = $VERSION";

cd ..
echo "Building Chat Observer"
cp config.py services/klatchat_observer
cp config.json services/klatchat_observer
cp version.py services/klatchat_observer
cp -R utils services/klatchat_observer
cp requirements/requirements.txt services/klatchat_observer
cd services/klatchat_observer

# replacing base image version
sed -i "1 s|.*|FROM ghcr.io/neongeckocom/pyklatchat_base:${VERSION}|" ../../dockerfiles/Dockerfile.observer

docker build -f ../../dockerfiles/Dockerfile.observer -t ghcr.io/neongeckocom/klatchat_observer:$VERSION .
cd ../../
echo "Building Chat Client"
cp requirements/requirements.txt chat_client
cp -R utils chat_client
cp config.py chat_client
cp version.py chat_server
cp uvicorn_logging.yaml chat_client
cd chat_client

# replacing base image version
sed -i "1 s|.*|FROM ghcr.io/neongeckocom/pyklatchat_base:${VERSION}|" ../dockerfiles/Dockerfile.client

docker build -f ../dockerfiles/Dockerfile.client -t ghcr.io/neongeckocom/chat_client:$VERSION .
cd ..
echo "Building Chat Server"
cp requirements/requirements.txt chat_server
cp config.py chat_server
cp version.py chat_server
cp -R utils chat_server
cp uvicorn_logging.yaml chat_server
cd chat_server

# replacing base image version
sed -i "1 s|.*|FROM ghcr.io/neongeckocom/pyklatchat_base:${VERSION}|" ../dockerfiles/Dockerfile.server
docker build -f ../dockerfiles/Dockerfile.server -t ghcr.io/neongeckocom/chat_server:$VERSION .

cd ../scripts
