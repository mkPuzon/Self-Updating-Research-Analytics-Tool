#######################################################
# Sets up and runs the main scraper logic             #
#######################################################
FROM python:3.12

# Creates a folder inside the container and cd into it
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code into /app
COPY . .

# Expose port for documentation
EXPOSE 8501

# Healthchack; confirms Streamlit is running every 30s
HEALTHCHECK --interval=30s CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Start command
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]