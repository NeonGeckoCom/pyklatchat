docker container stop chat-client-1
docker run --rm -d --name chat-client-1 --net=host -e PORT=8011 neon/chat_client:latest
docker container stop chat-client-2
docker run --rm -d --name chat-client-2 --net=host -e PORT=8012 neon/chat_client:latest
docker container stop chat-server
docker run --rm -d --name chat-server -e PORT=8010 -e HOST=0.0.0.0 -p 8010:8010 -v pyklatchat-static-media:/app/static neon/chat_server:latest
docker container stop klatchat-observer
docker run --rm -d --name klatchat-observer --net=host neon/klatchat_observer:latest
sudo nginx -s reload
