from pathlib import Path
import re
import sys

import pdfplumber
import fitz  # PyMuPDF


# ============================================================
# KONFIGURASI PATH
# ============================================================
# BASE_DIR = lokasi file data_loading.py berada.
# Dengan cara ini, path tidak bergantung pada terminal dijalankan dari folder mana.
BASE_DIR = Path(__file__).resolve().parent

RAW_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "markdown"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DEBUG_OCR_DIR = BASE_DIR / "data" / "processed" / "debug_ocr"
DEBUG_OCR_DIR.mkdir(parents=True, exist_ok=True)

SAVE_OCR_DEBUG = True

PEDOMAN_PDF = RAW_DIR / "Buku Pedoman Akademik Sarjana FT 2024.pdf"
KALENDER_PDF = RAW_DIR / "Kalender Akademik 2025-2026.pdf"


# ============================================================
# UTILITAS DASAR
# ============================================================
def check_file_exists(path: Path) -> None:
    """
    Mengecek apakah file PDF ditemukan.
    Jika tidak ditemukan, tampilkan folder yang dicek dan isi foldernya.
    """
    if path.exists():
        print(f"[OK] File ditemukan: {path}")
        return

    print(f"\n[ERROR] File tidak ditemukan: {path}")
    print(f"Folder yang dicek: {path.parent}")

    if path.parent.exists():
        print("\nIsi folder tersebut:")
        for file in path.parent.iterdir():
            print(f"- {file.name}")
    else:
        print("\nFolder tersebut belum ada.")

    raise FileNotFoundError(f"File tidak ditemukan: {path}")


def clean_text(text: str) -> str:
    """
    Membersihkan teks hasil ekstraksi PDF.
    """
    if not text:
        return ""

    text = text.replace("\x00", " ")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def normalize_pedoman_text(text: str) -> str:
    """
    Menggabungkan newline yang hanya terjadi karena line wrapping PDF,
    tetapi tetap menjaga heading, list, tabel markdown, dan metadata.
    """
    if not text:
        return ""

    lines = [line.strip() for line in text.splitlines()]
    output = []
    paragraph_buffer = []

    def flush_paragraph():
        nonlocal paragraph_buffer
        if paragraph_buffer:
            paragraph = " ".join(paragraph_buffer)
            paragraph = re.sub(r"\s+", " ", paragraph).strip()
            output.append(paragraph)
            paragraph_buffer = []

    def is_structural_line(line: str) -> bool:
        return (
            line.startswith("#")
            or line.startswith("<!--")
            or line.startswith("|")
            or re.match(r"^BAGIAN\s+\d+", line)
            or re.match(r"^LAMPIRAN\s+[A-Z]", line)
            or re.match(r"^\d+(\.\d+)*\s+", line)      # 4.1 Registrasi Akademik
            or re.match(r"^[A-Z]\.\s+", line)          # A. Registrasi Mahasiswa Baru
            or re.match(r"^\d+\.\s+", line)            # 1. Mahasiswa ...
            or re.match(r"^[a-z]\)\s+", line)          # a) Kartu ...
        )

    for line in lines:
        if not line:
            flush_paragraph()
            output.append("")
            continue

        if is_structural_line(line):
            flush_paragraph()
            output.append(line)
        else:
            paragraph_buffer.append(line)

    flush_paragraph()

    return "\n".join(output).strip()

def clean_markdown_cell(cell) -> str:
    """
    Membersihkan isi cell tabel agar aman saat dijadikan Markdown Table.
    """
    if cell is None:
        return ""

    cell = str(cell)
    cell = cell.replace("\n", " ")
    cell = cell.replace("|", "\\|")
    cell = re.sub(r"\s+", " ", cell)
    return cell.strip()


def table_to_markdown(table) -> str:
    """
    Mengubah tabel hasil pdfplumber menjadi Markdown Table.
    """
    if not table:
        return ""

    cleaned_rows = []
    for row in table:
        if not row:
            continue

        cleaned_row = [clean_markdown_cell(cell) for cell in row]

        # Lewati baris yang benar-benar kosong
        if any(cell for cell in cleaned_row):
            cleaned_rows.append(cleaned_row)

    if not cleaned_rows:
        return ""

    max_cols = max(len(row) for row in cleaned_rows)

    normalized_rows = []
    for row in cleaned_rows:
        row = row + [""] * (max_cols - len(row))
        normalized_rows.append(row)

    header = normalized_rows[0]

    # Jika header kosong semua, buat header otomatis
    if not any(header):
        header = [f"Kolom {i + 1}" for i in range(max_cols)]
        body = normalized_rows[1:]
    else:
        body = normalized_rows[1:]

    md = []
    md.append("| " + " | ".join(header) + " |")
    md.append("| " + " | ".join(["---"] * max_cols) + " |")

    for row in body:
        md.append("| " + " | ".join(row) + " |")

    return "\n".join(md)


def write_markdown(output_path: Path, markdown_parts: list[str]) -> None:
    """
    Menulis hasil ekstraksi ke file Markdown.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n\n".join(part for part in markdown_parts if part and part.strip())
    output_path.write_text(content, encoding="utf-8")
    print(f"[OK] File Markdown berhasil dibuat: {output_path}")


# ============================================================
# EKSTRAKSI PDF TEKS + TABEL
# Cocok untuk Buku Pedoman Akademik FT
# ============================================================
def extract_pdf_text_and_tables_to_markdown(pdf_path: Path, output_path: Path) -> None:
    """
    Mengekstrak teks dan tabel dari PDF menggunakan pdfplumber,
    lalu menyimpannya dalam format Markdown.
    """
    check_file_exists(pdf_path)

    markdown_parts = []
    total_text_chars = 0
    total_tables = 0

    print(f"\n[INFO] Memproses PDF: {pdf_path.name}")

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            raw_text = page.extract_text() or ""
            text = clean_text(raw_text)
            text = normalize_pedoman_text(text)

            total_text_chars += len(text)

            markdown_parts.append(f"# Halaman {page_number}")
            markdown_parts.append(
                f"<!-- source: {pdf_path.name} | page: {page_number} | type: text -->"
            )

            if text:
                markdown_parts.append(text)
            else:
                markdown_parts.append("_Tidak ada teks yang berhasil diekstrak pada halaman ini._")

            # Ekstraksi tabel pada halaman yang sama
            try:
                tables = page.extract_tables() or []
            except Exception as e:
                print(f"[WARNING] Gagal ekstrak tabel halaman {page_number}: {e}")
                tables = []

            for table_index, table in enumerate(tables, start=1):
                md_table = table_to_markdown(table)

                if md_table:
                    total_tables += 1
                    markdown_parts.append(
                        f"<!-- source: {pdf_path.name} | page: {page_number} | type: table | table_index: {table_index} -->"
                    )
                    markdown_parts.append(md_table)

    write_markdown(output_path, markdown_parts)

    print(f"[INFO] Total karakter teks: {total_text_chars}")
    print(f"[INFO] Total tabel terdeteksi: {total_tables}")


# ============================================================
# EKSTRAKSI KALENDER AKADEMIK
# Pertama coba teks/tabel digital.
# Jika hasil terlalu sedikit, gunakan OCR fallback.
# ============================================================
def extract_calendar_with_pymupdf(pdf_path: Path) -> list[dict]:
    """
    Mencoba ekstraksi teks Kalender Akademik menggunakan PyMuPDF.
    """
    check_file_exists(pdf_path)

    doc = fitz.open(pdf_path)
    results = []

    for page_index, page in enumerate(doc, start=1):
        text = clean_text(page.get_text("text") or "")
        results.append(
            {
                "page": page_index,
                "text": text,
                "char_count": len(text),
            }
        )

    doc.close()
    return results


def ocr_page_with_pymupdf(page, zoom: int = 3, return_raw: bool = False) -> str:
    """
    OCR halaman PDF dengan cara:
    1. Render halaman PDF menjadi gambar menggunakan PyMuPDF.
    2. Baca gambar menggunakan pytesseract.

    return_raw=True dipakai untuk menyimpan hasil OCR mentah sebelum cleaning.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:
        raise ImportError(
            "Library OCR belum tersedia. Install dulu dengan:\n"
            "pip install pytesseract pillow\n\n"
            "Selain itu, install aplikasi Tesseract OCR di Windows."
        ) from e

    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)

    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    try:
        text = pytesseract.image_to_string(image, lang="ind+eng")
    except Exception:
        text = pytesseract.image_to_string(image, lang="eng")

    if return_raw:
        return text

    return clean_text(text)

def save_ocr_debug_files(page_number: int, raw_ocr_text: str) -> None:
    """
    Menyimpan beberapa versi hasil OCR untuk kebutuhan pengecekan:
    1. raw OCR asli dari Tesseract,
    2. raw OCR dengan nomor baris,
    3. cleaned OCR setelah clean_text(),
    4. cleaned calendar lines setelah clean_calendar_line().
    """
    if not SAVE_OCR_DEBUG:
        return

    # 1. Raw OCR asli
    raw_path = DEBUG_OCR_DIR / f"calendar_page_{page_number}_raw_ocr.txt"
    raw_path.write_text(raw_ocr_text, encoding="utf-8")

    # 2. Raw OCR dengan nomor baris
    raw_lines = raw_ocr_text.splitlines()
    numbered_lines = []

    for index, line in enumerate(raw_lines, start=1):
        numbered_lines.append(f"{index:03d}: {line}")

    numbered_path = DEBUG_OCR_DIR / f"calendar_page_{page_number}_raw_ocr_numbered.txt"
    numbered_path.write_text("\n".join(numbered_lines), encoding="utf-8")

    # 3. OCR setelah clean_text()
    cleaned_text = clean_text(raw_ocr_text)
    cleaned_path = DEBUG_OCR_DIR / f"calendar_page_{page_number}_cleaned_text.txt"
    cleaned_path.write_text(cleaned_text, encoding="utf-8")

    # 4. OCR setelah clean_calendar_line() per baris
    calendar_cleaned_lines = []

    for index, line in enumerate(raw_ocr_text.splitlines(), start=1):
        cleaned_line = clean_calendar_line(line)

        if cleaned_line:
            calendar_cleaned_lines.append(f"{index:03d}: {cleaned_line}")

    calendar_cleaned_path = DEBUG_OCR_DIR / f"calendar_page_{page_number}_cleaned_calendar_lines.txt"
    calendar_cleaned_path.write_text("\n".join(calendar_cleaned_lines), encoding="utf-8")


# ============================================================
# REKONSTRUKSI KALENDER AKADEMIK MENJADI MARKDOWN TABLE
# ============================================================

MONTHS = (
    r"(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|"
    r"September|Oktober|Nopember|November|Desember)"
)

DATE_PATTERN = rf"""
(?:
    \d{{1,2}}\s*[-–]\s*\d{{1,2}}\s+{MONTHS}
    (?:\s+dan\s+\d{{1,2}}\s*[-–]\s*\d{{1,2}}\s+{MONTHS})?
    \s+\d{{4}}
    |
    \d{{1,2}}\s+{MONTHS}\s*[-–]\s*\d{{1,2}}\s+{MONTHS}\s+\d{{4}}
    |
    \d{{1,2}}\s+{MONTHS}\s+\d{{4}}\s*[-–]\s*\d{{1,2}}\s+{MONTHS}\s+\d{{4}}
    |
    \d{{1,2}}\s+{MONTHS}\s+\d{{4}}
    |
    {MONTHS}\s*[-–]\s*{MONTHS}\s+\d{{4}}
    |
    {MONTHS}\s+\d{{4}}
)
"""

DATE_RE = re.compile(DATE_PATTERN, re.VERBOSE | re.IGNORECASE)

SECTION_RE = re.compile(
    r"^(I|II|III|IV|V|VI|VII|VIII|IX|X|Il|ll|lll)\.\s+",
    re.IGNORECASE,
)

NEW_EVENT_START_RE = re.compile(
    r"^(Registrasi|Penetapan|Pengisian|Pendaftaran|Pengumuman|Proses|"
    r"Pelaksanaan|Verifikasi|Ujian|Tes|Pembayaran|Perubahan|Kuliah|"
    r"Perkuliahan|Batas|Validasi|Pelaporan|Rekonsiliasi|Audit|Rapat|"
    r"Monitor|Pengukuhan|PKKMB|Wisuda)\b",
    re.IGNORECASE,
)

SUBHEADING_RE = re.compile(
    r"^(PENDAFTARAN DAN PENETAPAN KELULUSAN|PENDAFTARAN WISUDA)$",
    re.IGNORECASE,
)


def remove_event_prefix(line: str) -> str:
    """
    Menghapus prefix nomor atau huruf agar pendeteksi kegiatan lebih akurat.

    Contoh:
    'B. Pendaftaran Kelulusan April 2026' -> 'Pendaftaran Kelulusan April 2026'
    'C, Pendaftaran Kelulusan Mei 2026' -> 'Pendaftaran Kelulusan Mei 2026'
    '18 | Pelaksanaan Kuliah Kerja Nyata' -> 'Pelaksanaan Kuliah Kerja Nyata'
    """
    line = clean_calendar_line(line)

    # Hapus nomor tabel, misalnya: "18 | ..."
    line = re.sub(r"^\d+\s*[|.)]\s*", "", line).strip()

    # Hapus prefix huruf, misalnya: "A. ...", "B. ...", "C, ..."
    line = re.sub(r"^[A-Z][\.,]\s*", "", line).strip()

    # Hapus prefix huruf kecil, misalnya: "a) ..."
    line = re.sub(r"^[a-z]\)\s*", "", line).strip()

    return line


def is_calendar_subheading(line: str) -> bool:
    """
    Mendeteksi subjudul di dalam bagian kalender.
    Contoh:
    PENDAFTARAN DAN PENETAPAN KELULUSAN
    PENDAFTARAN WISUDA
    """
    line = remove_event_prefix(line)
    return SUBHEADING_RE.match(line) is not None


def is_new_calendar_event_line(line: str) -> bool:
    """
    Mendeteksi apakah sebuah baris adalah awal kegiatan baru.
    Versi ini bisa mengenali:
    - Penetapan Kelulusan Maret 2026
    - B. Pendaftaran Kelulusan April 2026
    - C, Pendaftaran Kelulusan Mei 2026
    - Wisuda ke - 175
    """
    cleaned = clean_calendar_line(line)
    normalized = remove_event_prefix(cleaned)

    if NEW_EVENT_START_RE.match(normalized):
        return True

    extra_starts = (
        "Pendaftaran Kelulusan",
        "Penetapan Kelulusan",
        "Pendaftaran Wisuda",
        "Wisuda ke",
        "Pelaksanaan Kuliah Kerja Nyata",
    )

    return normalized.startswith(extra_starts)

def normalize_ocr_noise(text: str) -> str:
    """
    Memperbaiki noise OCR yang sering muncul pada kalender.
    """
    replacements = {
        "SELEKS!": "SELEKSI",
        "SELEKS|": "SELEKSI",
        "ll.": "II.",
        "lll.": "III.",
        "Il.": "II.",
        "Nopember": "November",
    }

    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)

    text = re.sub(r"\s+", " ", text)
    return text.strip()

def clean_calendar_line(line: str) -> str:
    """
    Membersihkan noise OCR ringan pada setiap baris kalender,
    tetapi tidak menghapus angka tanggal di awal baris.
    """
    if not line:
        return ""

    line = line.replace("—", "-")
    line = line.replace("–", "-")
    line = line.replace("~", "-")

    # Hapus nomor baris hanya kalau ada pemisah jelas.
    # Contoh yang dihapus:
    # "8 | Pembayaran UKT"
    # "9 | Pengumuman Mahasiswa Aktif"
    # "10. Pengisian KRS"
    # "11) Perubahan KRS"
    #
    # Contoh yang TIDAK dihapus:
    # "17 Juli - 15 Agustus 2025"
    # "2 Maret - 13 Juli 2026"
    line = re.sub(r"^\s*\d+\s*[|.)]\s*", "", line)

    line = line.replace("|", " ")
    line = re.sub(r"^[,]\s*", "", line)
    line = re.sub(r"\s+", " ", line)

    return normalize_ocr_noise(line)

def is_calendar_noise_line(line: str) -> bool:
    """
    Mendeteksi baris OCR yang kemungkinan besar hanya noise.
    """
    if not line:
        return True

    lowered = line.lower().strip()

    known_noise_patterns = [
        "nio wa",
        "elniau",
        "w)r",
        "wa) w",
    ]

    if any(pattern in lowered for pattern in known_noise_patterns):
        return True

    # Jika terlalu pendek dan tidak punya angka/tanggal/kata penting, abaikan.
    meaningful_keywords = [
        "pendaftaran", "pengumuman", "pembayaran", "pengisian",
        "perubahan", "perkuliahan", "ujian", "wisuda", "kkn",
        "cuti", "registrasi", "validasi", "pelaporan"
    ]

    has_keyword = any(keyword in lowered for keyword in meaningful_keywords)
    has_digit = any(char.isdigit() for char in lowered)

    if len(lowered) <= 12 and not has_keyword and not has_digit:
        return True

    return False

def has_day_number(date_text: str) -> bool:
    """
    Mengecek apakah tanggal memiliki angka hari.
    
    Contoh True:
    - 20 Februari 2026
    - 1-29 April 2026
    - 2 - 26 Maret 2026
    - 17 November 2025 - 5 Januari 2026

    Contoh False:
    - April 2026
    - Maret 2026
    - Juli - Agustus 2026
    """
    return re.search(r"\b\d{1,2}\b", date_text) is not None


def split_activity_and_date(line: str):
    """
    Memisahkan teks kegiatan dan tanggal dari satu baris OCR.

    Prinsip:
    - Kalau ada tanggal kuat yang punya angka hari, ambil sebagai Waktu.
    - Kalau hanya ada 'April 2026' di dalam nama kegiatan, jangan langsung dianggap Waktu.
    - Kalau baris hanya berisi 'Juli - Agustus 2026', tetap boleh dianggap Waktu.
    """
    line = clean_calendar_line(line)
    matches = list(DATE_RE.finditer(line))

    if not matches:
        return line, None

    # Coba ambil tanggal kuat dari belakang.
    for match in reversed(matches):
        date_text = match.group(0).strip()
        activity_text = (line[:match.start()] + " " + line[match.end():]).strip()
        activity_text = clean_calendar_line(activity_text)

        if has_day_number(date_text):
            return activity_text, date_text

    # Kalau tidak ada tanggal kuat, cek apakah satu baris memang hanya tanggal lemah.
    # Contoh: "Juli - Agustus 2026" atau "Oktober 2025"
    if len(matches) == 1:
        match = matches[0]
        date_text = match.group(0).strip()
        activity_text = (line[:match.start()] + " " + line[match.end():]).strip()
        activity_text = clean_calendar_line(activity_text)

        if not activity_text:
            return "", date_text

    # Kalau masih ada teks kegiatan, jangan pecah tanggalnya.
    # Contoh: "B. Pendaftaran Kelulusan April 2026"
    return line, None


def normalize_calendar_to_markdown_table(page_texts: list[dict]) -> str:
    """
    Mengubah hasil ekstraksi/OCR Kalender Akademik menjadi Markdown Table.

    Perbaikan penting:
    1. Tidak menjadikan 'April 2026' sebagai tanggal final jika itu bagian nama kegiatan.
    2. Menangani kasus layout:
       Proses Registrasi menjadi Mahasiswa Baru
       II. PERKULIAHAN DAN PEMBELAJARAN
       Batas Terakhir Pengajuan Cuti Akademik
       4-11 Februari 2026
       20 Februari 2026

       Tanggal pertama dipasangkan ke kegiatan sebelum section,
       tanggal kedua dipasangkan ke kegiatan setelah section.
    """
    rows = []
    current_section = ""
    current_activity = []
    current_date = None
    current_page = None

    pending_activity_before_section = []
    pending_section_before_section = ""
    pending_page_before_section = None

    def activity_to_text(activity_lines: list[str]) -> str:
        activity = " ".join(activity_lines)
        activity = clean_calendar_line(activity)
        return activity

    def append_row(page, section, activity_lines, date_text):
        activity = activity_to_text(activity_lines)

        if activity and date_text:
            rows.append(
                {
                    "page": page,
                    "section": section,
                    "activity": activity,
                    "date": date_text,
                }
            )

    def flush_row():
        nonlocal current_activity, current_date, current_page

        if current_activity and current_date:
            append_row(
                page=current_page,
                section=current_section,
                activity_lines=current_activity,
                date_text=current_date,
            )

        current_activity = []
        current_date = None

    for page_data in page_texts:
        page_number = page_data["page"]
        text = page_data["text"]

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        for line in lines:
            line = clean_calendar_line(line)

            if not line:
                continue

            if is_calendar_noise_line(line):
                continue

            upper_line = line.upper()

            # Lewati judul besar.
            if (
                "KALENDER AKADEMIK UNIVERSITAS UDAYANA" in upper_line
                or upper_line.startswith("TAHUN AKADEMIK")
                or upper_line == "KEGIATAN AKADEMIK"
            ):
                continue

            is_section = (
                SECTION_RE.match(line)
                or upper_line in [
                    "SEMESTER GASAL (2025-1)",
                    "SEMESTER GENAP (2025-2)",
                    "KEGIATAN AKADEMIK LAINNYA DAN PENJAMINAN MUTU",
                ]
            )

            if is_section:
                # Kalau ada kegiatan sebelum section tapi belum punya tanggal,
                # jangan dibuang. Simpan sebagai pending.
                if current_activity and not current_date:
                    pending_activity_before_section = current_activity.copy()
                    pending_section_before_section = current_section
                    pending_page_before_section = current_page or page_number
                    current_activity = []
                    current_date = None
                else:
                    flush_row()

                current_section = line
                continue

            # Subheading seperti "PENDAFTARAN DAN PENETAPAN KELULUSAN"
            # tidak dimasukkan ke nama kegiatan.
            if is_calendar_subheading(line):
                flush_row()
                continue

            activity_part, date_part = split_activity_and_date(line)

            # ============================================================
            # Kasus baris berisi tanggal
            # ============================================================
            if date_part:
                # Kasus khusus:
                # Ada kegiatan pending sebelum section,
                # lalu setelah section ada kegiatan baru,
                # lalu tanggal pertama muncul.
                #
                # Maka tanggal pertama ini milik kegiatan pending,
                # bukan milik kegiatan baru.
                if (
                    pending_activity_before_section
                    and current_activity
                    and not current_date
                ):
                    append_row(
                        page=pending_page_before_section or page_number,
                        section=pending_section_before_section,
                        activity_lines=pending_activity_before_section,
                        date_text=date_part,
                    )

                    pending_activity_before_section = []
                    pending_section_before_section = ""
                    pending_page_before_section = None

                    # current_activity tetap dipertahankan,
                    # karena akan menerima tanggal berikutnya.
                    continue

                if current_date:
                    flush_row()

                if activity_part:
                    current_activity.append(activity_part)

                current_date = date_part
                current_page = page_number
                continue

            # ============================================================
            # Kasus baris tanpa tanggal
            # ============================================================
            if current_date:
                if is_new_calendar_event_line(line):
                    flush_row()
                    current_activity.append(line)
                    current_page = page_number
                else:
                    current_activity.append(line)
                    flush_row()
            else:
                current_activity.append(line)
                current_page = page_number

    flush_row()

    md = []
    md.append("| Halaman | Bagian | Kegiatan | Waktu |")
    md.append("|---|---|---|---|")

    for row in rows:
        page = row["page"] or ""
        section = row["section"]
        activity = row["activity"]
        date = row["date"]

        md.append(f"| {page} | {section} | {activity} | {date} |")

    return "\n".join(md)

def extract_calendar_to_markdown(
    pdf_path: Path,
    output_path: Path,
    min_total_chars: int = 500,
    use_ocr_if_needed: bool = True,
) -> None:
    """
    Mengekstrak Kalender Akademik ke Markdown.
    Kalender biasanya berupa tabel gambar, sehingga perlu OCR jika teks digital kosong.
    """
    check_file_exists(pdf_path)

    print(f"\n[INFO] Memproses Kalender Akademik: {pdf_path.name}")

    pages = extract_calendar_with_pymupdf(pdf_path)
    total_chars = sum(page["char_count"] for page in pages)

    markdown_parts = []
    markdown_parts.append(f"# Kalender Akademik")
    markdown_parts.append(f"<!-- source: {pdf_path.name} -->")

    # Jika teks digital cukup terbaca, gunakan hasil PyMuPDF
    if total_chars >= min_total_chars:
        print("[INFO] Kalender terbaca sebagai teks digital.")
        print("[INFO] Merekonstruksi Kalender Akademik menjadi Markdown Table...")

        markdown_parts.append("## Tabel Kalender Akademik")
        markdown_parts.append(
            f"<!-- source: {pdf_path.name} | type: reconstructed_table_from_text -->"
        )

        calendar_table = normalize_calendar_to_markdown_table(pages)
        markdown_parts.append(calendar_table)

        write_markdown(output_path, markdown_parts)
        print(f"[INFO] Total karakter Kalender: {total_chars}")
        return

    # Jika teks digital minim, gunakan OCR fallback
    print("[WARNING] Teks Kalender sangat sedikit/kosong.")
    print("[INFO] Kalender kemungkinan berupa gambar atau scan tabel.")

    if not use_ocr_if_needed:
        print("[INFO] OCR fallback dimatikan. File Markdown tetap dibuat dari hasil ekstraksi digital.")
        for page in pages:
            markdown_parts.append(f"## Halaman {page['page']}")
            markdown_parts.append(page["text"] or "_Tidak ada teks yang berhasil diekstrak._")

        write_markdown(output_path, markdown_parts)
        return

    print("[INFO] Mencoba OCR fallback...")

    doc = fitz.open(pdf_path)

    try:
        # Kembali memakai OCR full-page yang lebih stabil untuk dokumen ini.
        # Percobaan layout OCR berbasis koordinat kata membuat hasil tabel menjadi rusak,
        # karena Tesseract tidak konsisten memisahkan kolom kegiatan dan kolom waktu.
        ocr_pages = []

        for page_index, page in enumerate(doc, start=1):
            print(f"[INFO] OCR halaman {page_index}...")

            raw_ocr_text = ocr_page_with_pymupdf(
                page,
                zoom=3,
                return_raw=True,
            )

            save_ocr_debug_files(page_index, raw_ocr_text)

            ocr_text = clean_text(raw_ocr_text)

            ocr_pages.append(
                {
                    "page": page_index,
                    "text": ocr_text,
                    "char_count": len(ocr_text),
                }
            )

        print("[INFO] Merekonstruksi hasil OCR Kalender Akademik menjadi Markdown Table...")

        markdown_parts.append("## Tabel Kalender Akademik")
        markdown_parts.append(
            f"<!-- source: {pdf_path.name} | type: reconstructed_table_from_ocr -->"
        )

        calendar_table = normalize_calendar_to_markdown_table(ocr_pages)
        markdown_parts.append(calendar_table)

    except Exception as e:
        print("\n[ERROR] OCR fallback gagal.")
        print(str(e))
        print(
            "\nSolusi sementara:\n"
            "1. Install pytesseract dan pillow:\n"
            "   pip install pytesseract pillow\n"
            "2. Install aplikasi Tesseract OCR di Windows.\n"
            "3. Jika sudah terinstal tapi tetap error, tambahkan path tesseract.exe ke environment variable PATH.\n"
            "4. Setelah itu, jalankan ulang script ini.\n"
        )

        markdown_parts.append("## Catatan OCR")
        markdown_parts.append(
            "Kalender Akademik kemungkinan berupa PDF gambar/scan, sehingga memerlukan OCR. "
            "Namun OCR belum berhasil dijalankan pada environment saat ini."
        )

    finally:
        doc.close()

    write_markdown(output_path, markdown_parts)


# ============================================================
# MAIN PROGRAM
# ============================================================
def main() -> None:
    print("====================================================")
    print("DATA LOADING - SMART CAMPUS INFORMATION ASSISTANT")
    print("====================================================")
    print(f"Base directory  : {BASE_DIR}")
    print(f"Raw directory   : {RAW_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")

    print("\n[INFO] Mengecek file input...")
    check_file_exists(PEDOMAN_PDF)
    check_file_exists(KALENDER_PDF)

    # 1. Ekstraksi Buku Pedoman Akademik
    extract_pdf_text_and_tables_to_markdown(
        PEDOMAN_PDF,
        OUTPUT_DIR / "pedoman_akademik_ft_2024.md",
    )

    # 2. Ekstraksi Kalender Akademik
    extract_calendar_to_markdown(
        KALENDER_PDF,
        OUTPUT_DIR / "kalender_akademik_2025_2026.md",
        min_total_chars=500,
        use_ocr_if_needed=True,
    )

    print("\n====================================================")
    print("[SELESAI] Semua proses ekstraksi selesai.")
    print("====================================================")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print(f"\n[STOP] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[STOP] Terjadi error tak terduga: {e}")
        sys.exit(1)