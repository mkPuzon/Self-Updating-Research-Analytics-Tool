FROM python:3.12

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# listen on 0.0.0.0 so nginx in another container can reach it
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]