from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from datetime import datetime
import bcrypt
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# Database connection - PostgreSQL
def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        port=5432, 
        user="postgres",
        password="Maxelov@2023",
        database="shalom_church_db"
    )
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    return render_template('admin_dashboard.html')

# ✅ Fixed: Only one admin_login route
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT user_id, password_hash, role FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

            if user:
                stored_hash = user[1].encode('utf-8')
                if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                    session['admin_logged_in'] = True
                    session['user_id'] = user[0]
                    session['user_role'] = user[2]
                    flash('Login successful! Welcome back.')
                    return redirect(url_for('admin_dashboard'))  # ✅ Redirects to admin_dashboard.html
                else:
                    flash('Incorrect password. Please try again.')
            else:
                flash('Username not found.')

        except Exception as e:
            flash(f'Login error: {e}')
        finally:
            cursor.close()
            conn.close()

    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/')

@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        date_of_birth = request.form['date_of_birth']
        baptism_status = request.form['baptism_status']
        membership_status = request.form['membership_status']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO members (first_name, last_name, email, phone, address, date_of_birth, date_joined, baptism_status, membership_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                first_name, last_name, email, phone, address, date_of_birth,
                datetime.now(), baptism_status, membership_status
            ))
            conn.commit()
            flash('Member added successfully!')
        except Exception as e:
            conn.rollback()
            flash('Error adding member: ' + str(e))
        finally:
            cursor.close()
            conn.close()

        return redirect('/add_member')

    return render_template('add_member.html')

@app.route('/api/events')
def api_events():
    if not session.get('admin_logged_in'):
        return {'error': 'Unauthorized'}, 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT event_id, title, description, event_date, start_time, end_time, 
                   location, is_published, created_at
            FROM events
            ORDER BY event_date DESC
        """)
        events = cursor.fetchall()
        
        events_list = []
        for event in events:
            events_list.append({
                'id': event[0],
                'title': event[1],
                'description': event[2],
                'event_date': event[3].strftime('%Y-%m-%d'),
                'start_time': str(event[4]) if event[4] else None,
                'end_time': str(event[5]) if event[5] else None,
                'location': event[6],
                'is_published': event[7],
                'created_at': event[8].strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return {'events': events_list}
    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/events', methods=['POST'])
def api_create_event():
    if not session.get('admin_logged_in'):
        return {'error': 'Unauthorized'}, 401
    
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO events (title, description, event_date, start_time, end_time, location, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            data['title'],
            data['description'],
            data['event_date'],
            data['start_time'],
            data.get('end_time'),
            data['location'],
            session['user_id']
        ))
        conn.commit()
        return {'message': 'Event created successfully'}
    except Exception as e:
        conn.rollback()
        return {'error': str(e)}, 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/members', methods=['POST'])
def api_create_member():
    if not session.get('admin_logged_in'):
        return {'error': 'Unauthorized'}, 401
    
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO members (first_name, last_name, email, phone, address, date_of_birth, date_joined, baptism_status, membership_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data['first_name'],
            data['last_name'],
            data['email'],
            data.get('phone'),
            data.get('address'),
            data.get('date_of_birth'),
            datetime.now(),
            data.get('baptism_status', 'Not Baptized'),
            data.get('membership_status', 'Visitor')
        ))
        conn.commit()
        return {'message': 'Member created successfully'}
    except Exception as e:
        conn.rollback()
        return {'error': str(e)}, 500
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    app.run(debug=True)
