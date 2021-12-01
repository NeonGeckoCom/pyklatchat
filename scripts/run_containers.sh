# docker run -d neon/klatchat_observer:latest --name klatchat-observer 
# docker run -d neon/chat_server:latest --name pyklatchat-server -p 8010:8000
docker run --rm -d --name chat-client --net=host -p 8001:8011 neon/chat_client:latest
