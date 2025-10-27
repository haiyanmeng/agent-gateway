# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install any needed packages specified in requirements.txt
RUN pip install fastmcp

# Copy the current directory contents into the container at /app
COPY agent.py .

# Run agent.py when the container launches
CMD ["python", "agent.py"]
