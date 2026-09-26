import os
import csv
import time
import json
import threading
import subprocess
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session
from gpiozero import MotionSensor

app = Flask(__name__)
app.secret_key = "supersecretkey_ganti_dengan_kunci_acak"

# --- Kredensial Login Dashboard ---
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

# --- Konfigurasi File & GPIO ---
UPLOAD_FOLDER = 'uploads'
CONFIG_FILE = 'config.json'
CSV_FILE = "log_deteksi.csv"
GPIO_PIN = 21

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Inisialisasi Sensor PIR menggunakan gpiozero
pir = MotionSensor(GPIO_PIN)

# --- Fungsi Helper Config JSON ---
def load_config():
    default_config = {
        "start_silent": "03:00",
        "end_silent": "20:00",
        "audio_file": "uploads/voice.mp3",
        "auto_reset_days": 365  # Default 1 tahun (dalam hitungan hari)
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                default_config.update(config)
                return default_config
        except Exception:
            pass
    return default_config

def save_config(data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- Logika Pembersihan Log Otomatis ---
def clean_old_logs():
    config = load_config()
    days = int(config.get("auto_reset_days", 365))
    
    if not os.path.exists(CSV_FILE) or days <= 0:
        return

    cutoff_date = datetime.now() - timedelta(days=days)
    new_rows = []
    header = ["Timestamp", "Event", "Audio_Status"]

    with open(CSV_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        if not rows:
            return
        
        # Ambil header jika ada
        if rows[0] == header:
            data_rows = rows[1:]
        else:
            data_rows = rows

        for row in data_rows:
            if len(row) > 0:
                try:
                    log_date = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                    if log_date >= cutoff_date:
                        new_rows.append(row)
                except ValueError:
                    # Simpan baris jika format tanggal tidak valid
                    new_rows.append(row)

    # Tulis ulang file CSV dengan data yang masih valid
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(new_rows)

# --- Decorator Login ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash("Silakan login terlebih dahulu untuk mengakses dashboard.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Logika Sensor PIR & Audio ---
def is_audio_enabled():
    config = load_config()
    start_silent = config.get("start_silent", "03:00")
    end_silent = config.get("end_silent", "20:00")
    
    current_time = datetime.now().time()
    start_time = datetime.strptime(start_silent, "%H:%M").time()
    end_time = datetime.strptime(end_silent, "%H:%M").time()
    
    if start_time <= end_time:
        return start_time <= current_time <= end_time
    else:
        return current_time >= start_time or current_time <= end_time

def log_to_csv(status_audio):
    # Jalankan pembersihan log lama sebelum menulis log baru
    clean_old_logs()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = ["Timestamp", "Event", "Audio_Status"]
    data_row = [timestamp, "Gerakan Terdeteksi", status_audio]
    
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)
        writer.writerow(data_row)

def pir_listener_loop():
    print("Program Announcer & Logger Standby (gpiozero)...")
    print(f"Menunggu gerakan pada GPIO {GPIO_PIN}...\n")
    time.sleep(2)
    
    while True:
        pir.wait_for_motion()
        
        config = load_config()
        audio_file = config.get("audio_file", "uploads/voice.mp3")
        start_silent = config.get("start_silent", "03:00")
        end_silent = config.get("end_silent", "20:00")
        
        audio_aktif = is_audio_enabled()
        status_log = "Diputar" if audio_aktif else f"Muted ({start_silent}-{end_silent})"
        
        log_to_csv(status_log)
        print(f"[!] Gerakan terdeteksi! [{status_log}]")
        
        if audio_aktif and os.path.exists(audio_file):
            subprocess.run(["mpg123", "-q", audio_file])
            print("[+] File MP3 selesai dijalankan...")
            
        pir.wait_for_no_motion()
        print("[+] Area steril. Sensor siap mendeteksi ulang.\n")
        time.sleep(0.5)

# Jalankan pendeteksi PIR di background thread
threading.Thread(target=pir_listener_loop, daemon=True).start()

# --- Route Flask Dashboard & Auth ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash("Login berhasil!", "success")
            return redirect(url_for('index'))
        else:
            flash("Username atau password salah!", "danger")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("Anda berhasil keluar.", "info")
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    config = load_config()
    
    # Ambil daftar file MP3
    audio_files = []
    if os.path.exists(UPLOAD_FOLDER):
        audio_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith('.mp3')]

    # Baca data log CSV
    logs = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode="r", encoding="utf-8") as f:
            reader = list(csv.reader(f))
            if len(reader) > 1:
                logs = reader[1:][::-1]
                
    return render_template('index.html', 
                           config=config,
                           audio_files=audio_files,
                           logs=logs[:50])

@app.route('/update-settings', methods=['POST'])
@login_required
def update_settings():
    config = load_config()
    config['start_silent'] = request.form.get('start_silent')
    config['end_silent'] = request.form.get('end_silent')
    save_config(config)
    
    flash("Pengaturan jam operasional berhasil diperbarui!", "success")
    return redirect(url_for('index'))

@app.route('/upload-audio', methods=['POST'])
@login_required
def upload_audio():
    if 'file_audio' not in request.files:
        flash("Tidak ada file yang dipilih!", "danger")
        return redirect(url_for('index'))
        
    file = request.files['file_audio']
    if file.filename == '':
        flash("File belum dipilih!", "danger")
        return redirect(url_for('index'))
        
    if file and file.filename.lower().endswith('.mp3'):
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        
        config = load_config()
        config['audio_file'] = filepath
        save_config(config)
        
        flash(f"File audio '{file.filename}' berhasil diunggah dan diaktifkan!", "success")
    else:
        flash("Format file harus .mp3!", "danger")
        
    return redirect(url_for('index'))

@app.route('/set-audio', methods=['POST'])
@login_required
def set_audio():
    selected_audio = request.form.get('selected_audio')
    if selected_audio:
        config = load_config()
        config['audio_file'] = os.path.join(UPLOAD_FOLDER, selected_audio)
        save_config(config)
        flash(f"Audio aktif berhasil diubah ke {selected_audio}", "success")
    else:
        flash("Silakan pilih file audio terlebih dahulu!", "danger")
        
    return redirect(url_for('index'))

@app.route('/update-log-settings', methods=['POST'])
@login_required
def update_log_settings():
    config = load_config()
    config['auto_reset_days'] = int(request.form.get('auto_reset_days', 365))
    save_config(config)
    
    # Langsung jalankan fungsi pembersihan setelah pengaturan diubah
    clean_old_logs()
    flash("Pengaturan reset otomatis log berhasil disimpan!", "success")
    return redirect(url_for('index'))

@app.route('/reset-log-manual', methods=['POST'])
@login_required
def reset_log_manual():
    header = ["Timestamp", "Event", "Audio_Status"]
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        
    flash("Seluruh riwayat log berhasil dihapus secara manual!", "warning")
    return redirect(url_for('index'))

@app.route('/download-log')
@login_required
def download_log():
    if os.path.exists(CSV_FILE):
        return send_file(CSV_FILE, as_attachment=True, download_name='log_deteksi.csv')
    flash("File log belum tersedia.", "warning")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
