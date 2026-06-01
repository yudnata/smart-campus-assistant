# Panduan Pemasukan Data (Data Ingestion Guide)

Dokumen ini menjelaskan cara memasukkan data dari berbagai sumber (PDF, CSV, JSON, dan URL) ke dalam *database* PostgreSQL agar dapat dicari oleh sistem *Smart Campus Information Assistant*.

Semua file akan diproses melalui endpoint `POST /api/ingest/file` atau `POST /api/ingest/url`. Anda dapat menggunakan **Postman**, **cURL (Terminal)**, atau membuat antarmuka (UI) di Flutter/React Anda.

---

## 1. Memasukkan Data File PDF
**Kapan digunakan?** Untuk buku pedoman resmi, SK Rektor, atau dokumen panjang. Sistem menggunakan `PDFPlumber` sehingga struktur tabel akan dipertahankan.
*(Catatan: Jika Anda memiliki file **.docx**, harap *Save As* menjadi **.pdf** terlebih dahulu sebelum diunggah).*

**Contoh via cURL (Terminal):**
```bash
curl -X POST "http://localhost:3001/api/ingest/file" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/lokasi/folder/Buku_Pedoman_Akademik_2024.pdf" \
  -F "prodi=Fakultas Teknik" \
  -F "bab=Panduan Umum"
```

---

## 2. Memasukkan Data File CSV
**Kapan digunakan?** Sangat direkomendasikan untuk memasukkan daftar **Tanya Jawab (FAQ)** atau data tabular spesifik agar akurasinya 100%.

**Format `data.csv` yang wajib diikuti:**
(Boleh menggunakan *header* apa saja, contoh: pertanyaan, jawaban)
```csv
pertanyaan,jawaban
"Berapa jumlah SKS minimal untuk lulus?","Mahasiswa wajib menyelesaikan 144 SKS."
"Kapan batas akhir pembayaran UKT?","Batas akhir pembayaran UKT adalah 2 minggu sebelum KRS dimulai."
```

**Contoh via cURL (Terminal):**
```bash
curl -X POST "http://localhost:3001/api/ingest/file" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/lokasi/folder/data-faq.csv" \
  -F "bab=FAQ UKT dan SKS"
```

---

## 3. Memasukkan Data File JSON
**Kapan digunakan?** Jika data diekspor dari sistem/database kampus lain. JSON harus berisi *Array of Objects*.

**Format `data.json` yang wajib diikuti:**
```json
[
  {
    "pertanyaan": "Apa itu Cuti Akademik?",
    "jawaban": "Cuti akademik adalah penundaan masa kuliah yang disetujui Dekan."
  },
  {
    "syarat_skripsi": "Telah lulus minimal 120 SKS tanpa nilai E."
  }
]
```

**Contoh via cURL (Terminal):**
```bash
curl -X POST "http://localhost:3001/api/ingest/file" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/lokasi/folder/data-sistem.json" \
  -F "prodi=Sistem Informasi"
```

---

## 4. Memasukkan Data dari Link Website (URL)
**Kapan digunakan?** Untuk menarik data dinamis seperti Jadwal Kalender Akademik atau pengumuman terbaru langsung dari website kampus.

**Contoh via cURL (Terminal):**
Endpoint yang digunakan adalah `/api/ingest/url`, dengan format JSON *raw body*.
```bash
curl -X POST "http://localhost:3001/api/ingest/url" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"https://unud.ac.id/kalender-akademik\"}"
```

---

## 💡 Panduan Ekstra menggunakan Postman
Bagi Anda yang lebih menyukai antarmuka visual (GUI):
1. Buka aplikasi Postman.
2. Buat Request baru, pilih metode **POST**, masukkan URL `http://localhost:3001/api/ingest/file`.
3. Buka tab **Body**, lalu pilih opsi **form-data**.
4. Isi kolom `Key` dengan `file`. Arahkan kursor ke tulisan `file` tersebut hingga muncul menu *dropdown* `Text / File` di sebelah kanannya. Ubah menjadi **File**.
5. Di kolom `Value`, sebuah tombol `Select Files` akan muncul. Klik dan pilih file PDF/CSV/JSON Anda.
6. (Opsional) Tambahkan baris baru di bawahnya: `Key` = `prodi`, `Value` = `Teknik Informatika`.
7. Tekan tombol **Send**.

## Apa yang Terjadi Setelah Data Diunggah?
Setiap kali Anda menekan "Send", teks dari dokumen akan langsung dipotong-potong (*chunking* sebesar 1500 karakter), diubah menjadi angka matematika (*embedding*), dan disimpan secara permanen di dalam PostgreSQL Anda. 
Data tersebut **seketika langsung bisa diuji coba** di dalam fitur *Chatbot* Anda!
