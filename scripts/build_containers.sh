cd ..
echo "Building Chat Observer"
CP /utils/common.py /services/klatchat_observer/utils
CP /requirements/requirements.txt /services/klatchat_observer
docker build -f dockerfiles/Dockerfile.observer -t neon/klatchat_observer:0.0.2 services/klatchat_observer
echo "Building Chat Client"
docker build -f dockerfiles/Dockerfile.client -t neon/chat_client:0.0.2 chat_client
echo "Building Chat Server"
docker build -f dockerfiles/Dockerfile.server -t neon/chat_server:0.0.2 chat_server
cd scripts