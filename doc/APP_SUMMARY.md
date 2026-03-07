# BeSTiapp - Scout Camp Management System

## 🎯 Business Goal
BeSTiapp (Scout Camp Ranking & Management) is a centralized platform designed to monitor and coordinate activities during a scout camp. Its primary objectives are:
- **Leaderboard & Competition**: Tracking patrol (pattuglia) progress through a points-based challenge system.
- **Logistics Coordination**: Managing the availability and reservation of physical spaces (terreni) using interactive mapping to avoid overlaps.
- **Transparency**: Providing real-time updates on rankings and activity timelines to all participants.

---

## 🛠️ Tech Stack
- **Backend**: Python 3.12+ with [FastAPI](https://fastapi.tiangolo.com/).
- **Database**: [SQLite](https://www.sqlite.org/) managed via [SQLAlchemy 2.0](https://www.sqlalchemy.org/).
- **Web Server**: [Uvicorn](https://www.uvicorn.org/).
- **Frontend**: [Jinja2](https://jinja.palletsprojects.com/) templates with Vanilla CSS and JavaScript.
- **Maps**: [Leaflet.js](https://leafletjs.com/) for interactive polygon rendering and geofencing.
- **Environment/Dependencies**: [uv](https://github.com/astral-sh/uv) for lightning-fast package management.
- **Deployment**: [Docker](https://www.docker.com/) and [Fly.io](https://fly.io/).
- **Quality Assurance**: `pytest`, `playwright` (E2E), `ruff` (linting), and `pyright` (typing).

---

## 🏗️ Architecture
The application follows a standard FastAPI structure:
- `app/main.py`: Application entry point and global middleware/exception handlers.
- `app/models.py`: SQLAlchemy data models defining the core entities.
- `app/routers/`: Modular route handlers:
    - `public.py`: Main logic for rankings, maps, timelines, and the reservation system.
    - `admin.py`: Management interface for administrative tasks.
    - `auth.py`: JWT-based authentication logic.
- `app/templates/`: UI components organized by feature.
- `app/static/`: Static assets (CSS, JS, images).
- `data/seed/`: CSV files used to bootstrap the database with initial units, patrols, and challenges.
- `geo/` & `kml_to_terreni.py`: Specialized tools for converting KML/KMZ files into database-ready terrain polygons.

---

## 📊 Core Entities & Behavior
### 1. Units & Patrols (`Unita`, `Pattuglia`)
- Users belong to **Units** (e.g., "Reparto" or "Posto").
- Units are subdivided into **Patrols**, which are the primary competitive entities.
- Patrols earn points by completing challenges.

### 2. Challenges & Rankings (`Challenge`, `Completion`)
- **Challenges** have specific point values and can be flagged as "fungo" (special/bonus).
- **Completions** link a patrol to a challenge with a timestamp.
- The **Leaderboard** displays real-time rankings filtered by subcamp (Alpino, Montano, etc.).

### 3. Terrains & Reservations (`Terreno`, `Prenotazione`)
- **Terrains** are geographic areas defined by polygons (JSON coordinates).
- Each terrain has tags (e.g., SPORT, CERIMONIA) and access restrictions based on unit type.
- The **Reservation System** allows units to book time slots (1-4 hours).
- Overlap logic prevents multiple approved bookings for the same terrain at the same time.

### 4. Role-Based Access Control (RBAC)
- **Unit**: Read-only access to rankings; can request terrain reservations.
- **Tech (Staff)**: "Referee" role; can register challenge completions and approve/reject terrain requests.
- **Admin**: Full system control; user management, data resets, and core entity configuration.

---

## 🔄 Common Workflows
1. **Bootstrap**: Run `init_db.py` to seed the database from CSVs and KML polygons.
2. **Point Entry**: Staff logs in to record a challenge completion for a patrol, automatically updating the leaderboard.
3. **Space Booking**: A unit views the interactive map, checks availability for a specific time slot, and submits a reservation request.
4. **Approval**: Staff reviews pending requests and approves them, triggering automated conflict resolution (overlapping pending requests are rejected).
