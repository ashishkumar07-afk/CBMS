from flask import Flask, request, jsonify, render_template
import sqlite3
from pathlib import Path
from datetime import datetime
import json

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "case_management.db"

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        category TEXT DEFAULT '',
        location TEXT DEFAULT '',
        status TEXT DEFAULT 'Active',
        priority TEXT DEFAULT 'Medium',
        lead_agency TEXT DEFAULT '',
        officer TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS agencies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        agency_type TEXT DEFAULT '',
        location TEXT DEFAULT '',
        contact TEXT DEFAULT '',
        email TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS collaborations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        requesting_agency TEXT DEFAULT '',
        target_agency TEXT DEFAULT '',
        collaboration_type TEXT DEFAULT '',
        details TEXT DEFAULT '',
        status TEXT DEFAULT 'Pending',
        created_at TEXT NOT NULL,
        FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        entity_type TEXT DEFAULT '',
        entity_id TEXT DEFAULT '',
        details TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()


def log_action(action, entity_type="", entity_id="", details=""):
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_logs(action, entity_type, entity_id, details, created_at) VALUES (?, ?, ?, ?, ?)",
        (action, entity_type, str(entity_id), details, datetime.now().isoformat(timespec="seconds"))
    )
    conn.commit()
    conn.close()


def body():
    return request.get_json(silent=True) or request.form.to_dict()


@app.route("/")
def index():
    # Use the existing template if available.
    for name in ("index.html", "dashboard.html"):
        if (BASE_DIR / "templates" / name).exists():
            return render_template(name)
    return """
    <h1>Case Management System</h1>
    <p>Database connected. Use the API endpoints: /api/cases, /api/agencies, /api/collaborations, /api/audit-logs</p>
    """


@app.route("/api/cases", methods=["GET", "POST"])
def cases():
    conn = get_db()
    if request.method == "GET":
        rows = conn.execute("SELECT * FROM cases ORDER BY id DESC").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    data = body()
    now = datetime.now().isoformat(timespec="seconds")
    case_id = data.get("case_id") or f"CASE-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    title = (data.get("title") or data.get("case_name") or "").strip()
    if not title:
        conn.close()
        return jsonify({"error": "Case title/name is required"}), 400

    try:
        cur = conn.execute("""
            INSERT INTO cases
            (case_id, title, description, category, location, status, priority, lead_agency, officer, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            case_id, title, data.get("description",""), data.get("category",""),
            data.get("location",""), data.get("status","Active"),
            data.get("priority","Medium"), data.get("lead_agency",""),
            data.get("officer",""), now, now
        ))
        conn.commit()
        case = conn.execute("SELECT * FROM cases WHERE id=?", (cur.lastrowid,)).fetchone()
        conn.close()
        log_action("CREATE", "case", cur.lastrowid, f"Created case {case_id}")
        return jsonify(dict(case)), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": f"Case ID '{case_id}' already exists"}), 409


@app.route("/api/cases/<int:case_id>", methods=["GET", "PUT", "DELETE"])
def case_detail(case_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Case not found"}), 404

    if request.method == "GET":
        conn.close()
        return jsonify(dict(row))

    if request.method == "DELETE":
        conn.execute("DELETE FROM cases WHERE id=?", (case_id,))
        conn.commit()
        conn.close()
        log_action("DELETE", "case", case_id, f"Deleted case {row['case_id']}")
        return jsonify({"success": True})

    data = body()
    allowed = {
        "title","description","category","location","status",
        "priority","lead_agency","officer"
    }
    fields = []
    values = []
    for key in allowed:
        if key in data:
            fields.append(f"{key}=?")
            values.append(data[key])
    if not fields:
        conn.close()
        return jsonify(dict(row))

    fields.append("updated_at=?")
    values.append(datetime.now().isoformat(timespec="seconds"))
    values.append(case_id)

    conn.execute(f"UPDATE cases SET {', '.join(fields)} WHERE id=?", values)
    conn.commit()
    updated = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    conn.close()
    log_action("UPDATE", "case", case_id, f"Updated case {row['case_id']}")
    return jsonify(dict(updated))


@app.route("/api/agencies", methods=["GET", "POST"])
def agencies():
    conn = get_db()
    if request.method == "GET":
        rows = conn.execute("SELECT * FROM agencies ORDER BY name").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    data = body()
    name = (data.get("name") or data.get("agency_name") or "").strip()
    if not name:
        conn.close()
        return jsonify({"error": "Agency name is required"}), 400

    try:
        cur = conn.execute("""
            INSERT INTO agencies(name, agency_type, location, contact, email, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name, data.get("agency_type",""), data.get("location",""),
            data.get("contact",""), data.get("email",""),
            datetime.now().isoformat(timespec="seconds")
        ))
        conn.commit()
        agency = conn.execute("SELECT * FROM agencies WHERE id=?", (cur.lastrowid,)).fetchone()
        conn.close()
        log_action("CREATE", "agency", cur.lastrowid, f"Registered agency {name}")
        return jsonify(dict(agency)), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": f"Agency '{name}' already exists"}), 409


@app.route("/api/agencies/<int:agency_id>", methods=["DELETE"])
def delete_agency(agency_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM agencies WHERE id=?", (agency_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Agency not found"}), 404
    conn.execute("DELETE FROM agencies WHERE id=?", (agency_id,))
    conn.commit()
    conn.close()
    log_action("DELETE", "agency", agency_id, f"Deleted agency {row['name']}")
    return jsonify({"success": True})


@app.route("/api/collaborations", methods=["GET", "POST"])
def collaborations():
    conn = get_db()
    if request.method == "GET":
        rows = conn.execute("""
            SELECT c.*, ca.case_id AS case_number, ca.title AS case_title
            FROM collaborations c
            JOIN cases ca ON ca.id = c.case_id
            ORDER BY c.id DESC
        """).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    data = body()
    raw_case = data.get("case_id")
    try:
        case_pk = int(raw_case)
    except (TypeError, ValueError):
        # Also accept CASE-... identifiers.
        row = conn.execute("SELECT id FROM cases WHERE case_id=?", (raw_case,)).fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Valid case_id is required"}), 400
        case_pk = row["id"]

    exists = conn.execute("SELECT id FROM cases WHERE id=?", (case_pk,)).fetchone()
    if not exists:
        conn.close()
        return jsonify({"error": "Case not found"}), 404

    cur = conn.execute("""
        INSERT INTO collaborations
        (case_id, requesting_agency, target_agency, collaboration_type, details, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        case_pk, data.get("requesting_agency",""), data.get("target_agency",""),
        data.get("collaboration_type",""), data.get("details",""),
        data.get("status","Pending"), datetime.now().isoformat(timespec="seconds")
    ))
    conn.commit()
    item = conn.execute("""
        SELECT c.*, ca.case_id AS case_number, ca.title AS case_title
        FROM collaborations c JOIN cases ca ON ca.id=c.case_id WHERE c.id=?
    """, (cur.lastrowid,)).fetchone()
    conn.close()
    log_action("CREATE", "collaboration", cur.lastrowid, f"Created collaboration for case {item['case_number']}")
    return jsonify(dict(item)), 201


@app.route("/api/collaborations/<int:item_id>", methods=["PUT", "DELETE"])
def collaboration_detail(item_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM collaborations WHERE id=?", (item_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Collaboration not found"}), 404

    if request.method == "DELETE":
        conn.execute("DELETE FROM collaborations WHERE id=?", (item_id,))
        conn.commit()
        conn.close()
        log_action("DELETE", "collaboration", item_id, "Deleted collaboration request")
        return jsonify({"success": True})

    data = body()
    fields, values = [], []
    for key in ("requesting_agency","target_agency","collaboration_type","details","status"):
        if key in data:
            fields.append(f"{key}=?")
            values.append(data[key])
    if fields:
        values.append(item_id)
        conn.execute(f"UPDATE collaborations SET {', '.join(fields)} WHERE id=?", values)
        conn.commit()
    updated = conn.execute("SELECT * FROM collaborations WHERE id=?", (item_id,)).fetchone()
    conn.close()
    log_action("UPDATE", "collaboration", item_id, "Updated collaboration request")
    return jsonify(dict(updated))


@app.route("/api/audit-logs", methods=["GET"])
def audit_logs():
    conn = get_db()
    rows = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    conn = get_db()
    result = {
        "total_cases": conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
        "active_cases": conn.execute("SELECT COUNT(*) FROM cases WHERE status='Active'").fetchone()[0],
        "closed_cases": conn.execute("SELECT COUNT(*) FROM cases WHERE status='Closed'").fetchone()[0],
        "total_agencies": conn.execute("SELECT COUNT(*) FROM agencies").fetchone()[0],
        "pending_collaborations": conn.execute("SELECT COUNT(*) FROM collaborations WHERE status='Pending'").fetchone()[0],
    }
    conn.close()
    return jsonify(result)


# Compatibility routes for simple existing frontend forms.
@app.route("/add_case", methods=["POST"])
def add_case_compat():
    return cases()


@app.route("/register_agency", methods=["POST"])
def register_agency_compat():
    return agencies()


@app.route("/interagency_request", methods=["POST"])
def interagency_request_compat():
    return collaborations()


@app.route("/add_agency", methods=["POST"])
def add_agency_compat():
    return agencies()


@app.route("/add_request", methods=["POST"])
def add_request_compat():
    return collaborations()


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
else:
    init_db()
