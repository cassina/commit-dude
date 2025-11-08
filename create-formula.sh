#!/bin/bash
# Helper script to generate Homebrew formula with correct SHA256 hashes

set -e

echo "Building the package..."
uv build

PACKAGE_FILE=$(ls dist/*.tar.gz | head -n 1)
PACKAGE_SHA=$(shasum -a 256 "$PACKAGE_FILE" | cut -d' ' -f1)

echo ""
echo "Package SHA256: $PACKAGE_SHA"
echo ""
echo "Update commit-dude.rb with this SHA256 hash."
echo "You'll also need to:"
echo "1. Upload the package to PyPI: uv publish"
echo "2. Update the URL in the formula to point to PyPI"
echo "3. Run 'brew install --build-from-source ./commit-dude.rb' to test locally"
echo ""
echo "For dependency SHA256 hashes, download them from PyPI and run:"
echo "  shasum -a 256 <package-file>.tar.gz"