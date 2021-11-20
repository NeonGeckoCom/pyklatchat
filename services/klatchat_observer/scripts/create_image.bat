cd ../../../
COPY "C:\Users\admin\PycharmProjects\pyklatchat\utils\common.py" "C:\Users\admin\PycharmProjects\pyklatchat\services\klatchat_observer\utils"
COPY "C:\Users\admin\PycharmProjects\pyklatchat\requirements\requirements.txt" "C:\Users\admin\PycharmProjects\pyklatchat\services\klatchat_observer"
cd services/klatchat_observer
docker build