cd ..
echo "Building Chat Observer"
COPY "\utils\common.py" "\services\klatchat_observer\utils"
COPY "\requirements\requirements.txt" "\services\klatchat_observer"
docker build -f dockerfiles/Dockerfile.observer -t neon/klatchat_observer:latest services/klatchat_observer
echo "Building Chat Client"
docker build -f dockerfiles/Dockerfile.client -t neon/chat_client:latest chat_client
echo "Building Chat Server"
docker build -f dockerfiles/Dockerfile.server -t neon/chat_server:latest chat_server
cd scripts