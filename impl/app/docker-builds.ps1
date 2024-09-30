# Build the two microservice Docker images for this app.
# Note 1: be sure to have Docker Desktop running on your system.
# Note 2: please change the Docker image names (the cjoakim prefix).
# Chris Joakim, Microsoft

echo 'building caig_graph_v2 image ...'
docker build -f docker\Dockerfile_graph -t cjoakim/caig_graph_v2 .

'building caig_web_v2 image ...'
docker build -f docker\Dockerfile_web -t cjoakim/caig_web_v2 .

echo 'next steps:'
echo '  docker push cjoakim/caig_graph_v2:latest'
echo '  docker push cjoakim/caig_web_v2:latest'

echo 'done'
