#!/bin/bash
set -e

echo "🚀 Starting Redis container..."
docker compose up -d redis

echo "🚀 Starting PostgreSQL container..."
docker compose up -d db

echo "⏳ Waiting for PostgreSQL to be ready..."
until docker exec $(docker compose ps -q db) pg_isready -U postgres > /dev/null 2>&1; do
  sleep 1
done

echo "✅ PostgreSQL is ready."

echo "📦 Creating database..."
echo "🔍 Checking if database 'core_realm00000' exists..."
if docker exec -i $(docker compose ps -q db) psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'core_realm00000'" | grep -q 1; then
  echo "✅ Database 'core_realm00000' already exists."
else
  echo "➕ Creating database 'core_realm00000'..."
  docker exec -i $(docker compose ps -q db) psql -U postgres -c "CREATE DATABASE core_realm00000;"
fi

echo "🚚 Running migration"
docker compose run --build --rm migration 

docker compose down
echo "✅ Done!"
