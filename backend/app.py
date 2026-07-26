from flask import Flask, jsonify, request
from db_config import get_db_connection
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app)

pattern = r'^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{6,}$'  # Password Validation

# Login Route
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    username = data.get('username').strip().lower()
    password = data.get('password').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch user by username only
    cursor.execute("SELECT * FROM users WHERE LOWER(username)=%s", (username,))
    user = cursor.fetchone()

    conn.close()

    # Compare password
    if user and user['password'].strip() == password:
        return jsonify({
            "status": "success",
            "role": user['role'],
            "student_id": user['student_id']
        })
    else:
        return jsonify({
            "status": "fail",
            "message": "Invalid credentials"
        })


# Subject Route
@app.route('/subjects/<branch>/<int:semester>', methods=['GET'])
def get_subjects(branch, semester):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM subjects WHERE branch=%s AND semester=%s",
        (branch, semester)
    )
    data = cursor.fetchall()

    conn.close()
    return jsonify(data)


# Student Registeration Route
@app.route('/add-full-student', methods=['POST'])
def add_full_student():
    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Clean name
    name_clean = data['name'].strip()

    # Insert student
    cursor.execute(
        "INSERT INTO students (name, branch, semester) VALUES (%s,%s,%s)",
        (name_clean, data['branch'], data['semester'])
    )

    student_id = cursor.lastrowid

    # Create username + strong password
    username = name_clean.lower()
    password = name_clean.capitalize() + "@123"

    cursor.execute("INSERT INTO users (username, password, role, student_id) VALUES (%s,%s,'student',%s)",(username, password, student_id))

    # Insert marks + attendance
    for item in data['subjects']:
        cursor.execute("INSERT INTO marks VALUES (%s,%s,%s)",(student_id, item['subject_id'], item['marks']))

        cursor.execute("INSERT INTO attendance VALUES (%s,%s,%s)",(student_id, item['subject_id'], item['attendance']))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": f"Student added! Username: {username}, Password: {password}"
    })


# Student Data Route
@app.route('/student-data/<int:student_id>', methods=['GET'])
def student_data(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT s.name, s.branch, s.semester,
               sub.subject_name,
               m.marks,
               a.attendance_percentage
        FROM students s
        JOIN marks m ON s.student_id = m.student_id
        JOIN subjects sub ON sub.subject_id = m.subject_id
        JOIN attendance a 
            ON a.student_id = s.student_id AND a.subject_id = sub.subject_id
        WHERE s.student_id = %s
    """, (student_id,))

    data = cursor.fetchall()
    conn.close()

    return jsonify(data)

# Change Password Route
@app.route('/change-password', methods=['POST'])
def change_password():
    data = request.get_json()

    username = data.get('username').strip().lower()
    new_password = data.get('password').strip()

    if not re.match(pattern, new_password):
        return jsonify({
            "status": "fail",
            "message": "Password must include uppercase, number & special char"
        })

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET password=%s WHERE LOWER(username)=%s",
        (new_password, username)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Password updated successfully"
    })

# Forgot Password Route
@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()

    username = data.get('username').strip().lower()
    new_password = data.get('password').strip()

    if not re.match(pattern, new_password):
        return jsonify({
            "status": "fail",
            "message": "Weak password"
        })

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE LOWER(username)=%s",(username,))

    if not cursor.fetchone():
        return jsonify({
            "status": "fail",
            "message": "User not found"
        })

    cursor.execute("UPDATE users SET password=%s WHERE LOWER(username)=%s",(new_password, username))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Password reset successful"
    })

@app.route('/analytics/<int:student_id>', methods=['GET'])
def analytics(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            AVG(m.marks) AS avg_marks,
            AVG(a.attendance_percentage) AS avg_attendance
        FROM marks m
        JOIN attendance a 
            ON m.student_id = a.student_id 
            AND m.subject_id = a.subject_id
        WHERE m.student_id = %s
    """, (student_id,))

    data = cursor.fetchone()
    conn.close()

    # Weak student logic
    status = "Good"
    if data['avg_marks'] < 40 or data['avg_attendance'] < 60:
        status = "Weak"

    return jsonify({
        "average_marks": round(data['avg_marks'], 2),
        "average_attendance": round(data['avg_attendance'], 2),
        "status": status
    })

if __name__ == '__main__':
    app.run(debug=True)