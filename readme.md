# **AliExpress Search Application**

This project is a FastAPI-based application that allows users to search for products on AliExpress. It integrates PostgreSQL for data storage and Redis for caching, with a Dockerized setup for easy deployment.

---

## **Features**
- **Product Search**: Search for products on AliExpress with an efficient backend service.
- **Database Support**: PostgreSQL database for persisting user data and search results.
- **Caching**: Redis for faster access to frequently queried data.
- **Environment Configuration**: Use `.env` files to manage sensitive information like database credentials and secret keys.

---

## **Technologies**
- **Backend**: FastAPI  
- **Database**: PostgreSQL  
- **Cache**: Redis  
- **Deployment**: Docker & Docker Compose

---

## **Getting Started**

### **1. Prerequisites**
Ensure you have the following installed:
- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- Python min 3.10 (if running locally for development)

---

### **2. Clone the Repository**
```bash
git clone https://github.com/pitergon/FastApiAliSearch.git
```

---

### **3. Configure Environment Variables**
Create a `.env` file in the directory and add the following:
``` 
    DB_USER=your_postgres_user
    DB_PASSWORD=your_postgres_password
    DB_HOST=your_postgres_host
    DB_PORT=5432
    DB_NAME=your_database_name
    
    REDIS_HOST=your_redis_host
    REDIS_PORT=6379
    REDIS_PASSWORD=your_redis_password

    JWT_SECRET_KEY=your_jwt_secret
    JWT_ALGORITHM=HS256
```

---

### **4. Configure the settings if needed**

You can change the settings in the `app/config.py` file:
```
# Set the base_url to the website
base_url = https://www.aliexpress.com/w/wholesale
# Max number of result pages for parsing. After 8 pages results are often  not relevant
max_page = 6
# Max number of pages without new products in search result
max_zero_pages = 2
# Rechecking the product name for compliance with the search query
filter_result = true
# Enable pause between requests
enable_pause = true
# Base value Max pause time in seconds. It automatically increases with the number of simultaneous searches.
max_pause_time = 2
# Enable save results to JSON file
enable_save_to_json = false
```
Also you can change expiration time for JWT token in `app/core/jwt_config.py` file:
```
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_MINUTES = 1440
```

### **5. Build and Run the Application**
Run the application using Docker Compose:
```bash
docker-compose up --build
```

This command will:

- Set up PostgreSQL and Redis containers.
- Build the FastAPI application Docker image.
- Start all services and link them using a Docker network.

Pay attention where located .env file, it should be in the same directory as docker-compose.yml file.
or you can specify the path to the .env file:
```bash 
docker-compose --env-file path/to/.env up --build
```

For next runs, you can use the following command:
```bash
docker-compose up
```

---

### **6. Initialize the Database**
Once the containers are running, execute the database initialization script:

```bash
docker exec -it fastapi python app/services/init_db.py
````
This script will:

- Create the database (if it doesn’t already exist).
- Set up the required tables.

---

### **7. Access the Application**
- App URL: http://localhost:8000/
- You should register a new user to access the search functionality.
- FastAPI Swagger UI (http://localhost:8000/docs) are disabled  
- Redis: Exposed on port 6379.
- PostgreSQL: Exposed on port 5432.

---

## **Stopping the Application**
To stop and remove all containers:
```bash
docker compose down
```