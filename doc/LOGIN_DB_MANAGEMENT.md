# Login System & Database Management

## 🔐 Authentication & Session Management
BeSTiapp uses a custom JWT-based (JSON Web Token) authentication system integrated with FastAPI's dependency injection.

### Key Components
- **Password Hashing**: Uses `passlib[bcrypt]` or `argon2-cffi` (as seen in `pyproject.toml`) to securely store user credentials.
- **JWT Tokens**: Tokens are generated on successful login (`app/auth.py`) and stored in a **HTTP-only cookie** (`access_token`) for enhanced security against XSS.
- **Role-Based Access (RBAC)**:
    - `get_authenticated_user`: Ensures the user is logged in.
    - `get_tech_user`: Restricted to 'tech' or 'admin' roles (used for point entry and terrain management).
    - `get_admin_user`: Restricted to 'admin' role (full system management).

### Login Flow
1. User submits credentials and a **selected role** (reparto, posto, staff, direzione).
2. The server verifies the password and confirms the user actually possesses the role they claimed.
3. If valid, a JWT is issued with the username as the subject (`sub`).

---

## 💾 Database Architecture
### Engine & ORM
- **Engine**: SQLite (via `sqlalchemy`).
- **Patterns**: Uses SQLAlchemy 2.0 `Mapped` and `mapped_column` syntax for type-safe models.
- **Session Management**: A FastAPI dependency (`get_db`) provides a scoped database session per request, ensuring clean resource cleanup.

### Data Management Workflows
- **Initialization**: `init_db.py` contains the logic to drop and recreate tables, and then populate them from `data/seed/*.csv`.
- **Reset Logic**: Admins can trigger a full database reset via the UI (`/admin/reset-db`), which re-runs the `init_db` script.
- **Persistence**: While using SQLite, the app is "Cloud-Ready" for platforms like Fly.io where the `.db` file is stored on a persistent volume.

### Schema Highlights
- **User Table**: Stores username, email, `password_hash`, `role`, and optional `unita_id` (foreign key to `unita`).
- **Unit Table**: Root organizational unit, categorizing entities into "Reparto" (Scouts) or "Posto" (Rovers/Pioneers).
- **Auditability**: Completion and Reservation records link back to the user or unit that created them, providing a clear history of actions.
