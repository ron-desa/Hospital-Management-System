# controllers/routes.py
from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from datetime import datetime

from models.models import get_db_connection

main_bp = Blueprint("main", __name__)


# --------- Helpers ---------
def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("main.login"))
        return view_func(*args, **kwargs)
    return wrapped


def role_required(role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if "user_id" not in session or session.get("role") != role:
                flash("Unauthorized access.", "danger")
                return redirect(url_for("main.login"))
            return view_func(*args, **kwargs)
        return wrapped
    return decorator


# --------- Auth & Index ---------
@main_bp.route("/")
def index():
    if "user_id" in session and "role" in session:
        role = session["role"]
        if role == "admin":
            return redirect(url_for("main.admin_dashboard"))
        elif role == "doctor":
            return redirect(url_for("main.doctor_dashboard"))
        elif role == "patient":
            return redirect(url_for("main.patient_dashboard"))
    return redirect(url_for("main.login"))


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ? AND is_active = 1;", (username,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["full_name"] = user["full_name"]
            flash("Logged in successfully.", "success")

            if user["role"] == "admin":
                return redirect(url_for("main.admin_dashboard"))
            elif user["role"] == "doctor":
                return redirect(url_for("main.doctor_dashboard"))
            else:
                return redirect(url_for("main.patient_dashboard"))
        else:
            flash("Invalid username or password", "danger")

    return render_template("login.html")


@main_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("main.login"))


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    # Only patient self-registration allowed
    if request.method == "POST":
        full_name = request.form.get("full_name")
        username = request.form.get("username")
        email = request.form.get("email")
        phone = request.form.get("phone")
        age = request.form.get("age") or None
        gender = request.form.get("gender")
        address = request.form.get("address")
        emergency_contact = request.form.get("emergency_contact")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        conn = get_db_connection()
        cur = conn.cursor()

        # Check if username exists
        cur.execute("SELECT id FROM users WHERE username = ?;", (username,))
        if cur.fetchone():
            conn.close()
            flash("Username already taken.", "warning")
            return render_template("register.html")

        now = datetime.utcnow().isoformat()
        password_hash = generate_password_hash(password)

        # Insert into users
        cur.execute("""
            INSERT INTO users (username, password_hash, full_name, email, phone, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 'patient', 1, ?);
        """, (username, password_hash, full_name, email, phone, now))
        user_id = cur.lastrowid

        # Insert into patients
        cur.execute("""
            INSERT INTO patients (user_id, age, gender, address, emergency_contact, is_blacklisted)
            VALUES (?, ?, ?, ?, ?, 0);
        """, (user_id, age, gender, address, emergency_contact))

        conn.commit()
        conn.close()

        flash("Registration successful. You can now log in.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html")


# --------- Dashboards ---------
@main_bp.route("/admin/dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS c FROM doctors;")
    total_doctors = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM patients;")
    total_patients = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM appointments;")
    total_appointments = cur.fetchone()["c"]

    conn.close()

    stats = {
        "total_doctors": total_doctors,
        "total_patients": total_patients,
        "total_appointments": total_appointments
    }

    return render_template("dashboard_admin.html", stats=stats)


@main_bp.route("/doctor/dashboard")
@login_required
@role_required("doctor")
def doctor_dashboard():
    # TODO: show upcoming appointments for this doctor, list of patients
    return render_template("dashboard_doctor.html")


@main_bp.route("/patient/dashboard")
@login_required
@role_required("patient")
def patient_dashboard():
    # fetch departments for listing
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM departments ORDER BY name;")
    departments = cur.fetchall()
    conn.close()

    return render_template("dashboard_patient.html", departments=departments)


# --------- Admin: Manage Doctors ---------
@main_bp.route("/admin/doctors")
@login_required
@role_required("admin")
def admin_doctors():
    q = request.args.get("q", "").strip()
    conn = get_db_connection()
    cur = conn.cursor()

    base_query = """
        SELECT d.id AS doctor_id,
               u.full_name,
               u.username,
               u.email,
               u.phone,
               d.room_no,
               d.is_blacklisted,
               dept.name AS dept_name
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        LEFT JOIN departments dept ON d.department_id = dept.id
    """

    params = []
    if q:
        base_query += """
            WHERE u.full_name LIKE ? OR dept.name LIKE ?
        """
        like_q = f"%{q}%"
        params.extend([like_q, like_q])

    base_query += " ORDER BY u.full_name;"

    cur.execute(base_query, params)
    doctors = cur.fetchall()
    conn.close()

    return render_template("admin_doctors.html", doctors=doctors)


@main_bp.route("/admin/doctors/add", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_add_doctor():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM departments ORDER BY name;")
    departments = cur.fetchall()

    if request.method == "POST":
        full_name = request.form.get("full_name")
        username = request.form.get("username")
        email = request.form.get("email")
        phone = request.form.get("phone")
        department_id = request.form.get("department_id") or None
        room_no = request.form.get("room_no")
        bio = request.form.get("bio")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            conn.close()
            return render_template("admin_doctor_form.html", departments=departments)

        # Check username uniqueness
        cur.execute("SELECT id FROM users WHERE username = ?;", (username,))
        if cur.fetchone():
            flash("Username already taken.", "warning")
            conn.close()
            return render_template("admin_doctor_form.html", departments=departments)

        now = datetime.utcnow().isoformat()
        password_hash = generate_password_hash(password)

        # Insert into users table with role=doctor
        cur.execute("""
            INSERT INTO users (username, password_hash, full_name, email, phone, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 'doctor', 1, ?);
        """, (username, password_hash, full_name, email, phone, now))
        user_id = cur.lastrowid

        # Insert into doctors table
        cur.execute("""
            INSERT INTO doctors (user_id, department_id, bio, room_no, is_blacklisted)
            VALUES (?, ?, ?, ?, 0);
        """, (user_id, department_id, bio, room_no))

        conn.commit()
        conn.close()

        flash("Doctor created successfully.", "success")
        return redirect(url_for("main.admin_doctors"))

    conn.close()
    return render_template("admin_doctor_form.html", departments=departments)


@main_bp.route("/admin/doctors/<int:doctor_id>/toggle_blacklist")
@login_required
@role_required("admin")
def admin_toggle_doctor_blacklist(doctor_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT is_blacklisted FROM doctors WHERE id = ?;", (doctor_id,))
    doc = cur.fetchone()

    if not doc:
        conn.close()
        flash("Doctor not found.", "danger")
        return redirect(url_for("main.admin_doctors"))

    new_status = 0 if doc["is_blacklisted"] else 1
    cur.execute("UPDATE doctors SET is_blacklisted = ? WHERE id = ?;", (new_status, doctor_id))
    conn.commit()
    conn.close()

    flash("Doctor status updated.", "info")
    return redirect(url_for("main.admin_doctors"))
