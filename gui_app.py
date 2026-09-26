import os
import csv
import time
import json
import subprocess
from datetime import datetime, timedelta

# Menggunakan PyQt5 menggantikan PyQt6
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTimeEdit, QPushButton, QComboBox, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QFormLayout
)
from PyQt5.QtCore import QTime, QThread, pyqtSignal
from gpiozero import MotionSensor

# --- Konfigurasi File & GPIO ---
UPLOAD_FOLDER = 'uploads'
CONFIG_FILE = 'config.json'
CSV_FILE = "log_deteksi.csv"
GPIO_PIN = 23

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Helper Config JSON ---
def load_config():
    default_config = {
        "start_silent": "03:00",
        "end_silent": "20:00",
        "audio_file": "uploads/voice.mp3",
        "auto_reset_days": 365
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
        
        data_rows = rows[1:] if rows[0] == header else rows
        for row in data_rows:
            if len(row) > 0:
                try:
                    log_date = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                    if log_date >= cutoff_date:
                        new_rows.append(row)
                except ValueError:
                    new_rows.append(row)

    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(new_rows)

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

# --- Worker Thread untuk PIR Sensor ---
class PIRWorker(QThread):
    motion_detected_signal = pyqtSignal()

    def run(self):
        pir = MotionSensor(GPIO_PIN, queue_len=5, sample_rate=100)
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
            self.motion_detected_signal.emit()
            
            if audio_aktif and os.path.exists(audio_file):
                subprocess.run(["mpg123", "-q", audio_file])
                
            pir.wait_for_no_motion()
            time.sleep(0.5)

# --- Window Utama GUI ---
class AnnouncerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kontrol Announcer & Sensor PIR")
        self.resize(800, 650)
        
        self.init_ui()
        self.load_settings()
        self.refresh_audio_list()
        self.load_logs()
        
        # Jalankan Thread PIR Sensor
        self.pir_thread = PIRWorker()
        self.pir_thread.motion_detected_signal.connect(self.load_logs)
        self.pir_thread.start()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Top Section: Settings Grid ---
        settings_layout = QHBoxLayout()

        # 1. GroupBox Mute Time
        mute_box = QGroupBox("Pengaturan Waktu Mute")
        mute_form = QFormLayout()
        
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setDisplayFormat("HH:mm")
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setDisplayFormat("HH:mm")
        
        btn_save_time = QPushButton("Simpan Jam Mute")
        btn_save_time.clicked.connect(self.save_time_settings)

        mute_form.addRow("Mulai Silent (Mute):", self.start_time_edit)
        mute_form.addRow("Berakhir Silent:", self.end_time_edit)
        mute_form.addRow(btn_save_time)
        mute_box.setLayout(mute_form)

        # 2. GroupBox Audio Settings
        audio_box = QGroupBox("Pengaturan File Audio")
        audio_form = QFormLayout()

        self.lbl_active_audio = QLabel("Audio Aktif: -")
        self.combo_audio = QComboBox()
        
        btn_set_audio = QPushButton("Jadikan Suara Aktif")
        btn_set_audio.clicked.connect(self.set_active_audio)

        btn_import_audio = QPushButton("Upload MP3 Baru...")
        btn_import_audio.clicked.connect(self.import_new_audio)

        audio_form.addRow(self.lbl_active_audio)
        audio_form.addRow("Pilih File Tersimpan:", self.combo_audio)
        audio_form.addRow(btn_set_audio)
        audio_form.addRow(btn_import_audio)
        audio_box.setLayout(audio_form)

        settings_layout.addWidget(mute_box)
        settings_layout.addWidget(audio_box)
        main_layout.addLayout(settings_layout)

        # 3. GroupBox Retensi Log
        retention_box = QGroupBox("Pengaturan Retensi Log Otomatis")
        retention_layout = QHBoxLayout()

        self.combo_retention = QComboBox()
        retention_options = [
            ("1 Hari", 1), ("3 Hari", 3), ("7 Hari (1 Minggu)", 7),
            ("2 Minggu", 14), ("1 Bulan", 30), ("3 Bulan", 90),
            ("6 Bulan", 180), ("12 Bulan (1 Tahun)", 365),
            ("2 Tahun", 730), ("3 Tahun", 1095)
        ]
        for label, value in retention_options:
            self.combo_retention.addItem(label, value)

        btn_save_retention = QPushButton("Simpan Retensi")
        btn_save_retention.clicked.connect(self.save_retention_setting)

        retention_layout.addWidget(QLabel("Simpan Data Log Selama:"))
        retention_layout.addWidget(self.combo_retention)
        retention_layout.addWidget(btn_save_retention)
        retention_box.setLayout(retention_layout)
        main_layout.addWidget(retention_box)

        # --- Bottom Section: Log Table ---
        log_box = QGroupBox("Riwayat Deteksi Gerakan")
        log_layout = QVBoxLayout()

        # Log Actions (Reset & Refresh)
        log_btn_layout = QHBoxLayout()
        btn_reset_log = QPushButton("Reset Log Manual")
        btn_reset_log.setStyleSheet("background-color: #d9534f; color: white;")
        btn_reset_log.clicked.connect(self.reset_log_manual)

        btn_refresh_log = QPushButton("Refresh Log")
        btn_refresh_log.clicked.connect(self.load_logs)

        log_btn_layout.addWidget(btn_reset_log)
        log_btn_layout.addStretch()
        log_btn_layout.addWidget(btn_refresh_log)

        # Table Widget (Penyesuaian PyQt5 QHeaderView)
        self.table_logs = QTableWidget()
        self.table_logs.setColumnCount(3)
        self.table_logs.setHorizontalHeaderLabels(["Timestamp", "Event", "Status Audio"])
        self.table_logs.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        log_layout.addLayout(log_btn_layout)
        log_layout.addWidget(self.table_logs)
        log_box.setLayout(log_layout)
        main_layout.addWidget(log_box)

    def load_settings(self):
        config = load_config()
        self.start_time_edit.setTime(QTime.fromString(config.get("start_silent", "03:00"), "HH:mm"))
        self.end_time_edit.setTime(QTime.fromString(config.get("end_silent", "20:00"), "HH:mm"))
        self.lbl_active_audio.setText(f"Audio Aktif: {config.get('audio_file', '-')}")

        days = config.get("auto_reset_days", 365)
        index = self.combo_retention.findData(days)
        if index != -1:
            self.combo_retention.setCurrentIndex(index)

    def refresh_audio_list(self):
        self.combo_audio.clear()
        if os.path.exists(UPLOAD_FOLDER):
            files = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith('.mp3')]
            self.combo_audio.addItems(files)

    def save_time_settings(self):
        config = load_config()
        config['start_silent'] = self.start_time_edit.time().toString("HH:mm")
        config['end_silent'] = self.end_time_edit.time().toString("HH:mm")
        save_config(config)
        QMessageBox.information(self, "Berhasil", "Pengaturan jam Mute berhasil disimpan!")

    def set_active_audio(self):
        selected = self.combo_audio.currentText()
        if selected:
            path = os.path.join(UPLOAD_FOLDER, selected)
            config = load_config()
            config['audio_file'] = path
            save_config(config)
            self.lbl_active_audio.setText(f"Audio Aktif: {path}")
            QMessageBox.information(self, "Berhasil", f"Audio diubah ke: {selected}")

    def import_new_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih File MP3", "", "Audio Files (*.mp3)")
        if file_path:
            filename = os.path.basename(file_path)
            dest_path = os.path.join(UPLOAD_FOLDER, filename)
            
            with open(file_path, 'rb') as fsrc, open(dest_path, 'wb') as fdst:
                fdst.write(fsrc.read())

            config = load_config()
            config['audio_file'] = dest_path
            save_config(config)

            self.refresh_audio_list()
            self.lbl_active_audio.setText(f"Audio Aktif: {dest_path}")
            QMessageBox.information(self, "Berhasil", f"File {filename} berhasil diunggah & diaktifkan!")

    def save_retention_setting(self):
        config = load_config()
        config['auto_reset_days'] = self.combo_retention.currentData()
        save_config(config)
        clean_old_logs()
        self.load_logs()
        QMessageBox.information(self, "Berhasil", "Pengaturan retensi log disimpan!")

    def reset_log_manual(self):
        reply = QMessageBox.question(self, "Konfirmasi", "Yakin ingin menghapus SELURUH log?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            header = ["Timestamp", "Event", "Audio_Status"]
            with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(header)
            self.load_logs()

    def load_logs(self):
        self.table_logs.setRowCount(0)
        if os.path.exists(CSV_FILE):
            with open(CSV_FILE, mode="r", encoding="utf-8") as f:
                reader = list(csv.reader(f))
                if len(reader) > 1:
                    logs = reader[1:][::-1]
                    for row_idx, row_data in enumerate(logs[:50]):
                        self.table_logs.insertRow(row_idx)
                        for col_idx, text in enumerate(row_data):
                            self.table_logs.setItem(row_idx, col_idx, QTableWidgetItem(text))

if __name__ == '__main__':
    app = QApplication([])
    window = AnnouncerApp()
    window.show()
    app.exec_()