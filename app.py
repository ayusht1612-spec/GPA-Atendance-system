from flask import Flask, render_template, jsonify, request, send_file
import sqlite3
import pandas as pd
from datetime import datetime

app = Flask(__name__, template_folder='templates')

# Active Faculty Session Variables
active_session = {
    "faculty_name": "Prof. Sharma",
    "lecture_name": "Python Programming",
    "room_no": "Lab-302"
}

# --- DATABASE INIT ---
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            faculty_name TEXT,
            lecture_name TEXT,
            UNIQUE(student_id, date, lecture_name)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

# Form Submit Endpoint (Auto Date & Time)
@app.route('/submit_attendance', methods=['POST'])
def submit_attendance():
    data = request.json
    student_id = data.get('student_id')
    name = data.get('name')
    
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")    # Automatic Date
    time_str = now.strftime("%H:%M:%S")    # Automatic Time

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO attendance (student_id, name, date, time, faculty_name, lecture_name) VALUES (?, ?, ?, ?, ?, ?)",
            (student_id, name, date_str, time_str, active_session["faculty_name"], active_session["lecture_name"])
        )
        conn.commit()
        response = {"status": "success", "message": f"Attendance marked for {name} ({student_id})"}
    except sqlite3.IntegrityError:
        response = {"status": "error", "message": "Attendance already marked for this subject today!"}
    finally:
        conn.close()

    return jsonify(response)

@app.route('/set_faculty', methods=['POST'])
def set_faculty():
    global active_session
    data = request.json
    active_session["faculty_name"] = data.get("faculty_name")
    active_session["lecture_name"] = data.get("lecture_name")
    active_session["room_no"] = data.get("room_no")
    return jsonify({"status": "success", "session": active_session})

@app.route('/get_attendance')
def get_attendance():
    conn = sqlite3.connect("database.db")
    df = pd.read_sql_query("SELECT student_id, name, date, time, faculty_name, lecture_name FROM attendance ORDER BY id DESC", conn)
    conn.close()
    return jsonify(df.to_dict(orient="records"))

# Student Login Statistics API
@app.route('/student_stats')
def student_stats():
    roll = request.args.get('roll')
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Total conducted classes/sessions count
    cursor.execute("SELECT COUNT(DISTINCT date || lecture_name) FROM attendance")
    total_sessions = cursor.fetchone()[0] or 1

    # Student attended sessions
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ?", (roll,))
    attended = cursor.fetchone()[0]
    conn.close()

    percentage = round((attended / total_sessions) * 100, 2) if total_sessions > 0 else 0
    return jsonify({
        "attended": attended,
        "total_sessions": total_sessions,
        "percentage": percentage
    })

@app.route('/download_excel')
def download_excel():
    conn = sqlite3.connect("database.db")
    df = pd.read_sql_query("SELECT student_id as Roll_No, name as Student_Name, date as Date, time as Time, faculty_name as Faculty_Name, lecture_name as Lecture_Name FROM attendance", conn)
    conn.close()
    
    filename = "Attendance_Master_Register.xlsx"
    df.to_excel(filename, index=False)
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
