# Build the Docker image for this app.
# Notes:
# 1: be sure to have Docker Desktop running on your system.
# 2: please change the Docker image names (the cjoakim prefix).
# 3: this script pushes the public image to public Docker Hub,
#    but you should instead use your private Azure Container Registry
#    for your images.
#
# Chris Joakim, Aleksey Savateyev

Write-Host 'compiling ...'
.\build.ps1 

Write-Host 'building caig_graph image ...'
docker build -f Dockerfile -t omnirag/caig_graph .

Write-Host 'next steps:'
Write-Host '  docker push omnirag/caig_graph:latest'

Write-Host 'done'


# Developer Notes:
# docker build -f Dockerfile -t omnirag/caig_graph .
# docker image ls
# docker ps
# docker stop -t 2 008038664a58
#
# Listing local images:
# docker images | grep v3
#
# DockerHub:
# docker push omnirag/caig_graph:latest
