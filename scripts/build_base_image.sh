echo "Building Base Image"
while getopts v: opts; do
   case ${opts} in
      v) version=${OPTARG} ;;
   esac
done

readonly VERSION=${version:-dev}

echo "Build version = $VERSION";

cd ..

cp requirements/requirements.txt base

cd base

docker build -f ../dockerfiles/Dockerfile.base -t ghcr.io/neongeckocom/pyklatchat_base:$VERSION .

cd ../scripts
echo "Base Image Building Completed Successfully"
