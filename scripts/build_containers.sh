cd ..
echo "Building Chat Observer"
cp utils/common.py services/klatchat_observer/utils
cp requirements/requirements.txt services/klatchat_observer
cd services/klatchat_observer
docker build -f ../../dockerfiles/Dockerfile.observer -t neon/klatchat_observer:latest .
cd ../../
echo "Building Chat Client"
cp requirements/requirements.txt chat_client
cp config.py chat_client
cd chat_client
docker build -f ../dockerfiles/Dockerfile.client -t neon/chat_client:latest chat_client
cd ../scripts
echo "Building Chat Server"
cp requirements/requirements.txt chat_server
cp config.py chat_server
cp -R utils chat_server
cd chat_server
docker build -f ../dockerfiles/Dockerfile.server -t neon/chat_server:latest chat_server
cd ../scripts
