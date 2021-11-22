cd ..
echo "Building Chat Observer"
cp utils/common.py services/klatchat_observer/utils
cp requirements/requirements.txt services/klatchat_observer
cd services/klatchat_observer
docker build -f ../../dockerfiles/Dockerfile.observer -t neon/klatchat_observer:latest .
# echo "Building Chat Client"
# docker build -f dockerfiles/Dockerfile.client -t neon/chat_client:latest chat_client
# echo "Building Chat Server"
# docker build -f dockerfiles/Dockerfile.server -t neon/chat_server:latest chat_server
cd ../../scripts
