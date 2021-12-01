docker container stop chat-server
docker run --rm -d --name chat-server --net=host neon/chat_server:latest
docker container stop chat-client
docker run --rm -d --name chat-client --net=host neon/chat_client:latest
docker container stop klatchat-observer
docker run --rm -d --name klatchat-observer --net=host neon/klatchat_observer:latest
