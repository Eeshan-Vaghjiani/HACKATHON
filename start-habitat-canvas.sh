#!/bin/bash

echo "========================================"
echo " HabitatCanvas Startup Script"
echo "========================================"
echo

echo "Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed or not running"
    echo "Please install Docker and make sure it's running"
    exit 1
fi

echo "Docker found! Starting HabitatCanvas..."
echo

echo "Cleaning previous builds..."
docker-compose down -v > /dev/null 2>&1

echo "Building and starting services..."
echo "This may take 5-10 minutes on first run..."
docker-compose up --build

echo
echo "========================================"
echo " HabitatCanvas should now be running at:"
echo " Frontend: http://localhost:3000"
echo " Backend:  http://localhost:8000"
echo " API Docs: http://localhost:8000/docs"
echo "========================================"