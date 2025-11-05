@echo off
setlocal

set IMAGE_NAME="mtgencode-interactive"

echo "Building Docker image: %IMAGE_NAME%"
docker build -t %IMAGE_NAME% .

echo "Starting interactive session in Docker container"
docker run -it --rm -v "%cd%:/usr/src/app" %IMAGE_NAME% bash
