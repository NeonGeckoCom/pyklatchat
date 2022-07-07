export DOCKER_BUILDKIT=1

while getopts version: flag
do
    case "${flag}" in
        version) version=${OPTARG};;
    esac
done

readonly VERSION=${version:-dev}

echo 'Build version = $VERSION';

cd ..
echo "Building Chat Observer"
cp config.py services/klatchat_observer
cp config.json services/klatchat_observer
cp version.py services/klatchat_observer
cp -R utils services/klatchat_observer
cp requirements/requirements.txt services/klatchat_observer
cd services/klatchat_observer

# replacing base image version
sed -i "1 s|.*|FROM ghcr.io/neongeckocom/pyklatchat_base:${sourceRegistryUrl}|" ../../dockerfiles/Dockerfile.observer

docker build -f ../../dockerfiles/Dockerfile.observer -t ghcr.io/neongeckocom/klatchat_observer:$VERSION .
cd ../../
echo "Building Chat Client"
cp requirements/requirements.txt chat_client
cp -R utils chat_client
cp config.py chat_client
cp uvicorn_logging.yaml chat_client
cd chat_client

# replacing base image version
sed -i "1 s|.*|FROM ghcr.io/neongeckocom/pyklatchat_base:${VERSION}|" ../dockerfiles/Dockerfile.client

docker build -f ../dockerfiles/Dockerfile.client -t ghcr.io/neongeckocom/chat_client:$VERSION .
cd ..
echo "Building Chat Server"
cp requirements/requirements.txt chat_server
cp config.py chat_server
cp -R utils chat_server
cp uvicorn_logging.yaml chat_server
cd chat_server

# replacing base image version
sed -i "1 s|.*|FROM ghcr.io/neongeckocom/pyklatchat_base:${sourceRegistryUrl}|" ../dockerfiles/Dockerfile.server
docker build -f ../dockerfiles/Dockerfile.server -t ghcr.io/neongeckocom/chat_server:$VERSION .

cd ../scripts
