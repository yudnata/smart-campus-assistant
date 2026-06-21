# Data Extraction & Processing

Direktori ini dikhususkan untuk tugas-tugas Tim **Data Science**, yang berfokus pada ekstraksi teks dari PDF mentah (seperti Pedoman Akademik), pembersihan data, dan pemotongan teks (*chunking*) agar siap dimasukkan ke dalam *Vector Database*.

## Alur Kerja (Workflow)
Dalam arsitektur *Best Practice*, Data Science tidak melakukan *push* langsung ke *database* produksi. Alur kerjanya adalah sebagai berikut:
1. Menempatkan dokumen PDF mentah di `data/raw/` (jika ada).
2. Mengeksekusi Jupyter Notebook untuk melakukan ekstraksi dan *chunking*.
3. Menghasilkan *file* output statis berupa `data/processed/chunks/chunks.json`.
4. (Selesai) Tim Backend atau skrip Backend akan mengambil `chunks.json` ini untuk melakukan *embedding* dan memasukkannya ke PostgreSQL.

## Struktur Direktori
- `notebooks/`: Berisi Jupyter Notebook interaktif. Mulai dari sini!
  - `01_data_extraction_and_chunking.ipynb`: Notebook utama untuk mengekstrak PDF, melakukan *cleaning* Markdown, dan *semantic chunking*.
- `data/`: Folder penyimpanan *file* lokal.
  - `raw/`: Tempat menaruh PDF asli.
  - `processed/`: Tempat hasil ekstrak Markdown (`cleaned/`) dan hasil akhir *chunks* (`chunks/`).
- `requirements.txt`: Daftar pustaka khusus Data Science (terpisah dari Backend).

## Panduan Instalasi dan Penggunaan

1. **Persiapan Lingkungan Virtual** (Opsional namun disarankan):
   ```bash
   cd data_extraction
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```

2. **Instal Dependensi**:
   Pastikan menginstal kebutuhan pustaka khusus seperti `pdfplumber`, `PyMuPDF`, dan `jupyter`:
   ```bash
   pip install -r requirements.txt
   ```

3. **Jalankan Jupyter Notebook**:
   ```bash
   jupyter notebook
   ```
   Lalu buka folder `notebooks/` dan eksekusi sel di `01_data_extraction_and_chunking.ipynb` secara berurutan.

4. **Output**:
   Pastikan Anda melihat pesan "Total chunk: XXX" dan *file* `chunks.json` berhasil terbuat di dalam folder `data/processed/chunks/`. Setelah *file* ini terbentuk, tugas ekstraksi selesai.
