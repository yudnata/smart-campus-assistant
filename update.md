# Changelog & Updates

Dokumen ini melacak seluruh pembaruan arsitektural dan penulisan ulang kode yang diterapkan pada sistem STKI.

## [Pembaruan Arsitektur & Performa] - Sesi Refactor Terakhir

### 1. Migrasi Layer Data Science ke Jupyter Notebook
- **[NEW]** Logika ekstraksi teks PDF dan *semantic chunking* dipindahkan sepenuhnya ke dalam lingkungan interaktif `data_extraction/notebooks/01_data_extraction_and_chunking.ipynb`. Hal ini memisahkan tugas riset Data Science dari lingkungan Backend.
- **[NEW]** Menambahkan `data_extraction/requirements.txt` terpisah khusus kebutuhan riset (seperti `pdfplumber`, `jupyter`, `PyMuPDF`).
- **[DELETE]** Membersihkan repositori dengan menghapus skrip *legacy* `data_extraction.py` dan `preprocessing_chunking.py`.
- **[NEW]** Menambahkan `data_extraction/README.md` untuk memandu proses Data Science dari bahan mentah (*raw*) hingga memproduksi `chunks.json`.

### 2. Standardisasi Struktur Backend (FastAPI Best Practices)
- **[NEW]** Menambahkan *placeholder folders* (`.gitkeep`) untuk `backend/app/schemas`, `backend/app/crud`, dan `backend/app/utils` untuk memastikan skalabilitas proyek sesuai dengan arsitektur standar FastAPI.
- **[FIX]** Memperbaiki seluruh *import error* pada *routing* dan *services* (khususnya di `chat_service.py`, `endpoints.py`, `ingest_service.py`) akibat perubahan skema database lama (`Document` diubah menjadi referensi tabel/model `DocumentChunk` yang benar).

### 3. Pembaruan Knowledge & Logika Overwrite Dokumen Baru
- **[NEW]** Menambahkan kapabilitas *update* dokumen tahunan. Sistem API backend (`/api/ingest/file`) dan modul `ingest_service.py` sekarang memiliki paramater `overwrite_old: bool = True`.
- **[UPDATE]** Ketika dokumen berformat sama (misal: "Pedoman Akademik 2025.pdf") diunggah, sistem otomatis menjalankan kueri `DELETE` untuk menghapus *chunks* milik dokumen dengan nama file yang sama sebelumnya, mencegah kebingungan LLM akibat data duplikat lintas-tahun.

### 4. Upgrade Dimensi Model Embedding (Supercharging Retrieval)
- **[UPDATE]** Mengganti model *embedding* standar dari dimensi 384 (`sentence-transformers/all-MiniLM-L6-v2`) menjadi model *high-performance multilingual* **1024 dimensi** (`intfloat/multilingual-e5-large`).
- **[UPDATE]** Skema *database* pgvector di `DocumentChunk` telah diperbarui dari `Vector(384)` menjadi `Vector(1024)`. Konsekuensinya, *table* lama harus di-*drop* dan dibuat ulang.
- **[UPDATE]** Menyelaraskan nama model `MODEL_NAME` di skrip CLI seperti `ingest_chunks.py` dan `retrieval_test.py`.

### 5. Pembaruan Dokumentasi Ekstensif
- **[UPDATE]** Memperluas `backend/README.md` untuk menyertakan instruksi instalasi lengkap, panduan mengaktifkan *virtual environment*, langkah-langkah *setup database* PostgreSQL (`pgvector`), dan cara menjalankan server FastAPI secara lokal (`uvicorn main:app --reload`).

---
*Catatan: Semua perubahan di atas dilakukan secara eksklusif pada layer Data Science dan Backend. Tidak ada kode pada aplikasi Flutter (Mobile) yang disentuh untuk memastikan stabilitas Front-end.*
