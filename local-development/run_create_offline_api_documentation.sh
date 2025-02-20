#!/bin/bash

# Define base URL and entities
BASE_URL="http://0.0.0.0:8000/realm00000/space00000/docs/api/v1"
ENTITIES=("account" "portfolio" "currency" "instrument" "transaction" "counterparty" "strategy" "report" "procedure" "ui" "explorer" "import" "iam" "vault")

# Create directories if they don't exist
mkdir -p api_docs/src
mkdir -p api_docs/dist

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

echo "🎉 Documentation generation complete!"
