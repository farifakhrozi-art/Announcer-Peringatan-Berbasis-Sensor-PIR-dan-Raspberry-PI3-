# 📢 Announcer Peringatan Aksesibilitas Berbasis Sensor PIR & Raspberry Pi 3

![Raspberry Pi](https://img.shields.io/badge/Hardware-Raspberry%20Pi%203-red)
![Python](https://img.shields.io/badge/Backend-Python-blue)
![HTML5](https://img.shields.io/badge/Frontend-HTML5%2FJS-orange)
![License](https://img.shields.io/badge/License-MIT-green)

Sistem pengumuman suara otomatis (*smart announcer*) berbasis IoT yang dirancang untuk mendeteksi penumpang dan memutar instruksi audio navigasi aksesibilitas di area pintu masuk ruang tunggu Bandara Halim Perdanakusuma.

---

## 📌 Latar Belakang

Di area pintu masuk ruang tunggu Citilink Bandara Halim Perdanakusuma, terdapat tangga yang berpotensi membahayakan bagi penumpang penyandang disabilitas dan lansia. Meskipun telah disediakan pintu khusus aksesibilitas, banyak penumpang yang belum menyadarinya.

Proyek ini dibuat untuk memberikan peringatan dini (*early warning announcement*) secara otomatis saat ada penumpang mendekati area tersebut, sehingga mereka terarah menuju akses jalan yang aman.

---

## ✨ Fitur Utama

- **Deteksi Gerakan Real-time**: Menggunakan sensor PIR yang terhubung ke Raspberry Pi 3 untuk mendeteksi kehadiran penumpang secara responsif.
- **Pengumuman Suara Otomatis**: Memutar file audio peringatan (*announcer*) secara otomatis begitu sensor terpicu.
- **Dashboard Manajemen Web & Desktop**:
  - **Penjadwalan Waktu Aktif**: Mengatur jam operasional sistem secara fleksibel.
  - **Manajemen Audio**: Fitur *upload* dan ganti file suara peringatan secara kustom.
  - **Log & Riwayat Deteksi**: Menyimpan catatan riwayat waktu deteksi penumpang.
- **Akses Antarmuka Fleksibel**:
  - Tampilan GUI Desktop lokal untuk dihubungkan langsung ke layar/monitor Raspberry Pi.
  - Akses kontrol jarak jauh melalui **VNC** atau browser web dalam jaringan yang sama.

---

## 🛠️ Spesifikasi Teknologi & Hardware

### Hardware
1. **Raspberry Pi 3 Model B/B+**
2. **Sensor PIR (Passive Infrared)**
3. **Module Audio / Speaker Active**
4. **Catu Daya / Power Supply 5V**

### Software & Stack
- **Backend**: Python (Flask / FastApi / Socket / Pygame / RPi.GPIO)
- **Frontend**: HTML5, CSS3, JavaScript
- **OS / Remote**: Raspberry Pi OS, VNC Server

---

## 🏗️ Arsitektur Sistem

```text
 [ Sensor PIR ] ---> [ Raspberry Pi 3 (Python Backend) ] ---> [ Speaker / Audio Output ]
                                |
                        (HTTP / WebSockets)
                                |
                 [ Dashboard Web / GUI Desktop (HTML) ]
```

---

## 🚀 Panduan Instalasi & Penggunaan

### 1. Cloning Repository
```bash
git clone https://github.com/username/announcer-raspi-halim.git
cd announcer-raspi-halim
```

### 2. Instalasi Dependency Python
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi GPIO
Pastikan pin GPIO untuk sensor PIR sudah disesuaikan pada file konfigurasi (misal: `config.py` atau `main.py`).

### 4. Menjalankan Aplikasi
- **Menjalankan Service Backend & Server Web:**
  ```bash
  python app.py
  ```
- Buka browser dan akses dashboard melalui alamat `http://localhost:5000` atau IP Raspberry Pi (`http://<IP_RASPI>:5000`).

---

## 🖥️ Tampilan Antarmuka (UI)

| Dashboard Web/Desktop | Pengaturan Audio & Waktu |
| --------------------- | ------------------------ |
| *(Tambahkan screenshot tampilan utama)* | *(Tambahkan screenshot form upload/jam)* |

---

## 📄 Lisensi

Proyek ini dilindungi di bawah lisensi **MIT**. Silakan gunakan dan kembangkan secara bebas.
