# Python version: 3.12
FROM python:3.12-slim

WORKDIR /alisearch
# Copy files to container
COPY requirements.txt /alisearch/
COPY app /alisearch/app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONPATH=/alisearch

# Start init db and run server
CMD ["bash", "-c", "python app/services/init_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
