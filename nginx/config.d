upstream pyklatchat_client {
    server 127.0.0.1:8011;
    server 127.0.0.1:8012;
}

server {
    location / {
      proxy_pass http://pyklatchat_client;
    }
}