#!/bin/bash

echo "=== Starting Neo4j Container ==="
echo "This script will start Neo4j using Docker Compose and check the connection."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Start Neo4j using Docker Compose
echo "Starting Neo4j..."
docker-compose up -d neo4j

# Wait for Neo4j to start
echo "Waiting for Neo4j to start up..."
for i in {1..30}; do
    if docker-compose ps | grep -q "Up (healthy)"; then
        echo "✅ Neo4j is up and running!"
        echo "Neo4j Browser: http://localhost:7474"
        echo "Neo4j Bolt: bolt://localhost:7687"
        echo "Username: neo4j"
        echo "Password: password"
        
        echo -e "\n=== Neo4j Container Info ==="
        docker-compose ps
        
        echo -e "\n=== Configuration ==="
        echo "Make sure your src/app/config/settings.py has these settings:"
        echo "NEO4J_URI: str = \"bolt://localhost:7687\""
        echo "NEO4J_USER: str = \"neo4j\""
        echo "NEO4J_PASSWORD: str = \"password\""
        
        echo -e "\n=== Testing API ==="
        echo "You can now test the context-gather API with:"
        echo "curl --location 'http://localhost:8000/api/v1/context-gather' \\"
        echo "--header 'Content-Type: application/json' \\"
        echo "--data '{ \"codebase_path\": \"/path/to/your/codebase\" }'"
        
        exit 0
    fi
    echo "Still waiting for Neo4j to be healthy... ($i/30)"
    sleep 2
done

echo "❌ Neo4j did not start properly within the timeout period."
echo "Check the logs with: docker-compose logs neo4j"
exit 1