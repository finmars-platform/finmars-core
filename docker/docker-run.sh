

# docker volume create --name=finmars-cache-data
# docker run --name finmars-redis -v finmars-cache-data:/data -d redis:3.0

# docker volume create --name=finmars-db-data
# docker run --name finmars-db -v finmars-db-data:/var/lib/postgresql/data -e POSTGRES_PASSWORD=finmars -d postgres:9.5

# docker volume create --name=finmars-data
docker run --name finmars --link finmars-db:postgres --link finmars-redis:redis -v finmars-data:/var/app-data --rm=true -p 8080:8080 -i -t finmars:latest