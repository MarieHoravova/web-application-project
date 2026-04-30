# Hotel Reservation System

A full-stack web application for managing hotel reservations, built with FastAPI and SQLite as a school project at MENDELU.

## Tech Stack

- **Backend:** Python, FastAPI
- **Database:** SQLite (raw SQL via repository pattern)
- **Templating:** Jinja2
- **Auth:** JWT (PyJWT) + bcrypt password hashing
- **Frontend:** HTML, CSS

## Features

- User registration and login with JWT-based authentication
- Role-based access control (guest, receptionist, admin)
- Room and room type management
- Reservation creation and management
- Payment tracking
- Public rooms browsing and gallery
- Contact form with admin message inbox
- User profile management

## Architecture

The project follows a layered architecture:

```
pages/        → FastAPI routers (request handling)
services/     → Business logic
repositories/ → Database access (raw SQL)
models/       → Pydantic schemas
domain/       → Constants and shared types
core/         → Config and security utilities
```

## Getting Started

**1. Clone the repository**
```bash
git clone <repo-url>
cd web-application-project
```

**2. Create and activate a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set environment variables**
```bash
cp .env.example .env
# Edit .env and set a strong SECRET_KEY
```

**5. Run the application**
```bash
uvicorn main:app --reload
```

The app will be available at `http://localhost:8000`.

## Project Structure

```
.
├── main.py                  # App factory and router registration
├── core/
│   ├── config.py            # Settings (loaded from environment)
│   └── security.py          # JWT and bcrypt utilities
├── database/
│   └── database.py          # SQLite connection context manager
├── pages/                   # Route handlers
├── services/                # Business logic layer
├── repositories/            # Data access layer
├── models/                  # Pydantic request/response schemas
├── templates/               # Jinja2 HTML templates
├── static/                  # CSS
└── img/                     # Static images
```
