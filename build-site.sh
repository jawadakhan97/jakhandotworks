#!/usr/bin/env bash

# Remove public directory if it exists
rm -rf ./public

# Create public directory
mkdir -p ./public

# Run ./send-mail.sh on 

# Temporary file to hold concatenated content
TEMPFILE=$(MKTEMP)

# Generate sorted list of files by depth and alphabetical order
mapfile -d '' file < <(
    find ./content -type f -print0 | \
    awk -v RS='\0' '{
        depth = gsub(/\//, "/", $0);
        print depth "\t" $0;
    }' | \
    sort -n -k1,1 -k2 | \
    cut -f2- | \
    tr '\n' '\0'
)

# Append each file's content followed by two new lines
for file in "${FILE[@]}"; do
    cat "$FILE" >> "$TEMPFILE"
    printf "\n\n" >> "$TEMPFILE"
done
