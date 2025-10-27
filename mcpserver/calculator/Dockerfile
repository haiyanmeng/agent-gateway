# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install any needed packages specified in requirements.txt
RUN pip install fastmcp

# Copy the current directory contents into the container at /app
COPY my_mcp_server.py .

# Make port 9000 available to the world outside this container
EXPOSE 9000

# Run the app when the container launches
CMD ["python", "my_mcp_server.py"]
