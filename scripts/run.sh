#!/bin/bash
# Unified script execution interface for Rethinking Park Backend API
# Provides easy access to all project scripts

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show usage information
show_usage() {
    echo "🚀 Rethinking Park Backend API - Script Runner"
    echo "=============================================="
    echo
    echo "Usage: $0 <category> <script> [arguments...]"
    echo
    echo "Categories:"
    echo "  setup       - Environment setup scripts"
    echo "  deployment  - Deployment scripts"
    echo "  testing     - Testing scripts"
    echo "  maintenance - Maintenance and verification scripts"
    echo
    echo "Available Scripts:"
    echo
    echo "📦 Setup Scripts:"
    echo "  setup.sh                    - Complete environment setup"
    echo
    echo "🚀 Deployment Scripts:"
    echo "  deploy_production.sh        - Production deployment"
    echo
    echo "🧪 Testing Scripts:"
    echo "  test-docker.sh              - Docker testing"
    echo "  run_tests.py                - Advanced test runner"
    echo
    echo "🔧 Maintenance Scripts:"
    echo "  organize_tests.py           - Organize test files"
    echo "  validate_frontend_tests.py  - Validate frontend tests"
    echo "  verify_*.py                 - Various verification scripts"
    echo
    echo "Examples:"
    echo "  $0 setup setup.sh"
    echo "  $0 deployment deploy_production.sh"
    echo "  $0 testing test-docker.sh"
    echo "  $0 testing run_tests.py --all"
    echo "  $0 maintenance organize_tests.py"
    echo "  $0 maintenance verify_setup.py"
    echo
    echo "Quick Commands:"
    echo "  $0 list                     - List all available scripts"
    echo "  $0 help                     - Show this help message"
}

# List all available scripts
list_scripts() {
    echo "📋 Available Scripts:"
    echo "===================="
    
    echo
    echo "📦 Setup Scripts (scripts/setup/):"
    if [ -d "scripts/setup" ]; then
        ls -1 scripts/setup/ | sed 's/^/  /'
    else
        echo "  No setup scripts found"
    fi
    
    echo
    echo "🚀 Deployment Scripts (scripts/deployment/):"
    if [ -d "scripts/deployment" ]; then
        ls -1 scripts/deployment/ | sed 's/^/  /'
    else
        echo "  No deployment scripts found"
    fi
    
    echo
    echo "🧪 Testing Scripts (scripts/testing/):"
    if [ -d "scripts/testing" ]; then
        ls -1 scripts/testing/ | sed 's/^/  /'
    else
        echo "  No testing scripts found"
    fi
    
    echo
    echo "🔧 Maintenance Scripts (scripts/maintenance/):"
    if [ -d "scripts/maintenance" ]; then
        ls -1 scripts/maintenance/ | sed 's/^/  /'
    else
        echo "  No maintenance scripts found"
    fi
}

# Execute a script
execute_script() {
    local category="$1"
    local script="$2"
    shift 2
    local args="$@"
    
    local script_path="scripts/$category/$script"
    
    # Check if script exists
    if [ ! -f "$script_path" ]; then
        error "Script not found: $script_path"
        echo
        echo "Available scripts in $category:"
        if [ -d "scripts/$category" ]; then
            ls -1 "scripts/$category/" | sed 's/^/  /'
        else
            echo "  Category directory not found: scripts/$category"
        fi
        exit 1
    fi
    
    # Make script executable if it's not
    if [ ! -x "$script_path" ]; then
        log "Making script executable: $script_path"
        chmod +x "$script_path"
    fi
    
    # Execute the script
    log "Executing: $script_path $args"
    echo "=============================================="
    
    # Change to project root directory
    cd "$(dirname "$0")/.."
    
    # Execute based on file extension
    if [[ "$script" == *.py ]]; then
        python "$script_path" $args
    elif [[ "$script" == *.sh ]]; then
        bash "$script_path" $args
    else
        # Try to execute directly
        "$script_path" $args
    fi
    
    local exit_code=$?
    echo "=============================================="
    
    if [ $exit_code -eq 0 ]; then
        success "Script completed successfully"
    else
        error "Script failed with exit code: $exit_code"
        exit $exit_code
    fi
}

# Main function
main() {
    # Check if we're in the right directory
    if [ ! -f "main.py" ] || [ ! -d "scripts" ]; then
        error "Please run this script from the project root directory"
        exit 1
    fi
    
    # Handle arguments
    case "${1:-help}" in
        "help"|"-h"|"--help")
            show_usage
            ;;
        "list"|"-l"|"--list")
            list_scripts
            ;;
        "setup"|"deployment"|"testing"|"maintenance")
            if [ -z "$2" ]; then
                error "Please specify a script name"
                echo
                echo "Available scripts in $1:"
                if [ -d "scripts/$1" ]; then
                    ls -1 "scripts/$1/" | sed 's/^/  /'
                fi
                exit 1
            fi
            execute_script "$@"
            ;;
        *)
            error "Unknown command: $1"
            echo
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"