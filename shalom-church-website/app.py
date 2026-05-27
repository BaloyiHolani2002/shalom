from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import psycopg2
from datetime import datetime
import os
from urllib.parse import urlparse
import re

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# ===========================================================
# LOCAL DATABASE CONFIG (fallback)
# ===========================================================
LOCAL_DB = {
    'host': 'localhost',
    'database': 'shalom_church_db',
    'user': 'postgres',
    'password': 'Baloyi',
    'port': '5432'
}

# ===========================================================
# DATABASE CONNECTION HANDLER
# ===========================================================
def get_db_connection():
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if DATABASE_URL:
            result = urlparse(DATABASE_URL)
            conn = psycopg2.connect(
                database=result.path[1:],
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port
            )
            print("🌍 Connected to RAILWAY PostgreSQL")
            return conn
        else:
            conn = psycopg2.connect(
                host=LOCAL_DB['host'],
                database=LOCAL_DB['database'],
                user=LOCAL_DB['user'],
                password=LOCAL_DB['password'],
                port=LOCAL_DB['port']
            )
            print("🖥 Connected to LOCAL PostgreSQL")
            return conn
    except Exception as e:
        print(f"❌ DATABASE CONNECTION ERROR: {e}")
        return None

# ===========================================================
# HOME PAGE (events display only)
# ===========================================================
@app.route('/')
def index():
    conn = get_db_connection()
    if not conn:
        return "Database connection failed. Please try again later.", 500

    cursor = conn.cursor()
    cursor.execute("""
        SELECT title, event_date, start_time, end_time, location, image_url
        FROM event_posts
        WHERE is_published = TRUE
        AND event_date >= CURRENT_DATE
        ORDER BY event_date ASC
        LIMIT 6
    """)
    events = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', events=events)

# ===========================================================
# ADMIN AUTHENTICATION (plain text passwords)
# ===========================================================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        if not conn:
            flash('Database connection failed.')
            return render_template('admin_login.html')

        cursor = conn.cursor()
        try:
            cursor.execute("SELECT user_id, password, role FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            # Plain text comparison
            if user and user[1] == password:
                session['admin_logged_in'] = True
                session['user_id'] = user[0]
                session['user_role'] = user[2]
                flash('Login successful! Welcome back.')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid username or password.')
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

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

# ===========================================================
# CREATE ADMIN USER (plain text password)
# ===========================================================
@app.route('/create-admin', methods=['GET', 'POST'])
def create_admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']   # stored as plain text
        role = request.form['role']

        conn = get_db_connection()
        if not conn:
            flash('Database connection failed.')
            return render_template('create_admin.html')

        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (username, password, role)
                VALUES (%s, %s, %s)
            """, (username, password, role))
            conn.commit()
            flash('Admin user created successfully!')
        except Exception as e:
            conn.rollback()
            flash('Error creating admin: ' + str(e))
        finally:
            cursor.close()
            conn.close()

    return render_template('create_admin.html')

# ===========================================================
# MEMBER MANAGEMENT
# ===========================================================
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
        if not conn:
            flash('Database connection failed.')
            return redirect('/add_member')

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

# ===========================================================
# STATIC PAGES
# ===========================================================
@app.route('/aboutus')
def about():
    return render_template('aboutus.html')

@app.route('/leadership')
def leadership():
    return render_template('leadership.html')

@app.route('/sermons')
def sermons():
    return render_template('sermons.html')


@app.route('/testimony')
def testimony():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, testimony, created_at FROM testimonies WHERE approved = TRUE ORDER BY created_at DESC LIMIT 20")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    testimonies = []
    for row in rows:
        created_at = row[3]
        # If it's a string, parse it into a datetime object
        if isinstance(created_at, str):
            try:
                created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                created_at = datetime.now()
        testimonies.append((row[0], row[1], row[2], created_at))

    return render_template('testimony.html', testimonies=testimonies)



@app.route('/submit-testimony', methods=['POST'])
def submit_testimony():
    name = request.form.get('name')
    email = request.form.get('email')
    testimony_text = request.form.get('testimony')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO testimonies (name, email, testimony, approved) VALUES (%s, %s, %s, FALSE)", (name, email, testimony_text))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Thank you for sharing your testimony! It will be reviewed before publishing.')
    return redirect(url_for('testimony'))

# ===========================================================
# ADMIN API: MEMBERS (GET, POST, DELETE)
# ===========================================================
@app.route('/api/members')
def api_get_members():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT member_id, first_name, last_name, email, phone, address,
                   date_of_birth, date_joined, baptism_status, membership_status
            FROM members
            ORDER BY date_joined DESC
        """)
        members = cursor.fetchall()
        members_list = []
        for m in members:
            members_list.append({
                'member_id': m[0],
                'first_name': m[1],
                'last_name': m[2],
                'email': m[3],
                'phone': m[4],
                'address': m[5],
                'date_of_birth': m[6].strftime('%Y-%m-%d') if m[6] else None,
                'date_joined': m[7].strftime('%Y-%m-%d %H:%M:%S') if m[7] else None,
                'baptism_status': m[8],
                'membership_status': m[9]
            })
        return jsonify({'members': members_list})
    except Exception as e:
        return jsonify({'error': str(e), 'members': []}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/members', methods=['POST'])
def api_create_member():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM members")
        count = cursor.fetchone()[0]
        member_id = f"MEM{str(count + 1).zfill(3)}"

        cursor.execute("""
            INSERT INTO members (member_id, first_name, last_name, email, phone, address,
                                 date_of_birth, date_joined, baptism_status, membership_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING member_id
        """, (
            member_id,
            data.get('first_name'),
            data.get('last_name'),
            data.get('email'),
            data.get('phone'),
            data.get('address'),
            data.get('date_of_birth'),
            datetime.now(),
            data.get('baptism_status', 'Not Baptized'),
            data.get('membership_status', 'Visitor')
        ))
        new_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({'message': 'Member created', 'member_id': new_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/members/<member_id>', methods=['DELETE'])
def api_delete_member(member_id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM members WHERE member_id = %s", (member_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'error': 'Member not found'}), 404
        return jsonify({'message': 'Member deleted'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ===========================================================
# ADMIN: TESTIMONY APPROVAL
# ===========================================================
@app.route('/admin/pending-testimonies')
def pending_testimonies():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, testimony, created_at FROM testimonies WHERE approved = FALSE ORDER BY created_at ASC")
    pending = cursor.fetchall()
    cursor.close()
    conn.close()
    pending_list = [{'id': p[0], 'name': p[1], 'email': p[2], 'testimony': p[3], 'created_at': p[4].strftime('%Y-%m-%d %H:%M')} for p in pending]
    return jsonify(pending_list)

@app.route('/admin/approve-testimony/<int:testimony_id>', methods=['POST'])
def approve_testimony(testimony_id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE testimonies SET approved = TRUE WHERE id = %s", (testimony_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Testimony approved'})

# ===========================================================
# HEALTH CHECK
# ===========================================================
@app.route('/api/health')
def api_health():
    conn = get_db_connection()
    if not conn:
        return jsonify({'status': 'unhealthy', 'database': 'disconnected'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify({'status': 'healthy', 'database': 'connected'})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# ===========================================================
# DATABASE INITIALIZATION (add testimonies table)
# ===========================================================
@app.route('/init-db')
def init_db():
    conn = get_db_connection()
    if not conn:
        return "Database connection failed", 500
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS members (
                member_id VARCHAR(50) PRIMARY KEY,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE,
                phone VARCHAR(50),
                address TEXT,
                date_of_birth DATE,
                date_joined TIMESTAMP NOT NULL,
                baptism_status VARCHAR(20) DEFAULT 'Not Baptized',
                membership_status VARCHAR(20) DEFAULT 'Visitor',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_posts (
                event_id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                event_date DATE NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME,
                location VARCHAR(255),
                image_url VARCHAR(500),
                is_published BOOLEAN DEFAULT FALSE,
                created_by INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS testimonies (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255),
                testimony TEXT NOT NULL,
                approved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        return "Database tables created successfully"
    except Exception as e:
        conn.rollback()
        return f"Error creating tables: {e}"
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )