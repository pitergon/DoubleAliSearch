# Python version: 3.12
FROM python:3.12-slim

WORKDIR /app

# Copy all files to the container
COPY . /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
#ENV DB_HOST=postgres
#ENV DB_PORT=5432
#ENV DB_USER=${DB_USER}
#ENV DB_PASSWORD=${DB_PASSWORD}
#ENV DB_DATABASE=${DB_DATABASE}
#ENV REDIS_HOST=redis
#ENV REDIS_PASSWORD=${REDIS_PASSWORD}
#ENV JWT_SECRET_KEY=${JWT_SECRET_KEY}
#ENV JWT_ALGORITHM=${JWT_ALGORITHM}
# Start init db and run server
CMD ["bash", "-c", "python app/services/init_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
