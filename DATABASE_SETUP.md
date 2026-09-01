# Database-connected Case Management System

Your frontend is now connected to SQLite through Flask.

## Run

1. Open a terminal in this project folder.
2. Install Flask if needed:
   `pip install flask`
3. Start:
   `python app.py`
4. Open:
   `http://127.0.0.1:5000`

A `case_management.db` file is automatically created beside `app.py`.

## API

- `GET/POST /api/cases`
- `GET/PUT/DELETE /api/cases/<id>`
- `GET/POST /api/agencies`
- `DELETE /api/agencies/<id>`
- `GET/POST /api/collaborations`
- `PUT/DELETE /api/collaborations/<id>`
- `GET /api/audit-logs`
- `GET /api/dashboard`

## Important

The database persists after restarting Flask. Do not delete `case_management.db` if you want to keep your records.

The original `app.py` is preserved as `app.py.original`.
