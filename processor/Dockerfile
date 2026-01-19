#######################################################
# Sets up and runs the main scraper logic             #
#######################################################
FROM python:3.11

# Creates a folder inside the container and cd into it
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy main controller
COPY main.py .

# Copy code into /app
COPY src/ ./src/

# Start command
CMD ["python", "-u", "main.py"]