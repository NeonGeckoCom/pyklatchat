cd ..
echo "Building Base Image"
while getopts version: flag
do
    case "${flag}" in
        version) version=${OPTARG};;
    esac
done

readonly VERSION=${version:-dev}

echo 'Build version = $VERSION';

docker build -f /dockerfiles/Dockerfile.base -t ghcr.io/neongeckocom/pyklatchat_base:$VERSION .
echo "Base Image Building Completed Successfully"
cd ../scripts
