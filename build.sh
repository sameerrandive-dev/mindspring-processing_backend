#!/bin/bash
# Build script to test Docker build before deploying to Railway
# Usage: ./build.sh

set -e  # Exit on error

echo "🔨 Building Docker image..."
docker build -t mindspring-fastapi:test .

echo ""
echo "✅ Build successful!"
echo ""
echo "To test run the container:"
echo "  docker run --rm -p 8000:8000 -e PORT=8000 mindspring-fastapi:test"
echo ""
echo "Or use docker-compose:"
echo "  docker-compose -f docker-compose.test.yml up --build"
