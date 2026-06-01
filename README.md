# Sistem Temu Kembali Informasi (STKI) Berbasis RAG
**Pedoman Akademik Kampus**

Sistem ini mengimplementasikan konsep *Retrieval-Augmented Generation* (RAG) untuk pencarian dan penjawaban dokumen pedoman akademik. Repositori ini terdiri dari tiga komponen utama: backend (layanan API dan pemrosesan AI), antarmuka web, dan aplikasi seluler.

## Arsitektur Sistem

```text
STKI-Project/
├── backend/    → FastAPI Server (Python)
├── website/    → React Web Application (Vite)
└── mobile/     → Flutter Mobile Application
```

## Teknologi yang Digunakan

### Layanan Backend
| Komponen | Teknologi |
|----------|-----------|
| Framework API | Python FastAPI |
| Vector Database | PostgreSQL dengan ekstensi `pgvector` |
| Orchestrator RAG | LangChain |
| Model Embedding | `sentence-transformers/all-MiniLM-L6-v2` (Lokal) |
| Large Language Model | Gemini / OpenAI (via LangChain) |

### Aplikasi Mobile (Flutter)
| Komponen | Teknologi |
|----------|-----------|
| Framework | Flutter |
| State Management | Riverpod |
| HTTP Client | Dio |
| Arsitektur | Feature-First (Terbatas pada antarmuka Chat) |

## Konfigurasi dan Instalasi

### 1. Persiapan Database
Pastikan layanan PostgreSQL berjalan dan ekstensi `pgvector` telah diaktifkan.
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
*(Catatan: Skema tabel akan dibuat secara otomatis oleh SQLAlchemy saat backend dijalankan).*

### 2. Instalasi Backend (Python)
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
```

Konfigurasi kredensial lingkungan:
Salin berkas konfigurasi contoh dan sesuaikan parameter koneksi database serta API Key model bahasa.
```bash
cp .env.example .env
```

Jalankan server API:
```bash
python main.py
# Server berjalan di http://localhost:3001
```

### 3. Instalasi Mobile (Flutter)
Aplikasi seluler saat ini dirancang secara eksklusif untuk antarmuka pengguna akhir (chatbot).
```bash
cd mobile
flutter pub get
flutter run
```

Konfigurasi URL API terdapat pada `lib/core/constants/api_constants.dart`. Sesuaikan IP lokal (misalnya `10.0.2.2` untuk Android Emulator) sesuai dengan mesin *host* backend Anda.

## Alur Implementasi RAG (Pipeline)

Informasi detail mengenai teori dan alur pemrosesan pemrosesan teks (STKI) dari ujung ke ujung telah didokumentasikan di dalam berkas dokumentasi internal backend. Silakan merujuk pada:
**[Dokumentasi Implementasi STKI Backend](backend/README.md)**.
