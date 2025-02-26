#!/bin/bash

# Define base URL and entities
BASE_URL="http://0.0.0.0:8000/realm00000/space00000/docs/api/v1"
ENTITIES=("account" "portfolio" "currency" "instrument" "transaction" "counterparty" "strategy" "report" "procedure" "ui" "explorer" "import" "iam" "vault")

# Create directories if they don't exist
mkdir -p api_docs/src
mkdir -p api_docs/dist
mkdir -p api_docs/dist/assets
mkdir -p api_docs/dist/assets/img
mkdir -p api_docs/dist/assets/css

# Loop through entities and generate docs
for entity in "${ENTITIES[@]}"; do
    JSON_FILE="api_docs/src/${entity}.json"
    HTML_FILE="api_docs/dist/${entity}.html"

    echo "Fetching OpenAPI schema for ${entity}..."
    curl -s "${BASE_URL}/${entity}?format=openapi" -o "$JSON_FILE"

    if [ $? -eq 0 ]; then
        echo "✅ Saved OpenAPI schema: $JSON_FILE"
    else
        echo "❌ Failed to fetch OpenAPI schema for ${entity}"
        continue
    fi

    echo "Generating Redoc HTML for ${entity}..."
    redocly build-docs "$JSON_FILE" -o "$HTML_FILE"

    if [ $? -eq 0 ]; then
        echo "✅ Generated Redoc HTML: $HTML_FILE"
    else
        echo "❌ Failed to generate Redoc HTML for ${entity}"
    fi
done


# Download main index.html from Redoc
echo "Downloading main Redoc page..."
curl -s "$BASE_URL/" -o "api_docs/dist/index.html"

# Extract and download all styles (CSS, JS)
echo "Downloading styles..."
curl -s http://0.0.0.0:8000/realm00000/api/static/css/redoc.css -o "api_docs/dist/assets/css/redoc.css"
curl -s http://0.0.0.0:8000/realm00000/api/static/img/logo.png -o "api_docs/dist/assets/img/logo.png"

sed -i '' 's|/realm00000/api/static/css/|assets/css/|g' api_docs/dist/index.html
sed -i '' 's|/realm00000/api/static/img/|assets/img/|g' api_docs/dist/index.html



# Detect OS and set sed command accordingly
if [[ "$OSTYPE" == "darwin"* ]]; then
    SED_CMD="sed -i ''"  # macOS BSD sed
else
    SED_CMD="sed -i"      # Linux GNU sed
fi

# Loop through each entity and replace its link in index.html
for entity in "${ENTITIES[@]}"; do
    $SED_CMD "s|/realm00000/space00000/docs/api/v1/${entity}|${entity}.html|g" api_docs/dist/index.html
done

echo "Updated links in $HTML_FILE"

find api_docs/dist/ -type f -name "*.html" -exec sed -i '' 's|/realm00000/docs/api/v1/|/|g' {} +


echo "🎉 Documentation generation complete!"
