from flask import Flask, render_template, request, redirect, url_for
import boto3
import pymysql
import os

app = Flask(__name__)

# --- KONFIGURASI RDS (GANTI SESUAI AWS LO) ---
DB_HOST = "database-1.cf44s2yomgkl.ap-southeast-1.rds.amazonaws.com"
DB_USER = "admin"
DB_PASS = "lailaadmin1234"
DB_NAME = "laila_db"

# --- KONFIGURASI S3 (GANTI SESUAI AWS LO) ---
S3_BUCKET = "laila-s3-bucket-demo"
# Pastiin Region-nya bener (misal us-east-1)
s3_client = boto3.client('s3', region_name='ap-southeast-1') 

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, db=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/')
def index():
    # Ambil data dari RDS (Guestbook)
    messages = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Buat tabel kalo belum ada
            cursor.execute("CREATE TABLE IF NOT EXISTS guestbook (id INT AUTO_INCREMENT PRIMARY KEY, message VARCHAR(255) NOT NULL)")
            cursor.execute("SELECT message FROM guestbook ORDER BY id DESC")
            messages = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"Error RDS: {e}")

    # List file dari S3 (Storage)
    files = []
    try:
        # Cek bucket ada/bisa diakses
        s3_client.head_bucket(Bucket=S3_BUCKET)
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET)
        if 'Contents' in response:
            files = [obj['Key'] for obj in response['Contents']]
    except Exception as e:
        print(f"Error S3: {e}")
        # Jika error, kasih info di list biar user tau
        files = [f"Error Akses S3: {str(e)}"]

    return render_template('index.html', messages=messages, files=files)

@app.route('/add', methods=['POST'])
def add_message():
    msg = request.form.get('message')
    if msg:
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO guestbook (message) VALUES (%s)", (msg,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error Insert RDS: {e}")
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if file:
        try:
            # Upload pake nama file asli
            s3_client.upload_fileobj(file, S3_BUCKET, file.filename)
        except Exception as e:
            print(f"Error Upload S3: {e}")
    return redirect(url_for('index'))

# Route buat Health Check Load Balancer
@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    # Jalan di port 80 biar bisa diakses langsung
    app.run(host='0.0.0.0', port=80, debug=True, threaded=True)
