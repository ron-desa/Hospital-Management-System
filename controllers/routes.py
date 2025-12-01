# controllers/routes.py
from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
# from datetime import datetime, date as date_cls
from datetime import datetime, date as date_cls, timedelta

import sqlite3

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


def get_current_patient_id():
    if "user_id" not in session:
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT p.id FROM patients p JOIN users u ON p.user_id = u.id WHERE u.id = ?;",
        (session["user_id"],),
    )
    row = cur.fetchone()
    conn.close()
    return row["id"] if row else None


def get_current_doctor_id():
    if "user_id" not in session:
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT d.id FROM doctors d JOIN users u ON d.user_id = u.id WHERE u.id = ?;",
        (session["user_id"],),
    )
    row = cur.fetchone()
    conn.close()
    return row["id"] if row else None


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
        cur.execute(
            """
            INSERT INTO users (username, password_hash, full_name, email, phone, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 'patient', 1, ?);
        """,
            (username, password_hash, full_name, email, phone, now),
        )
        user_id = cur.lastrowid

        # Insert into patients
        cur.execute(
            """
            INSERT INTO patients (user_id, age, gender, address, emergency_contact, is_blacklisted)
            VALUES (?, ?, ?, ?, ?, 0);
        """,
            (user_id, age, gender, address, emergency_contact),
        )

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
        "total_appointments": total_appointments,
    }

    return render_template("dashboard_admin.html", stats=stats)


@main_bp.route("/doctor/dashboard")
@login_required
@role_required("doctor")
def doctor_dashboard():
    return render_template("dashboard_doctor.html")


@main_bp.route("/patient/dashboard")
@login_required
@role_required("patient")
def patient_dashboard():
    conn = get_db_connection()
    cur = conn.cursor()

    # departments
    cur.execute("SELECT * FROM departments ORDER BY name;")
    departments = cur.fetchall()

    # doctor availability for next 7 days
    today = date_cls.today()
    max_day = today + timedelta(days=7)
    cur.execute(
        """
        SELECT da.date,
               da.start_time,
               da.end_time,
               du.full_name AS doctor_name,
               dept.name AS dept_name
        FROM doctor_availability da
        JOIN doctors d ON da.doctor_id = d.id
        JOIN users du ON d.user_id = du.id
        LEFT JOIN departments dept ON d.department_id = dept.id
        WHERE da.is_available = 1
          AND da.date >= ?
          AND da.date <= ?
        ORDER BY da.date, da.start_time, doctor_name;
        """,
        (today.isoformat(), max_day.isoformat()),
    )
    availability = cur.fetchall()

    conn.close()

    return render_template(
        "dashboard_patient.html",
        departments=departments,
        availability=availability,
    )



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
        cur.execute(
            """
            INSERT INTO users (username, password_hash, full_name, email, phone, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 'doctor', 1, ?);
        """,
            (username, password_hash, full_name, email, phone, now),
        )
        user_id = cur.lastrowid

        # Insert into doctors table
        cur.execute(
            """
            INSERT INTO doctors (user_id, department_id, bio, room_no, is_blacklisted)
            VALUES (?, ?, ?, ?, 0);
        """,
            (user_id, department_id, bio, room_no),
        )

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


# --------- Patient: Find Doctors & Book ---------
@main_bp.route("/patient/doctors")
@login_required
@role_required("patient")
def patient_doctors():
    q = request.args.get("q", "").strip()
    department_id = request.args.get("department_id", "").strip()

    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT d.id AS doctor_id,
               u.full_name,
               u.email,
               u.phone,
               d.room_no,
               dept.name AS dept_name
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        LEFT JOIN departments dept ON d.department_id = dept.id
        WHERE d.is_blacklisted = 0 AND u.is_active = 1
    """
    params = []

    if department_id:
        query += " AND dept.id = ?"
        params.append(department_id)

    if q:
        query += " AND (u.full_name LIKE ? OR dept.name LIKE ?)"
        like_q = f"%{q}%"
        params.extend([like_q, like_q])

    query += " ORDER BY u.full_name;"

    cur.execute(query, params)
    doctors = cur.fetchall()

    cur.execute("SELECT * FROM departments ORDER BY name;")
    departments = cur.fetchall()

    conn.close()

    return render_template("patient_doctors.html", doctors=doctors, departments=departments)


@main_bp.route("/patient/book/<int:doctor_id>", methods=["GET", "POST"])
@login_required
@role_required("patient")
def patient_book_appointment(doctor_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch doctor info
    cur.execute(
        """
        SELECT d.id AS doctor_id,
               u.full_name,
               u.email,
               u.phone,
               d.room_no,
               d.is_blacklisted,
               dept.name AS dept_name
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        LEFT JOIN departments dept ON d.department_id = dept.id
        WHERE d.id = ?;
        """,
        (doctor_id,),
    )
    doctor = cur.fetchone()

    if not doctor or doctor["is_blacklisted"]:
        conn.close()
        flash("Doctor not available.", "danger")
        return redirect(url_for("main.patient_doctors"))

    # availability for this doctor for next 7 days
    today = date_cls.today()
    max_day = today + timedelta(days=7)
    cur.execute(
        """
        SELECT * FROM doctor_availability
        WHERE doctor_id = ?
          AND is_available = 1
          AND date >= ?
          AND date <= ?
        ORDER BY date, start_time;
        """,
        (doctor_id, today.isoformat(), max_day.isoformat()),
    )
    availability = cur.fetchall()

    if request.method == "POST":
        date_str = request.form.get("date")
        time_str = request.form.get("time")

        if not date_str or not time_str:
            flash("Please select date and time.", "warning")
            conn.close()
            return render_template("patient_book_appointment.html", doctor=doctor, availability=availability)

        patient_id = get_current_patient_id()
        if not patient_id:
            conn.close()
            flash("Patient profile not found.", "danger")
            return redirect(url_for("main.patient_dashboard"))

        # Check that chosen time falls within an availability window
        cur.execute(
            """
            SELECT *
            FROM doctor_availability
            WHERE doctor_id = ?
              AND is_available = 1
              AND date = ?
              AND start_time <= ?
              AND end_time >= ?;
            """,
            (doctor_id, date_str, time_str, time_str),
        )
        slot = cur.fetchone()
        if not slot:
            flash("Doctor is not available at the selected date/time. Please choose within the available slots.", "danger")
            conn.close()
            return render_template("patient_book_appointment.html", doctor=doctor, availability=availability)

        now = datetime.utcnow().isoformat()
        try:
            cur.execute(
                """
                INSERT INTO appointments (patient_id, doctor_id, date, time, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'Booked', ?, ?);
                """,
                (patient_id, doctor_id, date_str, time_str, now, now),
            )
            conn.commit()
            flash("Appointment booked successfully.", "success")
        except sqlite3.IntegrityError:
            flash("This slot is already booked for the doctor. Please choose another time.", "danger")
            conn.rollback()
            conn.close()
            return render_template("patient_book_appointment.html", doctor=doctor, availability=availability)

        conn.close()
        return redirect(url_for("main.patient_appointments"))

    conn.close()
    return render_template("patient_book_appointment.html", doctor=doctor, availability=availability)



# --------- Patient: View & Cancel Appointments ---------
@main_bp.route("/patient/appointments")
@login_required
@role_required("patient")
def patient_appointments():
    patient_id = get_current_patient_id()
    if not patient_id:
        flash("Patient profile not found.", "danger")
        return redirect(url_for("main.patient_dashboard"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT a.*, u.full_name AS doctor_name, dept.name AS dept_name
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        JOIN users u ON d.user_id = u.id
        LEFT JOIN departments dept ON d.department_id = dept.id
        WHERE a.patient_id = ?
        ORDER BY a.date DESC, a.time DESC;
        """,
        (patient_id,),
    )
    rows = cur.fetchall()
    conn.close()

    today_str = date_cls.today().isoformat()
    upcoming = []
    past = []

    for r in rows:
        # simple classification: date >= today => upcoming
        if r["date"] >= today_str and r["status"] == "Booked":
            upcoming.append(r)
        else:
            past.append(r)

    return render_template("patient_appointments.html", upcoming=upcoming, past=past)


@main_bp.route("/patient/appointments/<int:appointment_id>/cancel")
@login_required
@role_required("patient")
def patient_cancel_appointment(appointment_id):
    patient_id = get_current_patient_id()
    if not patient_id:
        flash("Patient profile not found.", "danger")
        return redirect(url_for("main.patient_dashboard"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM appointments WHERE id = ? AND patient_id = ?;",
        (appointment_id, patient_id),
    )
    appt = cur.fetchone()

    if not appt:
        conn.close()
        flash("Appointment not found.", "danger")
        return redirect(url_for("main.patient_appointments"))

    if appt["status"] != "Booked":
        conn.close()
        flash("Only booked appointments can be cancelled.", "warning")
        return redirect(url_for("main.patient_appointments"))

    now = datetime.utcnow().isoformat()
    cur.execute(
        """
        UPDATE appointments
        SET status = 'Cancelled', updated_at = ?
        WHERE id = ?;
        """,
        (now, appointment_id),
    )
    conn.commit()
    conn.close()

    flash("Appointment cancelled.", "info")
    return redirect(url_for("main.patient_appointments"))


# --------- Doctor: View & Update Appointments ---------
@main_bp.route("/doctor/appointments")
@login_required
@role_required("doctor")
def doctor_appointments():
    doctor_id = get_current_doctor_id()
    if not doctor_id:
        flash("Doctor profile not found.", "danger")
        return redirect(url_for("main.doctor_dashboard"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT a.*, u.full_name AS patient_name, u.phone
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN users u ON p.user_id = u.id
        WHERE a.doctor_id = ?
        ORDER BY a.date DESC, a.time DESC;
        """,
        (doctor_id,),
    )
    rows = cur.fetchall()
    conn.close()

    today_str = date_cls.today().isoformat()
    upcoming = []
    past = []

    for r in rows:
        if r["date"] >= today_str and r["status"] == "Booked":
            upcoming.append(r)
        else:
            past.append(r)

    return render_template("doctor_appointments.html", upcoming=upcoming, past=past)


@main_bp.route("/doctor/appointments/<int:appointment_id>/status/<new_status>")
@login_required
@role_required("doctor")
def doctor_update_appointment_status(appointment_id, new_status):
    doctor_id = get_current_doctor_id()
    if not doctor_id:
        flash("Doctor profile not found.", "danger")
        return redirect(url_for("main.doctor_dashboard"))

    if new_status not in ("Completed", "Cancelled"):
        flash("Invalid status.", "danger")
        return redirect(url_for("main.doctor_appointments"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM appointments WHERE id = ? AND doctor_id = ?;",
        (appointment_id, doctor_id),
    )
    appt = cur.fetchone()

    if not appt:
        conn.close()
        flash("Appointment not found.", "danger")
        return redirect(url_for("main.doctor_appointments"))

    if appt["status"] != "Booked":
        conn.close()
        flash("Only booked appointments can be updated.", "warning")
        return redirect(url_for("main.doctor_appointments"))

    now = datetime.utcnow().isoformat()
    cur.execute(
        """
        UPDATE appointments
        SET status = ?, updated_at = ?
        WHERE id = ?;
        """,
        (new_status, now, appointment_id),
    )
    conn.commit()
    conn.close()

    flash(f"Appointment marked as {new_status}.", "success")
    return redirect(url_for("main.doctor_appointments"))

# --------- Doctor: Manage Availability (next 7 days) ---------
@main_bp.route("/doctor/availability", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def doctor_availability():
    doctor_id = get_current_doctor_id()
    if not doctor_id:
        flash("Doctor profile not found.", "danger")
        return redirect(url_for("main.doctor_dashboard"))

    today = date_cls.today()
    max_day = today + timedelta(days=7)

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        date_str = request.form.get("date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")

        if not date_str or not start_time or not end_time:
            flash("Please fill all fields.", "warning")
        else:
            try:
                d = date_cls.fromisoformat(date_str)
            except ValueError:
                d = None

            if not d:
                flash("Invalid date.", "danger")
            elif d < today or d > max_day:
                flash("Availability must be within the next 7 days.", "warning")
            elif start_time >= end_time:
                flash("Start time must be before end time.", "warning")
            else:
                cur.execute(
                    """
                    INSERT INTO doctor_availability (doctor_id, date, start_time, end_time, max_appointments, is_available)
                    VALUES (?, ?, ?, ?, ?, 1);
                    """,
                    (doctor_id, date_str, start_time, end_time, 10),
                )
                conn.commit()
                flash("Availability added.", "success")

    # fetch availability for this doctor for next 7 days
    cur.execute(
        """
        SELECT * FROM doctor_availability
        WHERE doctor_id = ?
          AND date >= ?
          AND date <= ?
          AND is_available = 1
        ORDER BY date, start_time;
        """,
        (doctor_id, today.isoformat(), max_day.isoformat()),
    )
    slots = cur.fetchall()
    conn.close()

    return render_template("doctor_availability.html", slots=slots, today=today, max_day=max_day)


@main_bp.route("/doctor/availability/<int:slot_id>/delete")
@login_required
@role_required("doctor")
def doctor_delete_availability(slot_id):
    doctor_id = get_current_doctor_id()
    if not doctor_id:
        flash("Doctor profile not found.", "danger")
        return redirect(url_for("main.doctor_dashboard"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, doctor_id FROM doctor_availability WHERE id = ?;",
        (slot_id,),
    )
    slot = cur.fetchone()

    if not slot or slot["doctor_id"] != doctor_id:
        conn.close()
        flash("Availability slot not found.", "danger")
        return redirect(url_for("main.doctor_availability"))

    cur.execute("DELETE FROM doctor_availability WHERE id = ?;", (slot_id,))
    conn.commit()
    conn.close()

    flash("Availability slot removed.", "info")
    return redirect(url_for("main.doctor_availability"))


# --------- Doctor: Add/Edit Treatment ---------
@main_bp.route("/doctor/appointments/<int:appointment_id>/treatment", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def doctor_treatment(appointment_id):
    doctor_id = get_current_doctor_id()
    if not doctor_id:
        flash("Doctor profile not found.", "danger")
        return redirect(url_for("main.doctor_dashboard"))

    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch appointment + existing treatment (if any)
    cur.execute(
        """
        SELECT a.*,
               u.full_name AS patient_name,
               t.diagnosis,
               t.prescription,
               t.notes
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN users u ON p.user_id = u.id
        LEFT JOIN treatments t ON t.appointment_id = a.id
        WHERE a.id = ? AND a.doctor_id = ?;
        """,
        (appointment_id, doctor_id),
    )
    appt = cur.fetchone()

    if not appt:
        conn.close()
        flash("Appointment not found.", "danger")
        return redirect(url_for("main.doctor_appointments"))

    if request.method == "POST":
        diagnosis = request.form.get("diagnosis")
        prescription = request.form.get("prescription")
        notes = request.form.get("notes")
        now = datetime.utcnow().isoformat()

        # If still Booked, mark as Completed when treatment is saved
        if appt["status"] == "Booked":
            cur.execute(
                """
                UPDATE appointments
                SET status = 'Completed', updated_at = ?
                WHERE id = ?;
                """,
                (now, appointment_id),
            )

        # Check if treatment already exists
        cur.execute(
            "SELECT id FROM treatments WHERE appointment_id = ?;",
            (appointment_id,),
        )
        existing = cur.fetchone()

        if existing:
            cur.execute(
                """
                UPDATE treatments
                SET diagnosis = ?, prescription = ?, notes = ?, created_at = ?
                WHERE appointment_id = ?;
                """,
                (diagnosis, prescription, notes, now, appointment_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO treatments (appointment_id, diagnosis, prescription, notes, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (appointment_id, diagnosis, prescription, notes, now),
            )

        conn.commit()
        conn.close()

        flash("Treatment details saved.", "success")
        return redirect(url_for("main.doctor_appointments"))

    # GET: show form with existing data (if any)
    conn.close()
    return render_template("doctor_treatment_form.html", appt=appt)


# --------- Patient: Appointment details with treatment ---------
@main_bp.route("/patient/appointments/<int:appointment_id>")
@login_required
@role_required("patient")
def patient_appointment_details(appointment_id):
    patient_id = get_current_patient_id()
    if not patient_id:
        flash("Patient profile not found.", "danger")
        return redirect(url_for("main.patient_dashboard"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT a.*,
               du.full_name AS doctor_name,
               dept.name AS dept_name,
               t.diagnosis,
               t.prescription,
               t.notes
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        JOIN users du ON d.user_id = du.id
        LEFT JOIN departments dept ON d.department_id = dept.id
        LEFT JOIN treatments t ON t.appointment_id = a.id
        WHERE a.id = ? AND a.patient_id = ?;
        """,
        (appointment_id, patient_id),
    )
    appt = cur.fetchone()
    conn.close()

    if not appt:
        flash("Appointment not found.", "danger")
        return redirect(url_for("main.patient_appointments"))

    return render_template("patient_appointment_details.html", appt=appt)
