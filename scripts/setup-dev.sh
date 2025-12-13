#!/bin/bash
# ===========================================
# Development Environment Setup Script
# ===========================================

set -e

echo "🚀 Gewerbespeicher Development Setup"
echo "======================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check prerequisites
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 is not installed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ $1 found${NC}"
}

echo ""
echo "Checking prerequisites..."
check_command docker
check_command docker-compose
check_command node
check_command python3

# Setup Backend
echo ""
echo "📦 Setting up Backend..."
cd backend

if [ ! -f ".env" ]; then
    echo "Creating .env from example..."
    cp .env.example .env 2>/dev/null || cat > .env << 'EOF'
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=postgresql://dev:devpass123@localhost:5432/gewerbespeicher
REDIS_URL=redis://localhost:6379
SECRET_KEY=dev-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ANTHROPIC_API_KEY=
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
EOF
    echo -e "${YELLOW}⚠️  Please add your ANTHROPIC_API_KEY to backend/.env${NC}"
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "Installing Python dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

cd ..

# Setup Frontend
echo ""
echo "📦 Setting up Frontend..."
cd frontend

if [ ! -f ".env.local" ]; then
    echo "Creating .env.local..."
    cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENVIRONMENT=development
EOF
fi

echo "Installing Node dependencies..."
npm install --silent

cd ..

# Start Docker services
echo ""
echo "🐳 Starting Docker services (PostgreSQL + Redis)..."
docker-compose up -d db redis

# Wait for PostgreSQL
echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Initialize database
echo "Initializing database schema..."
docker-compose exec -T db psql -U dev -d gewerbespeicher < backend/init.sql 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "To start development:"
echo ""
echo "  Terminal 1 (Backend):"
echo "    cd backend && source venv/bin/activate && uvicorn main:app --reload"
echo ""
echo "  Terminal 2 (Frontend):"
echo "    cd frontend && npm run dev"
echo ""
echo "  URLs:"
echo "    Frontend:  http://localhost:3000"
echo "    Backend:   http://localhost:8000"
echo "    API Docs:  http://localhost:8000/docs"
echo "    Adminer:   http://localhost:8080"
echo ""
