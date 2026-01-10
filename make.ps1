# PowerShell script for UV-based project management on Windows
# Usage: .\make.ps1 <command>

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "Available commands:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Setup & Installation:" -ForegroundColor Yellow
    Write-Host "  .\make.ps1 install        - Create venv and install dependencies with UV"
    Write-Host "  .\make.ps1 install-dev    - Install with dev dependencies"
    Write-Host "  .\make.ps1 setup          - Complete setup (install + docker)"
    Write-Host "  .\make.ps1 sync           - Sync dependencies from lockfile"
    Write-Host "  .\make.ps1 sync-req       - Generate requirements.txt from pyproject.toml"
    Write-Host "  .\make.ps1 update         - Update all dependencies"
    Write-Host ""
    Write-Host "Development:" -ForegroundColor Yellow
    Write-Host "  .\make.ps1 test           - Run tests with pytest"
    Write-Host "  .\make.ps1 lint           - Run linters (flake8, mypy)"
    Write-Host "  .\make.ps1 format         - Format code with black and isort"
    Write-Host "  .\make.ps1 clean          - Remove virtual environment and cache files"
    Write-Host "  .\make.ps1 run-jupyter    - Start Jupyter Lab"
    Write-Host ""
    Write-Host "Docker:" -ForegroundColor Yellow
    Write-Host "  .\make.ps1 docker-up      - Start Docker services (PostgreSQL, Neo4j)"
    Write-Host "  .\make.ps1 docker-down    - Stop Docker services"
    Write-Host "  .\make.ps1 docker-build   - Build production Docker image"
    Write-Host "  .\make.ps1 docker-build-dev - Build development Docker image"
    Write-Host ""
    Write-Host "See docs/DOCKER_GUIDE.md for Docker usage details" -ForegroundColor Cyan
}

function Test-UV {
    $uvExists = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uvExists) {
        Write-Host "UV not found. Installing..." -ForegroundColor Yellow
        powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
        Write-Host "UV installed! Please restart your terminal." -ForegroundColor Green
        exit
    }
}

function Install-Project {
    Test-UV
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    uv venv
    Write-Host "Installing dependencies..." -ForegroundColor Cyan
    uv pip install -e .
    Write-Host "✅ Installation complete! Activate with: .venv\Scripts\Activate.ps1" -ForegroundColor Green
}

function Install-Dev {
    Test-UV
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    uv venv
    Write-Host "Installing all dependencies..." -ForegroundColor Cyan
    uv sync --all-extras
    Write-Host "✅ Dev installation complete!" -ForegroundColor Green
}

function Sync-Dependencies {
    Test-UV
    Write-Host "Syncing dependencies from lockfile..." -ForegroundColor Cyan
    uv sync --all-extras
    Write-Host "✅ Dependencies synced!" -ForegroundColor Green
}

function Sync-Requirements {
    Test-UV
    Write-Host "Generating requirements.txt from pyproject.toml..." -ForegroundColor Cyan
    uv pip compile pyproject.toml -o requirements.txt
    Write-Host "✅ requirements.txt generated!" -ForegroundColor Green
}

function Update-Dependencies {
    Test-UV
    Write-Host "Updating dependencies..." -ForegroundColor Cyan
    uv lock --upgrade
    uv sync --all-extras
    Write-Host "✅ Dependencies updated!" -ForegroundColor Green
}

function Clean-Project {
    Write-Host "Cleaning project..." -ForegroundColor Cyan
    
    if (Test-Path .venv) { Remove-Item -Recurse -Force .venv }
    if (Test-Path build) { Remove-Item -Recurse -Force build }
    if (Test-Path dist) { Remove-Item -Recurse -Force dist }
    if (Test-Path .pytest_cache) { Remove-Item -Recurse -Force .pytest_cache }
    if (Test-Path .mypy_cache) { Remove-Item -Recurse -Force .mypy_cache }
    if (Test-Path htmlcov) { Remove-Item -Recurse -Force htmlcov }
    if (Test-Path .coverage) { Remove-Item -Force .coverage }
    
    Get-ChildItem -Path . -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Filter "*.pyc" | Remove-Item -Force
    Get-ChildItem -Path . -Recurse -Filter "*.egg-info" | Remove-Item -Recurse -Force
    
    Write-Host "✅ Cleaned up!" -ForegroundColor Green
}

function Run-Tests {
    Write-Host "Running tests..." -ForegroundColor Cyan
    uv run pytest tests/ -v --cov=src --cov-report=term-missing
}

function Run-TestsWithCoverage {
    Write-Host "Running tests with coverage..." -ForegroundColor Cyan
    uv run pytest tests/ -v --cov=src --cov-report=html --cov-report=term
    Write-Host "✅ Coverage report generated in htmlcov/" -ForegroundColor Green
}

function Run-Lint {
    Write-Host "Running linters..." -ForegroundColor Cyan
    uv run flake8 src tests
    uv run mypy src
    Write-Host "✅ Linting complete!" -ForegroundColor Green
}

function Check-Format {
    Write-Host "Checking code formatting..." -ForegroundColor Cyan
    uv run black --check src tests
    uv run isort --check-only src tests
}

function Format-Code {
    Write-Host "Formatting code..." -ForegroundColor Cyan
    uv run black src tests
    uv run isort src tests
    Write-Host "✅ Code formatted!" -ForegroundColor Green
}

function Start-Docker {
    Write-Host "Starting Docker services..." -ForegroundColor Cyan
    docker-compose up -d
    Write-Host "⏳ Waiting for services to be healthy..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    docker-compose ps
    Write-Host "✅ Docker services started!" -ForegroundColor Green
}

function Stop-Docker {
    Write-Host "Stopping Docker services..." -ForegroundColor Cyan
    docker-compose down
    Write-Host "✅ Docker services stopped!" -ForegroundColor Green
}

function Reset-Docker {
    Write-Host "Resetting Docker services..." -ForegroundColor Cyan
    docker-compose down -v
    docker-compose up -d
    Write-Host "✅ Docker services reset!" -ForegroundColor Green
}

function Setup-Project {
    Install-Dev
    Start-Docker
    Write-Host "🎉 Setup complete! You're ready to go!" -ForegroundColor Green
}

function Run-Jupyter {
    Write-Host "Starting Jupyter Lab..." -ForegroundColor Cyan
    uv run jupyter lab notebooks/
}

function Run-CLI {
    uv run python cli.py --help
}

function Run-Dev {
    Format-Code
    Run-Lint
    Run-Tests
    Write-Host "✅ Development checks passed!" -ForegroundColor Green
}

function Run-CI {
    Install-Dev
    Check-Format
    Run-Lint
    Run-Tests
    Write-Host "✅ CI checks passed!" -ForegroundColor Green
}

function Show-EnvInfo {
    Write-Host "Python Environment Information:" -ForegroundColor Cyan
    uv run python --version
    Write-Host "`nInstalled Packages:" -ForegroundColor Cyan
    uv pip list
}

function Add-Package {
    $package = Read-Host "Package name"
    uv add $package
    Write-Host "✅ Package added!" -ForegroundColor Green
}

function Add-DevPackage {
    $package = Read-Host "Package name"
    uv add --dev $package
    Write-Host "✅ Dev package added!" -ForegroundColor Green
}

function Build-DockerProd {
    Write-Host "Building production Docker image..." -ForegroundColor Cyan
    docker build -t naive-rag:latest .
    Write-Host "✅ Production image built: naive-rag:latest" -ForegroundColor Green
}

function Build-DockerDev {
    Write-Host "Building development Docker image..." -ForegroundColor Cyan
    docker build -f Dockerfile.dev -t naive-rag:dev .
    Write-Host "✅ Development image built: naive-rag:dev" -ForegroundColor Green
}

# Command dispatcher
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "install" { Install-Project }
    "install-dev" { Install-Dev }
    "sync" { Sync-Dependencies }
    "sync-req" { Sync-Requirements }
    "update" { Update-Dependencies }
    "clean" { Clean-Project }
    "test" { Run-Tests }
    "test-cov" { Run-TestsWithCoverage }
    "lint" { Run-Lint }
    "format-check" { Check-Format }
    "docker-build" { Build-DockerProd }
    "docker-build-dev" { Build-DockerDev }
    "format" { Format-Code }
    "docker-up" { Start-Docker }
    "docker-down" { Stop-Docker }
    "docker-reset" { Reset-Docker }
    "setup" { Setup-Project }
    "run-jupyter" { Run-Jupyter }
    "run-cli" { Run-CLI }
    "dev" { Run-Dev }
    "ci" { Run-CI }
    "env-info" { Show-EnvInfo }
    "add" { Add-Package }
    "add-dev" { Add-DevPackage }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
    }
}
