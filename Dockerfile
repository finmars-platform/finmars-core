# Use an official Python runtime as a parent image
FROM python:3.11.4-bullseye

# Update and install packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim htop wget supervisor nfs-common && \
    rm -rf /var/lib/apt/lists/*

# Set working directory in the container
WORKDIR /var/app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . .

# Create necessary directories and change their permissions
RUN mkdir -p /var/app-data/import/configs/ /var/app-data/import/files/ /var/app/finmars_data \
            /var/app-data/media/ /var/log/finmars/backend /var/log/celery && \
    chmod 777 /var/app/finmars_data

# Copy supervisor configs
COPY docker/supervisor/*.conf /etc/supervisor/conf.d/

# Change permission of the shell script
RUN chmod +x /var/app/docker/finmars-run.sh

# Set environment variables
ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run the command on container startup
CMD ["/bin/bash", "/var/app/docker/finmars-run.sh"]