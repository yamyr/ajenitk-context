#!/bin/bash
# Publish script for ajenitk-context to PyPI

set -e  # Exit on error

echo "Publishing ajenitk-context to PyPI..."
echo "===================================="

# Check if twine is installed
if ! command -v twine &> /dev/null; then
    echo "Installing twine..."
    pip install twine
fi

# Clean and build
echo "Building distributions..."
./build.sh

# Check the distributions
echo -e "\nChecking distributions..."
twine check dist/*

# Test upload to TestPyPI first (optional)
if [ "$1" == "--test" ]; then
    echo -e "\nUploading to TestPyPI..."
    twine upload --repository testpypi dist/*
    echo -e "\nTest with: pip install --index-url https://test.pypi.org/simple/ ajenitk-context"
    exit 0
fi

# Upload to PyPI
echo -e "\nUploading to PyPI..."
echo "This will make the package publicly available!"
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    twine upload dist/*
    echo -e "\nPackage published successfully!"
    echo "Install with: pip install ajenitk-context"
else
    echo "Upload cancelled."
fi