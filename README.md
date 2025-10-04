# HabitatCanvas

A web-based generative layout studio for space habitats that enables users to define pressurized habitat volumes and automatically generate, evaluate, and iterate interior layouts.

## Project Structure

```
habitat-canvas/
├── frontend/          # React + TypeScript + Three.js frontend
├── backend/           # FastAPI + Python backend
├── docker-compose.yml # Local development environment
└── README.md
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Setup
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd habitat-canvas
   ```

2. Start the development environment:
   ```bash
   # Using Docker Compose directly
   docker-compose up --build

   # Or using the setup script (Linux/Mac)
   ./scripts/dev-setup.sh

   # Or using the setup script (Windows)
   scripts\dev-setup.bat

   # Or using Make
   make setup
   ```

3. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Database: localhost:5432 (user: habitatcanvas, password: password)
   - Redis: localhost:6379

## Development

### Frontend
- React 18 with TypeScript
- React Three Fiber for 3D rendering
- Vite for build tooling
- TailwindCSS for styling

### Backend
- FastAPI with Python 3.11+
- Pydantic for data validation
- SQLAlchemy for database ORM
- PostgreSQL database
- Redis for caching

## Requirements

- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)
## Deve
lopment Commands

### Using Make (recommended)
```bash
make setup          # Set up development environment
make up             # Start services
make down           # Stop services
make logs           # View all logs
make test           # Run all tests
make clean          # Clean up containers and volumes
```

### Using Docker Compose directly
```bash
docker-compose up --build    # Build and start all services
docker-compose down          # Stop all services
docker-compose logs -f       # View logs
docker-compose restart       # Restart services
```

### Running Tests
```bash
# Frontend tests
make test-frontend
# or
docker-compose exec frontend npm test

# Backend tests
make test-backend
# or
docker-compose exec backend pytest
```

## Project Structure Details

### Frontend (`/frontend`)
- **Framework**: React 18 with TypeScript
- **3D Rendering**: React Three Fiber + Three.js
- **Build Tool**: Vite with HMR
- **Styling**: TailwindCSS
- **State Management**: Zustand
- **Testing**: Vitest + React Testing Library

### Backend (`/backend`)
- **Framework**: FastAPI with Python 3.11+
- **Database**: PostgreSQL with SQLAlchemy (async)
- **Cache**: Redis
- **Validation**: Pydantic v2
- **Testing**: pytest with async support
- **Code Quality**: Black, isort, mypy

### Key Features Implemented
- ✅ Monorepo structure with frontend and backend
- ✅ Docker Compose development environment
- ✅ TypeScript configuration with strict type checking
- ✅ FastAPI backend with Pydantic models and async support
- ✅ Vite build system with Three.js and React Three Fiber
- ✅ PostgreSQL database with initialization scripts
- ✅ Redis caching layer
- ✅ Basic API endpoints structure
- ✅ Testing setup for both frontend and backend
- ✅ Development tooling (linting, formatting, type checking)

## Next Steps

This completes Task 1 of the implementation plan. The project structure and development environment are now set up. You can proceed to Task 2 to implement the core data models and validation.

To start working on the next task:
1. Ensure the development environment is running: `make setup`
2. Verify all services are healthy by visiting the URLs above
3. Begin implementing Task 2.1: "Create TypeScript interfaces for frontend data models"