# Orchestr8r: Continuous Delivery of your Perfect Playlist
## A Music Recommendation System using Microservices Architecture

While recommendation engines exist for major music services, they are generally limited to that specific service. If a music fan wants to consider recommendations from other services, a service agnostic recommendation platform may be helpful for more diverse results. Stores of music data that are not tied to specific services include Last.fm and MusicBrainz.org. These tools obtain listener data across a number of services. Thus, querying these services can provide a larger breadth of music data not specific to a single service.

## C4 Model System Context, Container, Component, and Code diagrams

### Context Diagram: 
![alt text](structural_views/1%20-%20Context/Context_Diagram.png "Context Diagram")

### Container Diagram: 
![alt text](structural_views/2%20-%20Container/Container_Diagram.png "Container Diagram")

### Component Diagrams: 

#### Streamlit UI Service Component Diagram
![alt text](structural_views/3%20-%20Component/Component_Diagram_Streamlit.png "Streamlit UI Service Component Diagram")

#### API Gateway Service Component Diagram
![alt text](structural_views/3%20-%20Component/Component_Diagram_API_Gateway.png "API Gateway Service Component Diagram")

#### Database Init Service Component Diagram
![alt text](structural_views/3%20-%20Component/Component_Diagram_Database_Init.png "Database Init Service Component Diagram")

#### Album Service Component Diagram
![alt text](structural_views/3%20-%20Component/Component_Diagram_Album.png "Album Service Component Diagram")

#### Recommendation Service Component Diagram
![alt text](structural_views/3%20-%20Component/Component_Diagram_Album.png  "Recommendation Service Component Diagram")

#### Artist Service Component Diagram
![alt text](structural_views/3%20-%20Component/Component_Diagram_Artist.png "Artist Service Component Diagram")

### Code Diagrams: 

#### Get Album Code Diagram
![alt text](structural_views/4%20-%20Code/Code_Diagram_Get_Album.png "Get Album Code Diagram")

## Installation
TBD


## Usage
This application is deployed via Docker and Minikube

```bash
minikube start
```

## Contributing
N/A


## License
N/A
