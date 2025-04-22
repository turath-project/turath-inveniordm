# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Make port 5001 available
EXPOSE 5001

# Define environment variable defaults
ENV PORT=5001
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV HOCR_BASE_DIR=/hocr_data/books
ENV SEARCH_SERVICE_BASE_URL=http://search-service:5001
ENV IIIF_SERVER_BASE_URL=http://nginx:80
ENV USE_SSL=false

# Run app.py when the container launches, listening on the specified PORT (Shell form for variable substitution)
CMD flask run --host=0.0.0.0 --port=$PORT 