# Orchestr8r: Continuous Delivery of your Perfect Playlist
## A Music Recommendation System using Microservices Architecture

While recommendation engines exist for major music services, they are generally limited to that specific service. If a music fan wants to consider recommendations from other services, a service agnostic recommendation platform may be helpful for more diverse results. Stores of music data that are not tied to specific services include Last.fm and MusicBrainz.org. These tools obtain listener data across a number of services. Thus, querying these services can provide a larger breadth of music data not specific to a single service.

## C4 Model System Context, Container, Component, and Code diagrams

### Context Diagram: 
![alt text](https://github.com/RobotCosmonaut/musicbrainz-app/blob/main/structural_views/1%20-%20Context/Context_Diagram.png "Context Diagram")

### Container Diagram: 
![alt text](https://github.com/RobotCosmonaut/musicbrainz-app/blob/main/structural_views/2%20-%20Container/Container_Diagram.png "Container Diagram")

### Component Diagrams: 

#### Streamlit UI Service Component Diagram
![alt text](https://github.com/RobotCosmonaut/musicbrainz-app/blob/main/structural_views/3%20-%20Component/Component_Diagram_Streamlit.png "Streamlit UI Service Component Diagram")

#### API Gateway Service Component Diagram
![alt text](https://github.com/RobotCosmonaut/musicbrainz-app/blob/main/structural_views/3%20-%20Component/Component_Diagram_API_Gateway.png "API Gateway Service Component Diagram")

#### Database Init Service Component Diagram
![alt text](https://github.com/RobotCosmonaut/musicbrainz-app/blob/main/structural_views/3%20-%20Component/Component_Diagram_Database_Init.png "Database Init Service Component Diagram")

#### Album Service Component Diagram
![alt text](https://github.com/RobotCosmonaut/musicbrainz-app/blob/main/structural_views/3%20-%20Component/Component_Diagram_Album.png "Album Service Component Diagram")

#### Recommendation Service Component Diagram
![alt text](https://github.com/RobotCosmonaut/musicbrainz-app/blob/main/structural_views/3%20-%20Component/Component_Diagram_Recommender.png "Recommendation Service Component Diagram")

#### Artist Service Component Diagram
![alt text](https://github.com/RobotCosmonaut/musicbrainz-app/blob/main/structural_views/3%20-%20Component/Component_Diagram_Artist.png "Artist Service Component Diagram")

### Code Diagrams: 

#### Get Album Code Diagram
![alt text](https://github.com/RobotCosmonaut/musicbrainz-app/blob/main/structural_views/4%20-%20Code/Code_Diagram_Get_Album.png "Get Album Code Diagram")

## Installation
TBD


## Usage
This application is deployed via Docker and Minikube

### Set up PostgreSQL
docker run --name postgres -e POSTGRES_PASSWORD=password -e POSTGRES_DB=musicbrainz -p 5432:5432 -d postgres:14

### Run with Docker (no Minikube)

Bring up all Docker images
```bash
docker-compose up --build
```

### Run with Minikube

Start Minikube
```bash
minikube start
```

Ensure Minikube is using docker-env
```bash
minikube docker-env | Invoke-Expression
```

Now using Minikube's Docker daemon, so need to build all Docker 

```bash
# Build database initialization image
docker build -t musicbrainz-db-init:latest -f dockerfiles/Dockerfile.init .

# Build artist service
docker build -t musicbrainz-artist-service:latest -f dockerfiles/Dockerfile.artist .

# Build album service
docker build -t musicbrainz-album-service:latest -f dockerfiles/Dockerfile.album .

# Build recommendation service
docker build -t musicbrainz-recommendation-service:latest -f dockerfiles/Dockerfile.recommendation .

# Build API gateway
docker build -t musicbrainz-api-gateway:latest -f dockerfiles/Dockerfile.gateway .

# Build Streamlit UI
docker build -t musicbrainz-streamlit-ui:latest -f dockerfiles/Dockerfile.ui .
```

Ensure Minikube is using docker-env
```bash
docker images | Select-String -Pattern "musicbrainz"
```

Deploy to Kubernetes
```bash
# Apply all Kubernetes manifests
kubectl apply -f k8s.yaml
```

```bash
# Watch the deployment progress
kubectl get pods -w
```

```bash
# Get Minikube IP
minikube ip
```

```bash
# Get the NodePort for Streamlit UI
kubectl get svc streamlit-ui-service
```

```bash
# Access the UI (example if NodePort is 30007)
# Open browser to: http://<minikube-ip>:30007
minikube service streamlit-ui-service --url
```

### Troubleshooting

#### When running with Docker (no Minikube)

Remove any existing containers and images
```bash
docker-compose down
docker system prune -f
```

Rebuild everything with no cache from scratch
```bash
docker-compose build --no-cache
```

And run again with Docker
```bash
docker-compose up
```
#### When running with Minikube

Verify using Minikube's Docker:
```bash
docker info | Select-String -Pattern "Name:" -CaseSensitive:$false
# Should show: Name: minikube
```

Restart pods
```bash
kubectl delete pods --all
```

## Contributing
N/A


## License
N/A
