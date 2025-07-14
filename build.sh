#!/bin/bash
# Build script for ajenitk-context

set -e  # Exit on error

echo "Building ajenitk-context..."
echo "=========================="

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info/

# Create source distribution
echo "Creating source distribution..."
python setup.py sdist

# Create wheel distribution
echo "Creating wheel distribution..."
python setup.py bdist_wheel

# Display build artifacts
echo -e "\nBuild artifacts:"
ls -la dist/

# Optional: Test installation in a temporary virtual environment
if [ "$1" == "--test" ]; then
    echo -e "\nTesting installation..."
    
    # Create temporary directory
    TEMP_DIR=$(mktemp -d)
    cd $TEMP_DIR
    
    # Create virtual environment
    python -m venv test_env
    source test_env/bin/activate
    
    # Install the package
    pip install $OLDPWD/dist/*.whl
    
    # Test the CLI
    echo -e "\nTesting CLI commands..."
    agentic version
    agentic --help
    
    # Cleanup
    deactivate
    cd $OLDPWD
    rm -rf $TEMP_DIR
    
    echo -e "\nInstallation test completed successfully!"
fi

echo -e "\nBuild completed successfully!"
echo "To install locally: pip install dist/*.whl"
echo "To upload to PyPI: twine upload dist/*"