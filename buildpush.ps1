#Build commands
##Build every architecture needed
docker build --progress plain -t omadevs/clusterworker:arm32v5-0.0.11 --build-arg ARCH=arm32v5/ --secret src=myKEY.txt,id=myKEY .
docker build --progress plain -t omadevs/clusterworker:arm32v7-0.0.11 --build-arg ARCH=arm32v7/ --secret src=myKEY.txt,id=myKEY .
docker build --progress plain -t omadevs/clusterworker:amd64-0.0.11 --build-arg ARCH=amd64/ --secret src=myKEY.txt,id=myKEY .
##Push them
docker push omadevs/clusterworker:arm32v5-0.0.11
docker push omadevs/clusterworker:arm32v7-0.0.11
docker push omadevs/clusterworker:amd64-0.0.11
##Create multiarch manifest and push it
docker manifest create omadevs/clusterworker:0.0.11 --amend omadevs/clusterworker:arm32v5-0.0.11 --amend omadevs/clusterworker:arm32v7-0.0.11 --amend omadevs/clusterworker:amd64-0.0.11
docker manifest push omadevs/clusterworker:0.0.11

#Deploy commands
#sudo docker service create --name SERVICENAME --publish PORTEXPOSED:80/tcp --constraint node.role==ROLEHERE --replicas REPLICANUM --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock IMAGE
##phpmyadmin entrypoint
#-e PMA_HOST=192.168.1.200