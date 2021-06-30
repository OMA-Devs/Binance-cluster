#Build commands
##Build every architecture needed
docker build --progress plain -t omadevs/clusterworker:arm32v5-0.0.2 --build-arg ARCH=arm32v5/ --secret src=myKEY.txt,id=myKEY .
docker build --progress plain -t omadevs/clusterworker:arm32v7-0.0.2 --build-arg ARCH=arm32v7/ --secret src=myKEY.txt,id=myKEY .
docker build --progress plain -t omadevs/clusterworker:amd64-0.0.2 --build-arg ARCH=amd64/ --secret src=myKEY.txt,id=myKEY .
##Push them
docker push omadevs/clusterworker:arm32v5-0.0.2
docker push omadevs/clusterworker:arm32v7-0.0.2
docker push omadevs/clusterworker:amd64-0.0.2
##Create multiarch manifest and push it
docker manifest create omadevs/clusterworker:0.0.2 --amend omadevs/clusterworker:arm32v5-0.0.1 --amend omadevs/clusterworker:arm32v7-0.0.1 --amend omadevs/clusterworker:amd64-0.0.1
docker manifest push omadevs/clusterworker:0.0.2