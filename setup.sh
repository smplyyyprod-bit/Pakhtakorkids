#!/bin/bash

set -e

echo "🚀 Coaching Management System - Setup Script"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is installed${NC}"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker Compose is installed${NC}"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}📝 Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ .env file created${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  Please edit .env and add your TELEGRAM_BOT_TOKEN${NC}"
    echo "   You can get a token from @BotFather in Telegram"
    echo ""
else
    echo -e "${GREEN}✅ .env file already exists${NC}"
fi

echo ""
echo -e "${YELLOW}📦 Checking Docker images...${NC}"

# Pull images
docker-compose pull

echo ""
echo -e "${YELLOW}🏗️  Building application image...${NC}"

# Build images
docker-compose build

echo ""
echo -e "${YELLOW}🚀 Starting services...${NC}"

# Start containers
docker-compose up -d

echo ""
echo -e "${GREEN}✅ Services started!${NC}"
echo ""

# Wait for services to be healthy
echo -e "${YELLOW}⏳ Waiting for services to be healthy...${NC}"

COUNTER=0
MAX_ATTEMPTS=30

while [ $COUNTER -lt $MAX_ATTEMPTS ]; do
    if docker-compose ps | grep -q "postgres" && docker-compose exec -T postgres pg_isready -U coaching_user &>/dev/null; then
        echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
        break
    fi
    COUNTER=$((COUNTER + 1))
    echo "Attempt $COUNTER/$MAX_ATTEMPTS..."
    sleep 2
done

if [ $COUNTER -eq $MAX_ATTEMPTS ]; then
    echo -e "${RED}❌ Services failed to start within timeout${NC}"
    docker-compose logs
    exit 1
fi

echo ""
echo -e "${GREEN}✅ All services are healthy!${NC}"
echo ""

# Show bot status
echo -e "${YELLOW}📋 Service Status:${NC}"
docker-compose ps

echo ""
echo -e "${GREEN}🎉 Setup complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Edit .env file and add your TELEGRAM_BOT_TOKEN:"
echo "   nano .env"
echo ""
echo "2. Restart the bot:"
echo "   docker-compose restart bot"
echo ""
echo "3. Check the bot logs:"
echo "   docker-compose logs -f bot"
echo ""
echo "4. Open Telegram and find your bot"
echo "5. Send /start to initialize"
echo ""
echo -e "${YELLOW}Documentation:${NC}"
echo "- README.md - Overview and features"
echo "- DEPLOYMENT.md - Detailed deployment guide"
echo ""
