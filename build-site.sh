#!/usr/bin/env bash

# Remove public directory if it exists
rm -rf ./public

# Create public directory
mkdir -p ./public

# Run ./send-mail.sh on 

# Generate sorted list of files by depth and alphabetical order
file_list=()
while IFS= read -r path; do
    if [ -n "$path" ]; then
        file_list+=("$path")
    fi
done < <(
    find ./src/content -type f | awk '{ print length, $0 }' | sort -n | cut -d" " -f2-
)

# Process each file individually into its own HTML file
for file in "${file_list[@]}"; do
    if [ -f "$file" ]; then
        # 1. Cleanly swap ./src/content to ./public using sed
        # Example: ./src/content/about/index.html -> ./public/about/index.html 
        html_file=$(echo "$file" | sed 's|./src/content|./public|')

        # 2. Ensure the extension is cleanly set to .html 
        html_file="${html_file%.*}.html"
        
        # 3. Create the nested directory structure inside ./public if needed
        mkdir -p "$(dirname "$html_file")"
        
        # 4. Convert this specific file with pandoc
        pandoc "$file" -f markdown -o "$html_file"
    fi
done

echo "Successfully built ${#file_list[@]} individual pages inside ./public/"
