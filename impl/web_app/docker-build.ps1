# Build the Docker image for this app.
# Notes:
# 1: be sure to have Docker Desktop running on your system.
# 2: please change the Docker image names (the cjoakim prefix).
# 3: this script pushes the public image to public Docker Hub,
#    but you should instead use your private Azure Container Registry
#    for your images.
#
# Chris Joakim, Microsoft, 2025

Write-Host 'building caig_web_v3 image ...'
docker build -f Dockerfile -t cjoakim/caig_web_v3 .

Write-Host 'next steps:'
Write-Host '  docker push cjoakim/caig_web_v3:latest'

Write-Host 'done'


# Developer Notes:
# docker build -f Dockerfile -t cjoakim/caig_web_v3 .
# docker image ls
# docker ps
# docker stop -t 2 008038664a58
#
# Listing local images:
# docker images | grep v3
#
# DockerHub:
# docker push cjoakim/caig_web_v3:latest
