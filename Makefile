.PHONY: build test run clean help

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker image locally
	@echo "🔨 Building Docker image..."
	docker build -t mindspring-fastapi:test .
	@echo "✅ Build successful!"

test: build ## Build and test the Docker image
	@echo "🧪 Testing Docker build..."
	docker build -t mindspring-fastapi:test .
	@echo "✅ Build test passed!"

run: ## Run the Docker container locally
	@echo "🚀 Running container..."
	docker run --rm -p 8000:8000 \
		-e PORT=8000 \
		-e DATABASE_URL="postgresql://user:pass@host:5432/db" \
		-e REDIS_URL="redis://localhost:6379" \
		-e SECRET_KEY="test-secret-key" \
		mindspring-fastapi:test

clean: ## Remove test Docker image
	@echo "🧹 Cleaning up..."
	docker rmi mindspring-fastapi:test || true
	@echo "✅ Cleanup complete!"
