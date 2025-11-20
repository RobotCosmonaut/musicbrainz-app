#!/usr/bin/env pwsh
# Complete deployment script for Orchestr8r with monitoring

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Orchestr8r - Minikube Deployment with Monitoring" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan

# Step 1: Start Minikube
Write-Host "`n[1/6] Starting Minikube..." -ForegroundColor Yellow
minikube start
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start Minikube" -ForegroundColor Red
    exit 1
}

# Step 2: Use Minikube's Docker daemon
Write-Host "`n[2/6] Configuring Docker environment..." -ForegroundColor Yellow
minikube docker-env | Invoke-Expression

# Step 3: Build all images
Write-Host "`n[3/6] Building Docker images..." -ForegroundColor Yellow
docker build -t musicbrainz-db-init:latest -f dockerfiles/Dockerfile.init .
docker build -t musicbrainz-artist-service:latest -f dockerfiles/Dockerfile.artist .
docker build -t musicbrainz-album-service:latest -f dockerfiles/Dockerfile.album .
docker build -t musicbrainz-recommendation-service:latest -f dockerfiles/Dockerfile.recommendation .
docker build -t musicbrainz-api-gateway:latest -f dockerfiles/Dockerfile.gateway .
docker build -t musicbrainz-streamlit-ui:latest -f dockerfiles/Dockerfile.ui .
docker build -t musicbrainz-metrics-collector:latest -f dockerfiles/Dockerfile.metrics-collector .

Write-Host "`n✓ All images built successfully!" -ForegroundColor Green

# Verify images
Write-Host "`nVerifying images:" -ForegroundColor Cyan
docker images | Select-String -Pattern "musicbrainz"

# Step 4: Deploy to Kubernetes
Write-Host "`n[4/6] Deploying to Kubernetes..." -ForegroundColor Yellow
kubectl apply -f k8s.yaml

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to apply Kubernetes configuration" -ForegroundColor Red
    exit 1
}

# Step 5: Wait for pods to be ready
Write-Host "`n[5/6] Waiting for pods to be ready..." -ForegroundColor Yellow
Write-Host "This may take 2-3 minutes..." -ForegroundColor Gray

Start-Sleep -Seconds 10

# Watch deployment progress
kubectl get pods -w &
$watchJob = $jobs[0]
Start-Sleep -Seconds 60
Stop-Job $watchJob
Remove-Job $watchJob

# Step 6: Get service URLs
Write-Host "`n[6/6] Getting service URLs..." -ForegroundColor Yellow

$minikubeIp = minikube ip

Write-Host "`n" + "=" * 70 -ForegroundColor Green
Write-Host "✓ DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Green

Write-Host "`nAccess your services:" -ForegroundColor Cyan
Write-Host "  Streamlit UI:  http://${minikubeIp}:30007" -ForegroundColor White
Write-Host "  Prometheus:    http://${minikubeIp}:30090" -ForegroundColor White
Write-Host "  Grafana:       http://${minikubeIp}:30030 (admin/admin)" -ForegroundColor White

Write-Host "`nUseful commands:" -ForegroundColor Cyan
Write-Host "  kubectl get pods               # Check pod status" -ForegroundColor Gray
Write-Host "  kubectl logs <pod-name>        # View logs" -ForegroundColor Gray
Write-Host "  kubectl describe pod <pod-name> # Debug issues" -ForegroundColor Gray
Write-Host "  minikube dashboard             # Open Kubernetes dashboard" -ForegroundColor Gray

Write-Host "`n" + "=" * 70 -ForegroundColor Green