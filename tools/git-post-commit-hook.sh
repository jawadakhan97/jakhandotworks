#!/bin/bash
# Git post-commit hook for automatic newsletter/blog broadcasting
#
# This hook triggers the Kit broadcast script whenever you commit
# changes to newsletter or blog posts.
#
# Installation:
#   1. Copy this file to .git/hooks/post-commit
#   2. Make it executable: chmod +x .git/hooks/post-commit
#   3. Set required environment variables in your shell or CI/CD:
#      - KIT_API_KEY: Your Kit API key
#      - KIT_FORM_ID: Your subscriber form ID
#
# Testing:
#   Before installing the hook, test manually with:
#   python tools/kit_broadcast.py --dry-run

# Get the commit hash of the current commit
COMMIT_HASH=$(git rev-parse HEAD)

# Change to the repository root
cd "$(git rev-parse --show-toplevel)"

# Run the broadcast script (with --dry-run commented out by default)
# Remove --dry-run flag when ready to actually send broadcasts
echo "Checking for newsletter/blog updates in commit ${COMMIT_HASH:0:8}..."

python3 tools/kit_broadcast.py --commit-hash "$COMMIT_HASH" # --dry-run

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "✓ Post-commit broadcast check completed successfully"
else
    echo "✗ Post-commit broadcast check failed with exit code $exit_code"
fi

exit 0
