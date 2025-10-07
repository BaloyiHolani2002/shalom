from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from datetime import datetime

app = Flask(__name__)

# Database connection
def get_db_connection():
    conn = mysql.connector.connect(
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

@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    if request.method == 'POST':
        # Collect form data
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
        cursor.execute("""
            INSERT INTO members (first_name, last_name, email, phone, address, date_of_birth, date_joined, baptism_status, membership_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            first_name, last_name, email, phone, address, date_of_birth,
            datetime.now(), baptism_status, membership_status
        ))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('index'))

    return render_template('add_member.html')

if __name__ == "__main__":
    app.run(debug=True)
