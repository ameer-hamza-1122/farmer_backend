# Use official Python image from the Docker Hub
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential libpq-dev --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install pipenv and project dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files to the container
COPY . .

# Expose the port for the Django application
EXPOSE 8009

# Run Django server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8009"]

# Set TensorFlow logging level to reduce verbosity
ENV TF_CPP_MIN_LOG_LEVEL=2

