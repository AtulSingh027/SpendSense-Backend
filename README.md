# SpendSense — Personal Expense Tracker API

SpendSense is a high-performance backend API built with FastAPI that acts as a personal finance tracker. It ingests and parses transactional SMS alerts from major Indian banks (HDFC, ICICI, Axis, SBI, BOB, etc.) to automatically extract transaction details, track expenses, categorize them, and generate dashboard metrics.

---

## 🛠️ Tech Stack & Prerequisites

*   **Runtime**: Python 3.10+
*   **Framework**: FastAPI (Pydantic v2, SQLAlchemy ORM)
*   **Database**: MySQL 8.0+
*   **Libraries**: `bcrypt` (password hashing), `python-jose` (JWT auth), `pytest` (testing)
*   **Docker** & **Docker Compose** (for localized database development)

---

## 🚀 Setup Instructions

### 1. Set Up Virtual Environment & Dependencies

From the project root directory, initialize a python virtual environment and install the required modules:

```bash
# Create the virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create/verify the `.env` file in the project root with the following configuration:

```env
DATABASE_NAME=spend_sense
DATABASE_USER=root
DATABASE_PASSWORD=12345
DATABASE_HOST=127.0.0.1
DATABASE_PORT=3306

JWT_SECRET=f7a3e9c1d4b8f2a6e0c5d9b3a7f1e4c8d2b6a0f5e9c3d7b1a5f9e3c7d1b5a9
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=1440
```

### 3. Spin Up MySQL Database Container

Use Docker Compose to run a local MySQL 8.0 instance:

```bash
# Start MySQL in detached mode
docker compose up -d
```
> [!NOTE]
> The default `docker-compose.yml` binds the container MySQL port `3306` to host port `3307`. If you are connecting from your host directly to the docker database container, use port `3307` and the root password `SpendSense@2024`. If you are running MySQL locally on your host directly, configure `.env` to point to port `3306`.

### 4. Initialize Database Schema

Once your MySQL instance is running, create the database and import the tables using the migration schema script:

```bash
# Log in and create the database if not exists (using container mapped port 3307)
mysql -h 127.0.0.1 -P 3307 -u root -pSpendSense@2024 -e "CREATE DATABASE IF NOT EXISTS spend_sense;"

# Run the schema migration script
mysql -h 127.0.0.1 -P 3307 -u root -pSpendSense@2024 spend_sense < helpers/migrations/schema.sql
```

---

## 💻 Running the Application

To start the FastAPI development server:

```bash
# Ensure virtual environment is active
source .venv/bin/activate

# Start the uvicorn server
uvicorn app:app --reload
```

The server will spin up at `http://127.0.0.1:8000`. 
*   Interactive API docs (Swagger UI) are available at: `http://127.0.0.1:8000/docs`
*   ReDoc documentation is available at: `http://127.0.0.1:8000/redoc`

---

## 🧪 Running the Test Suite

We use `pytest` for unit and integration testing. Database tests run automatically inside an isolated environment structure.

To execute tests:

```bash
# Run the complete test suite
pytest tests/ -v
```

---

## 📂 Project Directory Structure

```
SpendSense/
├── api/                  # FastAPI router versions (v1, auth, sms, dashboard, etc.)
├── configs/              # DB session & connection configurations
├── helpers/              # Middlewares, DB migrations schema
├── models/               # SQLAlchemy Models (User, Transaction, Category, etc.)
├── schemas/              # Pydantic schemas for request/response serialization
├── services/             # Core business services (regex SMS parsing strategies)
└── tests/                # Automated pytest files
```
