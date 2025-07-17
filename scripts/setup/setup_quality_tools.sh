#!/bin/bash

# Setup script for code quality tools
# This script installs and configures all code quality tools for the project

set -e

echo "🔧 Setting up code quality tools for Rethinking Park Backend API..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_error "pyproject.toml not found. Please run this script from the project root directory."
    exit 1
fi

# Install development dependencies
print_status "Installing development dependencies..."
pip install -r requirements/dev.txt

# Install pre-commit hooks
print_status "Installing pre-commit hooks..."
pre-commit install

# Run initial formatting
print_status "Running initial code formatting..."
black app services models tests || print_warning "Black formatting had issues, continuing..."
isort app services models tests || print_warning "isort had issues, continuing..."

# Run initial quality checks
print_status "Running initial quality checks..."

echo "Running flake8..."
flake8 app services models tests || print_warning "Flake8 found issues, please review"

echo "Running pylint..."
pylint app services models || print_warning "Pylint found issues, please review"

echo "Running mypy..."
mypy app services models || print_warning "MyPy found issues, please review"

echo "Running bandit security check..."
bandit -r app services models -f json -o bandit-report.json || print_warning "Bandit found security issues, please review"

# Run tests to ensure everything works
print_status "Running tests to verify setup..."
pytest tests/unit/ -v || print_warning "Some unit tests failed, please review"

print_status "Code quality tools setup completed!"
print_status "You can now use the following commands:"
echo "  make lint           - Run all linting checks"
echo "  make format         - Format code"
echo "  make type-check     - Run type checking"
echo "  make security-check - Run security checks"
echo "  make quality-check  - Run all quality checks"
echo "  make pre-commit     - Run pre-commit hooks"

print_status "Pre-commit hooks are now installed and will run automatically on git commit."