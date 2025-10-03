# Use Minikube's Docker daemon
minikube docker-env | Invoke-Expression

# Build all images
docker build -t musicbrainz-db-init:latest -f dockerfiles/Dockerfile.init .
docker build -t musicbrainz-artist-service:latest -f dockerfiles/Dockerfile.artist .
docker build -t musicbrainz-album-service:latest -f dockerfiles/Dockerfile.album .
docker build -t musicbrainz-recommendation-service:latest -f dockerfiles/Dockerfile.recommendation .
docker build -t musicbrainz-api-gateway:latest -f dockerfiles/Dockerfile.gateway .
docker build -t musicbrainz-streamlit-ui:latest -f dockerfiles/Dockerfile.ui .

Write-Host "All images built successfully!" -ForegroundColor Green