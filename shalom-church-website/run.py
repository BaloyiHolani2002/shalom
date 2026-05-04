from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import psycopg2
from datetime import datetime
import bcrypt
import os
from urllib.parse import urlparse  # Added missing import

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
# DATABASE CONNECTION HANDLER (LOCAL OR RAILWAY)
# ===========================================================
def get_db_connection():
    """
    Connect to Railway PostgreSQL if DATABASE_URL exists,
    otherwise connect to the local PostgreSQL database.
    """
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")

        if DATABASE_URL:
            # RAILWAY DATABASE CONNECTION
            result = urlparse(DATABASE_URL)

            conn = psycopg2.connect(
                database=result.path[1:],  # remove "/" at the start
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port
            )

            print("🌍 Connected to RAILWAY PostgreSQL")
            return conn

        else:
            # LOCAL DATABASE CONNECTION
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

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT title, event_date, start_time, end_time, location
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


@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')



@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = None
        cursor = None
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if user exists with direct password comparison
            cursor.execute("SELECT user_id, password, role FROM users WHERE username = %s AND password = %s", 
                          (username, password))
            user = cursor.fetchone()

            if user:
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
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/')

# Route to create admin user with hashed password
@app.route('/create-admin', methods=['GET', 'POST'])
def create_admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']   # PLAIN TEXT
        role = request.form['role']
        
        conn = get_db_connection()
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

# ===========================================================
# API ENDPOINTS
# ===========================================================

@app.route('/api/events')
def api_events():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if table exists and get its name
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND (table_name = 'events' OR table_name = 'event_posts')
        """)
        tables = cursor.fetchall()
        
        if not tables:
            return jsonify({'events': []})
        
        table_name = tables[0][0]  # Get first matching table name
        
        cursor.execute(f"""
            SELECT event_id, title, description, event_date, start_time, end_time, 
                   location, is_published, created_at
            FROM {table_name}
            ORDER BY event_date DESC
        """)
        events = cursor.fetchall()
        
        events_list = []
        for event in events:
            events_list.append({
                'event_id': event[0],
                'title': event[1],
                'description': event[2],
                'event_date': event[3].strftime('%Y-%m-%d') if event[3] else None,
                'start_time': str(event[4]) if event[4] else None,
                'end_time': str(event[5]) if event[5] else None,
                'location': event[6],
                'is_published': event[7],
                'created_at': event[8].strftime('%Y-%m-%d %H:%M:%S') if event[8] else None
            })
        
        return jsonify({'events': events_list})
    except Exception as e:
        print(f"Error fetching events: {e}")
        return jsonify({'error': str(e), 'events': []}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/events', methods=['POST'])
def api_create_event():
    # Check admin login
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    conn = None
    cursor = None

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Required fields
        required_fields = ['title', 'description', 'event_date', 'start_time', 'location']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Validate time format HH:MM
        import re
        time_pattern = re.compile(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')

        if not time_pattern.match(data['start_time']):
            return jsonify({'error': 'Invalid start time format. Use HH:MM'}), 400

        end_time = None
        if data.get('end_time'):
            if not time_pattern.match(data['end_time']):
                return jsonify({'error': 'Invalid end time format. Use HH:MM'}), 400
            end_time = data['end_time']

        conn = get_db_connection()
        cursor = conn.cursor()

        # Ensure event_posts table exists
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'event_posts'
        """)

        if not cursor.fetchone():
            return jsonify({'error': 'event_posts table not found'}), 404

        # Insert event (AUTO PUBLISHED + DEFAULT IMAGE)
        cursor.execute("""
            INSERT INTO event_posts (
                title,
                description,
                event_date,
                start_time,
                end_time,
                location,
                image_url,
                is_published,
                created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s)
            RETURNING event_id
        """, (
            data['title'],
            data['description'],
            data['event_date'],
            data['start_time'],
            end_time,
            data['location'],
            '/static/uploads/events/new.jpg',
            session.get('user_id')
        ))

        event_id = cursor.fetchone()[0]
        conn.commit()

        return jsonify({
            'message': 'Event created successfully',
            'event_id': event_id,
            'is_published': True,
            'image_url': '/static/uploads/events/new.jpg'
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error creating event: {e}")
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/api/events/<int:event_id>', methods=['DELETE'])
def api_delete_event(event_id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check which table exists
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND (table_name = 'events' OR table_name = 'event_posts')
        """)
        tables = cursor.fetchall()
        
        if not tables:
            return jsonify({'error': 'Events table not found'}), 404
        
        table_name = tables[0][0]
        
        cursor.execute(f"DELETE FROM {table_name} WHERE event_id = %s", (event_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Event not found'}), 404
            
        return jsonify({'message': 'Event deleted successfully'})
        
    except Exception as e:
        print(f"Error deleting event: {e}")
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/members')
def api_get_members():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
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
        for member in members:
            members_list.append({
                'member_id': member[0],
                'first_name': member[1],
                'last_name': member[2],
                'email': member[3],
                'phone': member[4],
                'address': member[5],
                'date_of_birth': member[6].strftime('%Y-%m-%d') if member[6] else None,
                'date_joined': member[7].strftime('%Y-%m-%d %H:%M:%S') if member[7] else None,
                'baptism_status': member[8],
                'membership_status': member[9]
            })
        
        return jsonify({'members': members_list})
        
    except Exception as e:
        print(f"Error fetching members: {e}")
        return jsonify({'error': str(e), 'members': []}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/members', methods=['POST'])
def api_create_member():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generate member_id if not provided (for string IDs)
        member_id = data.get('member_id')
        if not member_id:
            # Generate an ID like MEM001, MEM002, etc.
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
        
        new_member_id = cursor.fetchone()[0]
        conn.commit()
        
        return jsonify({'message': 'Member created successfully', 'member_id': new_member_id})
        
    except Exception as e:
        print(f"Error creating member: {e}")
        if conn:
            conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/members/<member_id>', methods=['DELETE'])
def api_delete_member(member_id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM members WHERE member_id = %s", (member_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Member not found'}), 404
            
        return jsonify({'message': 'Member deleted successfully'})
        
    except Exception as e:
        print(f"Error deleting member: {e}")
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ===========================================================
# HEALTH CHECK ENDPOINT
# ===========================================================

@app.route('/api/health')
def api_health():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify({'status': 'healthy', 'database': 'connected'})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# ===========================================================
# DATABASE INITIALIZATION (Optional - for first-time setup)
# ===========================================================

@app.route('/init-db')
def init_db():
    """Create tables if they don't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Create members table
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
        
        # Create users table
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
        
        # Create events table (using event_posts as per your schema)
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
        
        conn.commit()
        return "Database tables created successfully"
        
    except Exception as e:
        conn.rollback()
        return f"Error creating tables: {e}"
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    app.run(debug=True)