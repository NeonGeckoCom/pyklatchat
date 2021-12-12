# Remove all untagged images
docker rmi $(docker images --filter "dangling=true" -q --no-trunc) --force
# Remove all containers
docker rm -f $(docker ps -a -q)
# Remove dangling cache
docker builder prune
