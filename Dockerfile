# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file into the container at /usr/src/app
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Download the NLTK data
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

# Copy the rest of the application's code into the container
COPY . .

# Specify that the container will listen on port 8080 (if applicable)
# EXPOSE 8080

# Define the command to run your application
# CMD ["python", "your_script.py"]
