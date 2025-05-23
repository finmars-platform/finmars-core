#!/bin/bash

ENV_FILE=".env"
ENV_SAMPLE_FILE=".env.sample"

if [ -f "$ENV_FILE" ]; then
  read -p "$ENV_FILE already exists. Overwrite? (y/N): " ans
  if [[ "$ans" != "y" && "$ans" != "Y" ]]; then
    echo "Skipped creating $ENV_FILE."
    exit 0
  fi
fi

cp "$ENV_SAMPLE_FILE" "$ENV_FILE"

SECRET_KEY=$(openssl rand -base64 64 | tr -dc 'a-zA-Z0-9!@#$%^&*(-_=+)' | head -c 50)

sed -i.bak "s|YOUR_DJANGO_SECRET_KEY|$SECRET_KEY|" "$ENV_FILE"
rm "${ENV_FILE}.bak"

echo "$ENV_FILE created with new SECRET_KEY."
