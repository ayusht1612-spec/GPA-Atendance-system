import os
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, render_template, jsonify, request, send_file
import pandas as pd
from datetime import datetime

# Explicitly set absolute template directory path for Render cloud environment
base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)

# Initialize Firebase Firestore SDK
try:
    cred_path = os.path.join(base_dir, 'serviceAccountKey.json')
    if not firebase_admin._apps:
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Firebase Initialized Successfully!")
        else:
            print("Warning: serviceAccountKey.json file not found.")
    db = firestore.client()
except Exception as e:
    print(f"Firebase Initialization Error: {e}")
    db = None

# Active Faculty Session Variables
active_session = {
    "faculty_name": "Prof. Sharma",
    "lecture_name": "Python Programming",
    "room_no": "Lab-302"
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/session', methods=['GET', 'POST'])
def handle_session():
    global active_session
    if request.method == 'POST':
        data = request.json
        active_session['faculty_name'] = data.get('faculty_name', active_session['faculty_name'])
        active_session['lecture_name'] = data.get('lecture_name', active_session['lecture_name'])
        active_session['room_no'] = data.get('room_no', active_session['room_no'])
        return jsonify({"status": "success", "session": active_session})
    return jsonify(active_session)

@app.route('/api/mark_attendance', methods=['POST'])
def mark_attendance():
    if not db:
        return jsonify({"status": "error", "message": "Database not initialized"}), 500
        
    data = request.json
    student_id = data.get('student_id')
    name = data.get('name')
    
    if not student_id or not name:
        return jsonify({"status": "error", "message": "Student ID and Name required"}), 400

    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M:%S')

    record = {
        'student_id': str(student_id).strip(),
        'name': name.strip(),
        'date': date_str,
        'time': time_str,
        'faculty_name': active_session['faculty_name'],
        'lecture_name': active_session['lecture_name'],
        'timestamp': firestore.SERVER_TIMESTAMP
    }

    try:
        # Check duplicate entry for the same student on the same date and lecture
        docs = db.collection('attendance')\
            .where('student_id', '==', record['student_id'])\
            .where('date', '==', date_str)\
            .where('lecture_name', '==', record['lecture_name'])\
            .get()

        if len(docs) > 0:
            return jsonify({"status": "warning", "message": f"Attendance already marked for {name} today!"}), 200

        db.collection('attendance').add(record)
        return jsonify({"status": "success", "message": f"Attendance marked for {name}!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/get_attendance', methods=['GET'])
def get_attendance():
    if not db:
        return jsonify([])
    try:
        docs = db.collection('attendance').order_by('date', direction=firestore.Query.DESCENDING).get()
        data = []
        for doc in docs:
            d = doc.to_dict()
            d['id'] = doc.id
            if 'timestamp' in d:
                del d['timestamp']
            data.append(d)
        return jsonify(data)
    except Exception as e:
        return jsonify([])

@app.route('/api/student_stats/<student_id>', methods=['GET'])
def student_stats(student_id):
    if not db:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        docs = db.collection('attendance').where('student_id', '==', str(student_id).strip()).get()
        records = [doc.to_dict() for doc in docs]
        
        total_lectures = 30 # Standard benchmark total
        attended = len(records)
        percentage = round((attended / total_lectures) * 100, 2) if total_lectures > 0 else 0
        
        return jsonify({
            "student_id": student_id,
            "name": records[0]['name'] if records else "Student",
            "attended": attended,
            "total": total_lectures,
            "percentage": percentage,
            "history": records
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/export_excel', methods=['GET'])
def export_excel():
    if not db:
        return "Database Error", 500
    try:
        docs = db.collection('attendance').get()
        data = [doc.to_dict() for doc in docs]
        for d in data:
            d.pop('timestamp', None)
            
        df = pd.DataFrame(data)
        file_path = os.path.join(base_dir, 'Attendance_Register.xlsx')
        df.to_excel(file_path, index=False)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
