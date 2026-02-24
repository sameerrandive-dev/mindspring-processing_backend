# Build script to test Docker build before deploying to Railway
# Usage: .\build.ps1

Write-Host "🔨 Building Docker image..." -ForegroundColor Cyan

docker build -t mindspring-fastapi:test .

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Build successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "To test run the container:"
    Write-Host "  docker run --rm -p 8000:8000 -e PORT=8000 mindspring-fastapi:test"
    Write-Host ""
    Write-Host "Or use docker-compose:"
    Write-Host "  docker-compose -f docker-compose.test.yml up --build"
} else {
    Write-Host ""
    Write-Host "❌ Build failed! Check the error messages above." -ForegroundColor Red
    exit 1
}
