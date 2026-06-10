# Implementasi Sistem Temu Kembali Informasi (STKI) Berbasis RAG

Dokumen ini menguraikan metodologi dan alur kerja Sistem Temu Kembali Informasi (STKI) yang diterapkan dalam proyek ini, mulai dari pemrosesan dokumen mentah hingga penyajian jawaban akhir melalui antarmuka pemrograman aplikasi (API).

Sistem ini menggunakan arsitektur **RAG (Retrieval-Augmented Generation)**, yang merupakan evolusi dari STKI tradisional. Dalam RAG, proses *retrieval* (pencarian) tradisional digunakan untuk menemukan dokumen yang relevan, sementara *Large Language Model* (LLM) digunakan di tahap akhir murni sebagai instrumen untuk menyempurnakan dan memformat jawaban (bukan sebagai sumber memori utama).

Alur kerja sistem dibagi menjadi dua fase utama: **Fase Ingestion (Pemasukan Data)** dan **Fase Retrieval & Generation (Pencarian & Penjawaban)**.

---

## 1. Fase Ingestion (Pemasukan Data)

Fase ini bertanggung jawab untuk mengubah dokumen sumber (seperti PDF Pedoman Akademik atau halaman Website) menjadi format matematis yang dapat dipahami dan dicari oleh komputer.

1. **Pengumpulan Teks & Metadata (Parsing)**
   Dokumen dari berbagai format diekstraksi menjadi teks biasa (string). Dalam sistem ini, `PDFPlumberLoader` digunakan karena keakuratannya menjaga struktur tabel, didukung dengan `CSVLoader` dan `JSON` parser untuk data terstruktur, serta `WebBaseLoader` untuk HTML. Saat pengunggahan, metadata khusus (seperti `prodi` dan `bab`) dapat disisipkan untuk mempertajam pencarian.
   
2. **Pemecahan Teks (Semantic Chunking)**
   Teks dipecah menjadi unit-unit kecil (*chunks*). Sistem ini menggunakan `RecursiveCharacterTextSplitter` yang memotong teks setiap 1500 karakter dengan tumpang tindih (*overlap*) sebesar 200 karakter. Ukuran ini menjaga konteks aturan (seperti syarat kelulusan) tetap utuh dalam satu bagian.

3. **Penyandian Vektor (Embedding)**
   Setiap *chunk* teks dikonversi menjadi representasi vektor numerik (berdimensi 384) menggunakan model `all-MiniLM-L6-v2`.

4. **Penyimpanan (Indexing)**
   Teks asli, metadata, dan vektor disimpan ke dalam PostgreSQL. Database ini memanfaatkan ekstensi `pgvector` untuk pencarian vektor matematis dan fitur bawaan PostgreSQL `tsvector` untuk pencarian teks penuh (Full Text Search).

---

## 2. Fase Retrieval & Generation (Pencarian & Penjawaban)

Fase ini berlangsung secara otomatis (dan dalam waktu sepersekian detik) setiap kali pengguna mengirimkan pertanyaan (kueri) melalui aplikasi Mobile atau antarmuka Web.

1. **Pencarian Ganda (Hybrid Search Retrieval)**
   Pertanyaan pengguna ditangkap oleh `/api/chat` dan sistem langsung menjalankan DUA metode pencarian secara paralel ke dalam database PostgreSQL:
   - **Vector Search (Dense Retrieval):** Mengubah pertanyaan menjadi vektor lalu mencari kedekatan makna (*Cosine Similarity*) menggunakan `pgvector`.
   - **Keyword Search (Sparse Retrieval):** Melakukan pencarian kecocokan kata persis menggunakan *Full Text Search* (`to_tsvector` dan `plainto_tsquery`), yang sangat ampuh untuk menangkap singkatan lokal kampus (misal: "UKT", "KRS").

2. **Penggabungan Peringkat (Reciprocal Rank Fusion - RRF)**
   Hasil dari kedua metode pencarian digabungkan dan diurutkan ulang menggunakan algoritma *Reciprocal Rank Fusion* (RRF). Algoritma ini memastikan bahwa dokumen yang memiliki makna relevan sekaligus mengandung kata kunci persis akan naik ke peringkat teratas. Hanya dokumen *Top-K* terbaik yang diambil.

3. **Injeksi Konteks (Prompt Formulation)**
   Teks yang paling relevan beserta metadatanya disuntikkan ke dalam *Prompt* LLM. 
   LLM diinstruksikan dengan ketat untuk **selalu mengutip sumber (bab/prodi/nama dokumen)** di akhir jawabannya dan dilarang keras mengarang jawaban (mencegah *hallucination*).

4. **Penyempurnaan Bahasa (LLM Generation)**
   *Prompt* yang berisi konteks pasti tersebut dikirimkan ke Large Language Model (misalnya Gemini 1.5 Flash atau GPT-4o-mini). Karena LLM telah dikunci oleh instruksi untuk hanya menggunakan konteks yang disediakan (hasil *retrieval* STKI), masalah halusinasi LLM dapat ditekan hingga mendekati nol. LLM membaca fakta matematis hasil *retrieval* dan menyusunnya menjadi kalimat manusiawi yang komprehensif.

5. **Pengiriman API ke Klien**
   Backend FastAPI merangkum teks jawaban akhir dari LLM, beserta statistik waktu pencarian dan kutipan sumber aslinya (metadatanya), lalu mengemasnya menjadi format JSON. 
   Respons JSON ini dikirimkan kembali ke Frontend React (Website) dan Frontend Flutter (Mobile App) untuk dirender sebagai gelembung pesan (*message bubble*).

Dengan mekanisme ini, aplikasi Mobile dan Website tetap sangat ringan karena seluruh beban komputasi STKI, pencarian ruang vektor tingkat lanjut, dan intervensi LLM sepenuhnya diproses oleh arsitektur Backend Python ini.

---

## 3. Panduan Instalasi dan Menjalankan Backend

### Persyaratan Sistem
- Python 3.10+
- PostgreSQL dengan ekstensi `pgvector`
- Virtual Environment (disarankan)

### Instalasi
1. Masuk ke direktori `backend/`:
   ```bash
   cd backend
   ```
2. Buat dan aktifkan Virtual Environment:
   ```bash
   python -m venv venv
   # Di Windows:
   venv\Scripts\activate
   # Di Linux/Mac:
   source venv/bin/activate
   ```
3. Instal semua dependensi:
   ```bash
   pip install -r requirements.txt
   ```
4. Salin file environment:
   ```bash
   cp .env.example .env
   # Buka .env dan atur koneksi PostgreSQL (DATABASE_URL) 
   # serta API Key LLM Anda (GOOGLE_API_KEY atau OPENAI_API_KEY).
   ```

### Menyiapkan Database
Pastikan Anda sudah menginstal ekstensi `pgvector` di PostgreSQL Anda.
Jika sebelumnya Anda menggunakan dimensi vektor 384 dan sekarang menggunakan versi terbaru 1024, **Anda harus menghapus tabel lama terlebih dahulu**:
```sql
DROP TABLE IF EXISTS document_chunks;
```

### Menjalankan Server
Untuk menjalankan API server FastAPI secara lokal:
```bash
uvicorn main:app --reload --port 3001
```
Aplikasi akan tersedia di:
- Base URL: `http://localhost:3001`
- Dokumentasi API Otomatis (Swagger): `http://localhost:3001/docs`

### Endpoint Utama
- `POST /api/chat`: Mengirimkan pertanyaan ke STKI RAG. Menerima `question` dan `topK`.
- `POST /api/ingest/file`: Mengunggah file PDF, CSV, atau JSON ke database (otomatis menimpa versi lama jika `overwrite_old=True`).
- `POST /api/ingest/url`: Menarik data halaman web untuk diubah menjadi *vector chunks*.
- `GET /api/stats`: Mengembalikan jumlah total dokumen (chunks) yang ada di database.
