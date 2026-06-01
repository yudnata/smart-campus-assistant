# Implementasi Sistem Temu Kembali Informasi (STKI) Berbasis RAG

Dokumen ini menguraikan metodologi dan alur kerja Sistem Temu Kembali Informasi (STKI) yang diterapkan dalam proyek ini, mulai dari pemrosesan dokumen mentah hingga penyajian jawaban akhir melalui antarmuka pemrograman aplikasi (API).

Sistem ini menggunakan arsitektur **RAG (Retrieval-Augmented Generation)**, yang merupakan evolusi dari STKI tradisional. Dalam RAG, proses *retrieval* (pencarian) tradisional digunakan untuk menemukan dokumen yang relevan, sementara *Large Language Model* (LLM) digunakan di tahap akhir murni sebagai instrumen untuk menyempurnakan dan memformat jawaban (bukan sebagai sumber memori utama).

Alur kerja sistem dibagi menjadi dua fase utama: **Fase Ingestion (Pemasukan Data)** dan **Fase Retrieval & Generation (Pencarian & Penjawaban)**.

---

## 1. Fase Ingestion (Pemasukan Data)

Fase ini bertanggung jawab untuk mengubah dokumen sumber (seperti PDF Pedoman Akademik atau halaman Website) menjadi format matematis yang dapat dipahami dan dicari oleh komputer.

1. **Pengumpulan Teks (Parsing)**
   Dokumen dari berbagai format diekstraksi menjadi teks biasa (string). Dalam sistem ini, `PyPDFLoader` digunakan untuk membaca teks per halaman dari berkas PDF, sementara `WebBaseLoader` men-scrape elemen teks dari HTML.
   
2. **Pemecahan Teks (Chunking)**
   Teks yang panjang tidak dapat langsung dimasukkan ke dalam basis data karena konteksnya terlalu luas dan melampaui batas masukan model AI. Oleh karena itu, teks dipecah menjadi unit-unit kecil yang disebut *chunks* (potongan). 
   Sistem ini menggunakan teknik `RecursiveCharacterTextSplitter` yang memotong teks setiap 500 karakter dengan sedikit tumpang tindih (*overlap* sebesar 50 karakter) agar tidak ada kalimat krusial yang terpotong di tengah jalan.

3. **Penyandian Vektor (Embedding)**
   Setiap *chunk* teks kemudian dikonversi menjadi representasi vektor numerik (deretan angka). Sistem ini menggunakan model bahasa khusus bernama `all-MiniLM-L6-v2` yang menghasilkan ruang vektor berdimensi 384. Model ini sangat efisien dalam menangkap relasi semantik (makna kalimat).

4. **Penyimpanan (Indexing)**
   Teks asli ( *chunk* ), metadata (sumber dokumen, nomor halaman), dan representasi vektor numeriknya disimpan bersamaan ke dalam PostgreSQL yang telah dilengkapi dengan ekstensi `pgvector`. Struktur ini memungkinkan basis data untuk memproses perhitungan matematis jarak antar vektor.

---

## 2. Fase Retrieval & Generation (Pencarian & Penjawaban)

Fase ini berlangsung secara otomatis (dan dalam waktu sepersekian detik) setiap kali pengguna mengirimkan pertanyaan (kueri) melalui aplikasi Mobile atau antarmuka Web.

1. **Vektorisasi Kueri Pengguna**
   Pertanyaan yang dikirimkan oleh pengguna ("Berapa SKS maksimal di semester 3?") ditangkap oleh *endpoint API* (`/api/chat`). Teks pertanyaan ini kemudian diubah menjadi vektor numerik menggunakan model embedding yang sama persis seperti pada Fase Ingestion (`all-MiniLM-L6-v2`).

2. **Pencarian Relevansi (Vector Retrieval)**
   Sistem melakukan pencarian pada tabel PostgreSQL menggunakan metrik **Cosine Similarity** (atau Cosine Distance). Basis data menghitung kedekatan (sudut kemiripan) antara vektor pertanyaan pengguna dengan puluhan ribu vektor *chunk* yang ada di dalam database.
   Hanya *Top-K* dokumen (misalnya 5 potongan teks dengan nilai kedekatan tertinggi) yang diambil. Ini adalah esensi utama dari STKI tradisional yang ditingkatkan dengan pencarian berbasis kedekatan semantik.

3. **Injeksi Konteks (Prompt Formulation)**
   Kelima teks yang paling relevan (beserta metadatanya) tersebut digabungkan ke dalam sebuah templat instruksi (*Prompt*) yang dirancang khusus.
   Contoh format logika templat:
   > "Anda adalah asisten akademik. Berdasarkan dokumen berikut: [Teks 1], [Teks 2]... Tolong jawab pertanyaan ini: [Pertanyaan Pengguna]. Jangan mengarang jawaban di luar konteks."

4. **Penyempurnaan Bahasa (LLM Generation)**
   *Prompt* yang berisi konteks pasti tersebut dikirimkan ke Large Language Model (misalnya Gemini 1.5 Flash atau GPT-4o-mini). Karena LLM telah dikunci oleh instruksi untuk hanya menggunakan konteks yang disediakan (hasil *retrieval* STKI), masalah halusinasi LLM dapat ditekan hingga mendekati nol. LLM membaca fakta matematis hasil *retrieval* dan menyusunnya menjadi kalimat manusiawi yang komprehensif.

5. **Pengiriman API ke Klien**
   Backend FastAPI merangkum teks jawaban akhir dari LLM, beserta statistik waktu pencarian dan kutipan sumber aslinya (metadatanya), lalu mengemasnya menjadi format JSON. 
   Respons JSON ini dikirimkan kembali ke Frontend React (Website) dan Frontend Flutter (Mobile App) untuk dirender sebagai gelembung pesan (*message bubble*).

Dengan mekanisme ini, aplikasi Mobile dan Website tetap sangat ringan karena seluruh beban komputasi STKI, pencarian ruang vektor tingkat lanjut, dan intervensi LLM sepenuhnya diproses oleh arsitektur Backend Python ini.
