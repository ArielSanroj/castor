#!/bin/bash
# Script to prepare HTML templates for Vercel deployment
# Replaces Flask url_for with static paths

echo "Preparing templates for Vercel deployment..."

# Set API base URL (default to ngrok URL)
API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-https://castorelecciones.ngrok.app}"

# Function to replace Flask url_for in a file
replace_url_for() {
    local file=$1
    
    # Replace url_for('static', filename='...') with /static/...
    sed -i.bak "s|{{ url_for('static', filename='\([^']*\)') }}|/static/\1|g" "$file"
    
    # Replace url_for('index', _external=True) with API_BASE_URL
    sed -i.bak "s|{{ url_for('index', _external=True).rstrip('/') if url_for else '' }}|$API_BASE_URL|g" "$file"
    
    # Remove backup files
    rm -f "${file}.bak"
}

# Process all HTML templates
for file in templates/*.html; do
    if [ -f "$file" ]; then
        echo "Processing $file..."
        replace_url_for "$file"
    fi
done

echo "Done! Templates are ready for Vercel deployment."
echo "API Base URL set to: $API_BASE_URL"

