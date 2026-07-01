from pathlib import Path
import re
import sys

import pdfplumber
import fitz  # PyMuPDF


# ============================================================
# KONFIGURASI PATH
# ============================================================
# Untuk Jupyter Notebook, gunakan parent dari direktori saat ini
# Notebook berada di: data_extraction/notebooks/
# Jadi BASE_DIR = data_extraction/
# Menggunakan __file__ agar kebal terhadap current working directory terminal
BASE_DIR = Path(__file__).resolve().parent.parent  # Naik satu level dari extract_process ke data_extraction

# Verifikasi
if not (BASE_DIR / "data").exists():
    raise FileNotFoundError(
        f"Folder data tidak ditemukan di {BASE_DIR}.\n"
        f"Pastikan script ini berada di dalam subfolder dari data_extraction/"
    )

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


def ocr_page_with_pymupdf(page, zoom: int = 3, return_raw: bool = False, config: str = "") -> str:
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
        text = pytesseract.image_to_string(image, lang="ind+eng", config=config)
    except Exception:
        text = pytesseract.image_to_string(image, lang="eng", config=config)

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

DAY_SEP = r"(?:\s*[-–]\s*|\s+dan\s+|\s+s/d\s+)"
MONTH_SEP = r"(?:\s*[-–]\s*|\s+dan\s+|\s+s/d\s+|\s+)"

DATE_PATTERN = rf"""
(?:
    \d{{1,2}}{DAY_SEP}\d{{1,2}}\s+{MONTHS}
    (?:\s+dan\s+\d{{1,2}}{DAY_SEP}\d{{1,2}}\s+{MONTHS})?
    \s+\d{{4}}
    |
    \d{{1,2}}\s+{MONTHS}{MONTH_SEP}\d{{1,2}}\s+{MONTHS}\s+\d{{4}}
    |
    \d{{1,2}}\s+{MONTHS}\s+\d{{4}}{MONTH_SEP}\d{{1,2}}\s+{MONTHS}\s+\d{{4}}
    |
    \d{{1,2}}\s+{MONTHS}\s+\d{{4}}{MONTH_SEP}\d{{1,2}}\s+{MONTHS}
    |
    \d{{1,2}}\s+{MONTHS}\s+\d{{4}}
    |
    {MONTHS}{MONTH_SEP}{MONTHS}\s+\d{{4}}
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
    r"Monitor|Pengukuhan|PKKMB|Wisuda|Upacara|Dies|Hari|Penerimaan)\b",
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

    # Correct month OCR typos (case-insensitive whole word match)
    text = re.sub(r"\bJann?a\b", "Januari", text, flags=re.IGNORECASE)
    text = re.sub(r"\bJanaon\b", "Januari", text, flags=re.IGNORECASE)
    text = re.sub(r"\bJanaan\b", "Januari", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPebruari\b", "Februari", text, flags=re.IGNORECASE)

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
    line = line.replace("\ufffd", "-")

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
def reconstruct_missing_end_year(date_text: str) -> str:
    # Pattern matching a range like: 28 Desember 2026 - 8 Januari
    pattern = rf"^(\d{{1,2}})\s+({MONTHS})\s+(\d{{4}})\s*[-–]\s*(\d{{1,2}})\s+({MONTHS})$"
    match = re.match(pattern, date_text, re.IGNORECASE)
    if match:
        start_day = match.group(1)
        start_month = match.group(2)
        start_year = match.group(3)
        end_day = match.group(4)
        end_month = match.group(5)
        
        if start_month.lower() == "desember" and end_month.lower() in ["januari", "februari"]:
            end_year = str(int(start_year) + 1)
        else:
            end_year = start_year
            
        return f"{start_day} {start_month} {start_year} - {end_day} {end_month} {end_year}"
    return date_text

def has_day_number(date_text: str) -> bool:
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

        is_at_end = (line[match.end():].strip() == "")
        if has_day_number(date_text) or is_at_end:
            date_text = reconstruct_missing_end_year(date_text)
            return activity_text, date_text

    # Kalau tidak ada tanggal kuat, cek apakah satu baris memang hanya tanggal lemah.
    # Contoh: "Juli - Agustus 2026" atau "Oktober 2025"
    if len(matches) == 1:
        match = matches[0]
        date_text = match.group(0).strip()
        activity_text = (line[:match.start()] + " " + line[match.end():]).strip()
        activity_text = clean_calendar_line(activity_text)

        if not activity_text:
            date_text = reconstruct_missing_end_year(date_text)
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
    current_semester = ""
    current_activity = []
    current_date = None
    current_page = None

    pending_activity_before_section = []
    pending_section_before_section = ""
    pending_page_before_section = None
    pending_semester_before_section = ""

    def activity_to_text(activity_lines: list[str]) -> str:
        activity = " ".join(activity_lines)
        activity = clean_calendar_line(activity)
        return activity

    def append_row(page, semester, section, activity_lines, date_text):
        nonlocal current_section
        activity = activity_to_text(activity_lines)

        if activity and date_text:
            activity_lower = activity.lower()
            if "kuliah kerja nyata" in activity_lower or "kkn-ppm" in activity_lower:
                section = "VI. KKN-PPM"
                current_section = "VI. KKN-PPM"
            elif "kelulusan" in activity_lower or "yudisium" in activity_lower:
                section = "VII. PENETAPAN KELULUSAN"
                current_section = "VII. PENETAPAN KELULUSAN"
            elif "wisuda ke" in activity_lower:
                section = "VIII. WISUDA"
                current_section = "VIII. WISUDA"
            elif any(k in activity_lower for k in ["audit mutu", "ami", "rapat tinjauan", "rtm", "dies natalis", "monev"]):
                section = "IX. KEGIATAN AKADEMIK LAINNYA"
                current_section = "IX. KEGIATAN AKADEMIK LAINNYA"

            rows.append(
                {
                    "page": page,
                    "semester": semester,
                    "section": section,
                    "activity": activity,
                    "date": date_text,
                }
            )

    def flush_row():
        nonlocal current_activity, current_date, current_page, current_semester, current_section

        if current_activity and current_date:
            append_row(
                page=current_page,
                semester=current_semester,
                section=current_section,
                activity_lines=current_activity,
                date_text=current_date,
            )

        current_activity = []
        current_date = None
    # Compile helper regex for split date lookahead
    SPLIT_DATE_END_RE = re.compile(
        rf"(?:"
        rf"\d{{1,2}}\s+{MONTHS}\s+\d{{4}}\s*[-–]\s*\d{{1,2}}\s+{MONTHS}"
        rf"|"
        rf"\d{{1,2}}\s*[-–]\s*\d{{1,2}}\s+{MONTHS}"
        rf")\s*$",
        re.IGNORECASE
    )

    for page_data in page_texts:
        page_number = page_data["page"]
        text = page_data["text"]

        raw_lines = [line.strip() for line in text.splitlines() if line.strip()]

        # Preprocess lines to merge split date ranges
        lines = []
        skip_next = False
        for idx in range(len(raw_lines)):
            if skip_next:
                skip_next = False
                continue
            curr_line = clean_calendar_line(raw_lines[idx])
            if idx + 1 < len(raw_lines):
                next_line = clean_calendar_line(raw_lines[idx+1])
                if SPLIT_DATE_END_RE.search(curr_line):
                    year_match = re.search(r"\b(\d{4})\b\s*$", next_line)
                    if year_match:
                        year = year_match.group(1)
                        next_line_cleaned = next_line[:year_match.start()] + next_line[year_match.end():]
                        next_line_cleaned = clean_calendar_line(next_line_cleaned)

                        curr_line = curr_line + " " + year
                        lines.append(curr_line)
                        if next_line_cleaned:
                            raw_lines[idx+1] = next_line_cleaned
                        else:
                            skip_next = True
                        continue
            lines.append(curr_line)

        for line in lines:
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
                or "SEMESTER GASAL" in upper_line
                or "SEMESTER GENAP" in upper_line
                or "KEGIATAN AKADEMIK LAINNYA" in upper_line
            )

            if is_section:
                # Kalau ada kegiatan sebelum section tapi belum punya tanggal,
                # jangan dibuang. Simpan sebagai pending.
                if current_activity and not current_date:
                    pending_activity_before_section = current_activity.copy()
                    pending_section_before_section = current_section
                    pending_page_before_section = current_page or page_number
                    pending_semester_before_section = current_semester
                    current_activity = []
                    current_date = None
                else:
                    flush_row()

                # Update current_semester based on section headers
                if "SEMESTER GASAL" in upper_line:
                    current_semester = "gasal"
                elif "SEMESTER GENAP" in upper_line:
                    current_semester = "genap"

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
                        semester=pending_semester_before_section or current_semester,
                        section=pending_section_before_section,
                        activity_lines=pending_activity_before_section,
                        date_text=date_part,
                    )

                    pending_activity_before_section = []
                    pending_section_before_section = ""
                    pending_page_before_section = None
                    pending_semester_before_section = ""

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
    md.append("| Halaman | Semester | Bagian | Kegiatan | Waktu |")
    md.append("|---|---|---|---|---|")

    for row in rows:
        page = row["page"] or ""
        semester = row["semester"] or ""
        section = row["section"]
        activity = row["activity"]
        date = row["date"]

        md.append(f"| {page} | {semester} | {section} | {activity} | {date} |")

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

            # Layout restoration for specific PDF OCR anomalies
            if page_index == 1:
                if "1 - 8 Agustus 2026" in ocr_text and "bagi Mahasiswa Baru)" in ocr_text:
                    ocr_text = ocr_text.replace("1 - 8 Agustus 2026", "")
                    ocr_text = ocr_text.replace("bagi Mahasiswa Baru)", "bagi Mahasiswa Baru) 1 - 8 Agustus 2026")

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


from pathlib import Path
import re
import json
import hashlib
from dataclasses import dataclass
from typing import Any


# ============================================================
# KONFIGURASI PATH
# ============================================================
# Notebook berada di: data_extraction/notebooks/
# Parent folder adalah: data_extraction/
# Data folder berada di: data_extraction/data/

BASE_DIR = Path.cwd().parent  # Naik satu level dari notebooks ke data_extraction

# Verifikasi
if not (BASE_DIR / "data").exists():
    raise FileNotFoundError(
        f"Folder data tidak ditemukan di {BASE_DIR}.\n"
        f"Current working directory: {Path.cwd()}\n"
        f"Pastikan notebook berada di folder: data_extraction/notebooks/"
    )

MARKDOWN_DIR = BASE_DIR / "data" / "processed" / "markdown"
CLEANED_DIR = BASE_DIR / "data" / "processed" / "cleaned"
CHUNKS_DIR = BASE_DIR / "data" / "processed" / "chunks"

CLEANED_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_MARKDOWN_FILES = [
    MARKDOWN_DIR / "pedoman_akademik_ft_2024.md",
    MARKDOWN_DIR / "kalender_akademik_2025_2026.md",
]

OUTPUT_CHUNKS_JSON = CHUNKS_DIR / "chunks.json"

# Ukuran chunk untuk dokumen naratif seperti Pedoman Akademik.
# Kalender Akademik tidak memakai target ini karena satu kegiatan = satu chunk.
TARGET_CHARS = 1000
OVERLAP_CHARS = 150
MIN_CHUNK_CHARS = 120

# Bagian awal Pedoman Akademik berisi lembar pengesahan, sambutan, daftar isi, dsb.
# Bagian isi utama mulai sekitar halaman PDF 25 pada hasil ekstraksi.
PEDOMAN_BODY_START_PAGE = 25

# Opsi jika nanti ingin hanya memasukkan bagian inti tertentu dari Pedoman Akademik.
# Default False agar seluruh isi utama Pedoman tetap dipakai.
ONLY_CORE_PEDOMAN_SECTIONS = False
CORE_PEDOMAN_CHAPTER_PREFIXES = (
    "BAGIAN 3.",
    "BAGIAN 4.",
    "BAGIAN 5.",
    "BAGIAN 10.",
)


# ============================================================
# DATA STRUCTURE
# ============================================================

@dataclass
class TextBlock:
    text: str
    source_file: str
    doc_type: str
    page: int | None
    chapter: str
    section: str
    subsection: str
    block_type: str
    semester: str | None = None  # Track semester dari parent heading (kalender)


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict[str, Any]


# ============================================================
# UTILITAS FILE
# ============================================================

def check_file_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"File tidak ditemukan: {path}\n"
            f"Pastikan file berada di folder: {path.parent}"
        )


def read_text_file(path: Path) -> str:
    check_file_exists(path)
    return path.read_text(encoding="utf-8")


def write_text_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def infer_doc_type(filename: str) -> str:
    name = filename.lower()

    if "kalender" in name:
        return "kalender_akademik"

    if "pedoman" in name:
        return "pedoman_akademik"

    return "dokumen_akademik"


# ============================================================
# CLEANING LANJUTAN UNTUK RAG
# ============================================================

FOOTER_INLINE_RE = re.compile(
    r"\b(?:[ivxlcdm]+|\d+)?\s*"
    r"Pedoman Akademik Program Sarjana Fakultas Teknik Universitas Udayana\s+20(?:22|24)"
    r"\s*(?:[ivxlcdm]+|\d+)?\b",
    re.IGNORECASE,
)

EMPTY_EXTRACTION_RE = re.compile(
    r"^_?Tidak ada teks (yang )?berhasil diekstrak.*_?$",
    re.IGNORECASE,
)

DAFTAR_SECTION_RE = re.compile(
    r"^(DAFTAR ISI|DAFTAR TABEL|DAFTAR GAMBAR)\b",
    re.IGNORECASE,
)


def fix_doubled_char_line(line: str) -> str:
    """
    Memperbaiki kasus PDF yang mengekstrak teks menjadi huruf dobel:
    Contoh: 'PPuujjii ssyyuukkuurr' -> 'Puji syukur'.
    """
    if len(line) < 20:
        return line

    non_space_chars = [char for char in line if not char.isspace()]
    if not non_space_chars:
        return line

    repeated_pairs = 0
    for i in range(len(line) - 1):
        if line[i] == line[i + 1] and not line[i].isspace():
            repeated_pairs += 1

    ratio = repeated_pairs / max(len(non_space_chars), 1)

    if ratio >= 0.25:
        line = re.sub(r"(.)\1", r"\1", line)

    return line


def clean_markdown_line(line: str) -> str:
    """
    Membersihkan noise per baris tanpa merusak struktur Markdown.
    """
    line = fix_doubled_char_line(line)
    line = line.replace("\x00", " ")
    line = re.sub(r"[ \t]+", " ", line)
    line = line.strip()

    if EMPTY_EXTRACTION_RE.match(line):
        return ""

    # Menghapus footer/header yang berdiri sendiri atau menempel pada kalimat.
    line = FOOTER_INLINE_RE.sub(" ", line)
    line = re.sub(r"\s+", " ", line).strip()

    return line


def normalize_blank_lines(lines: list[str]) -> list[str]:
    """
    Menghindari blank line berlebihan.
    """
    normalized = []
    previous_blank = False

    for line in lines:
        is_blank = line.strip() == ""

        if is_blank and previous_blank:
            continue

        normalized.append(line)
        previous_blank = is_blank

    return normalized


def clean_markdown_for_rag(markdown_text: str) -> str:
    """
    Cleaning lanjutan sebelum chunking:
    - memperbaiki huruf dobel hasil ekstraksi PDF,
    - menghapus halaman kosong,
    - menghapus header/footer berulang,
    - menjaga metadata comment, heading, dan Markdown Table.
    """
    cleaned_lines = []

    for raw_line in markdown_text.splitlines():
        line = clean_markdown_line(raw_line)
        cleaned_lines.append(line)

    cleaned_lines = normalize_blank_lines(cleaned_lines)

    cleaned_text = "\n".join(cleaned_lines)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    return cleaned_text.strip()


# ============================================================
# PARSING METADATA DAN STRUKTUR MARKDOWN
# ============================================================

# Metadata comment dibuat oleh data_extraction.py, contohnya:
# <!-- source: Buku Pedoman Akademik Sarjana FT 2024.pdf | page: 49 | type: text -->
SOURCE_META_RE = re.compile(r"^<!--\s*(.*?)\s*-->$", re.IGNORECASE)

PAGE_HEADING_RE = re.compile(r"^#{1,3}\s*Halaman\s+(\d+)", re.IGNORECASE)

# Heading Pedoman Akademik.
CHAPTER_HEADING_RE = re.compile(
    r"^(BAGIAN\s+\d+\.?\s+.+|LAMPIRAN\s+[A-Z]\.?\s+.+)$",
    re.IGNORECASE,
)

SECTION_2_LEVEL_RE = re.compile(
    r"^\d+\.\d+\.?\s+.+$",
    re.IGNORECASE,
)

SECTION_3PLUS_LEVEL_RE = re.compile(
    r"^\d+\.\d+\.\d+(?:\.\d+)*\.?\s+.+$",
    re.IGNORECASE,
)

# Heading Kalender Akademik.
CALENDAR_SECTION_RE = re.compile(
    r"^(SEMESTER\s+.+|[IVXLC]+\.\s+.+|KEGIATAN AKADEMIK LAINNYA.+)$",
    re.IGNORECASE,
)

MARKDOWN_TABLE_RE = re.compile(r"^\|.*\|$")


def strip_markdown_heading(line: str) -> str:
    return re.sub(r"^#+\s*", "", line).strip()


def remove_toc_dots(line: str) -> str:
    """
    Menghapus pola titik-titik daftar isi pada heading.
    Contoh:
    '4.2 Cuti Akademik ................................ 49' -> '4.2 Cuti Akademik'
    """
    line = re.sub(r"\.{5,}\s*\d+\s*$", "", line).strip()
    return line


def normalize_calendar_section(section: str) -> str:
    section = section.strip()
    section = section.replace("ll.", "II.")
    section = section.replace("lll.", "III.")
    section = section.replace("Il.", "II.")
    section = re.sub(r"\s+", " ", section)
    return section.strip()


def classify_heading(line: str, doc_type: str) -> str | None:
    """
    Mengklasifikasikan heading menjadi chapter, section, atau subsection.
    """
    text = remove_toc_dots(strip_markdown_heading(line))

    if not text:
        return None

    if doc_type == "kalender_akademik":
        normalized = normalize_calendar_section(text)

        if normalized.lower().startswith("kalender akademik"):
            return "chapter"

        if normalized.lower().startswith("tabel kalender akademik"):
            return "chapter"

        if CALENDAR_SECTION_RE.match(normalized):
            return "section"

        return None

    if CHAPTER_HEADING_RE.match(text):
        return "chapter"

    if SECTION_3PLUS_LEVEL_RE.match(text):
        return "subsection"

    if SECTION_2_LEVEL_RE.match(text):
        return "section"

    return None


def extract_metadata_from_comment(line: str) -> dict[str, Any] | None:
    """
    Membaca metadata dari komentar HTML.
    Parsing dilakukan dengan split "|" agar source_file tidak terpotong.
    """
    match = SOURCE_META_RE.match(line.strip())

    if not match:
        return None

    content = match.group(1).strip()
    parts = [part.strip() for part in content.split("|") if part.strip()]

    metadata: dict[str, str] = {}

    for part in parts:
        if ":" not in part:
            continue

        key, value = part.split(":", 1)
        metadata[key.strip().lower()] = value.strip()

    source = metadata.get("source", "")
    page = metadata.get("page")
    meta_type = metadata.get("type", "")

    return {
        "source_file": source,
        "page": int(page) if page and page.isdigit() else None,
        "source_type": meta_type,
    }


def is_metadata_comment(line: str) -> bool:
    return line.strip().startswith("<!--") and line.strip().endswith("-->")


def is_page_heading(line: str) -> bool:
    return PAGE_HEADING_RE.match(line.strip()) is not None


def get_page_from_heading(line: str) -> int | None:
    match = PAGE_HEADING_RE.match(line.strip())

    if not match:
        return None

    return int(match.group(1))


def is_section_heading(line: str, doc_type: str) -> bool:
    return classify_heading(line, doc_type) is not None


def is_markdown_table_line(line: str) -> bool:
    return MARKDOWN_TABLE_RE.match(line.strip()) is not None


def is_pedoman_front_matter(doc_type: str, page: int | None) -> bool:
    """
    Mengecek apakah sebuah konten Pedoman masih berada di bagian awal dokumen.
    """
    return doc_type == "pedoman_akademik" and page is not None and page < PEDOMAN_BODY_START_PAGE


def is_excluded_pedoman_line(
    line: str,
    doc_type: str,
    page: int | None,
    current_chapter: str,
) -> bool:
    """
    Menentukan apakah baris/blok Pedoman perlu dikeluarkan dari retrieval.
    """
    if doc_type != "pedoman_akademik":
        return False

    text = strip_markdown_heading(line).strip()

    # Buang front matter: lembar pengesahan, sambutan, tim penyusun, daftar isi, dsb.
    if is_pedoman_front_matter(doc_type, page):
        return True

    # Buang daftar isi/tabel/gambar jika masih muncul.
    if DAFTAR_SECTION_RE.match(text):
        return True

    if DAFTAR_SECTION_RE.match(current_chapter):
        return True

    # Opsional: hanya pakai bagian inti tertentu.
    if ONLY_CORE_PEDOMAN_SECTIONS:
        if current_chapter and not current_chapter.startswith(CORE_PEDOMAN_CHAPTER_PREFIXES):
            return True

    return False


# ============================================================
# UTILITAS TABEL KALENDER
# ============================================================

def split_markdown_table_row(row: str) -> list[str]:
    """
    Memecah satu baris Markdown table menjadi list cell sederhana.
    """
    row = row.strip().strip("|")
    return [cell.strip() for cell in row.split("|")]


def is_table_separator_row(row: str) -> bool:
    """
    Mengecek baris separator Markdown table, misalnya:
    |---|---|---|
    """
    cells = split_markdown_table_row(row)

    if not cells:
        return False

    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def extract_semester_from_section(section: str) -> str | None:
    """
    Ekstrak semester dari section text.
    Contoh: "I. SEMESTER GASAL (2025-1)" -> "gasal"
    """
    section_lower = section.lower()
    
    if "semester gasal" in section_lower or "gasal" in section_lower:
        return "gasal"
    elif "semester genap" in section_lower or "genap" in section_lower:
        return "genap"
    
    return None


def enrich_activity(activity: str) -> str:
    """
    Enrichment untuk activity field saja.
    Tambahkan keyword penting jika aktivitas terkait pembayaran + biaya pendidikan.
    Contoh: "Pembayaran Biaya Pendidikan Mahasiswa Lama" -> "Pembayaran Biaya Pendidikan Mahasiswa Lama (Pembayaran UKT)"
    """
    if not activity:
        return activity
    
    activity_lower = activity.lower()
    
    # Jika aktivitas bernama pembayaran biaya pendidikan tapi belum ada "UKT"
    if "pembayaran" in activity_lower and "biaya pendidikan" in activity_lower:
        if "ukt" not in activity_lower:
            return activity + " (Pembayaran UKT)"
    
    return activity


def calendar_table_to_blocks(
    table_text: str,
    source_file: str,
    fallback_page: int | None,
    fallback_chapter: str,
    fallback_section: str,
    current_semester: str | None = None,
) -> list[TextBlock]:
    """
    Khusus kalender akademik:
    tabel tidak disimpan sebagai satu blok besar, tetapi dipecah per baris kegiatan.
    
    Parameter current_semester: semester yang diekstrak dari heading parent (SEMESTER GASAL/GENAP)
    """
    rows = [row.strip() for row in table_text.splitlines() if row.strip()]
    if len(rows) < 3:
        return []

    header_cells = [cell.lower() for cell in split_markdown_table_row(rows[0])]

    required_columns = ["halaman", "semester", "bagian", "kegiatan", "waktu"]
    if not all(column in header_cells for column in required_columns):
        # Fallback to check if it's the old 4-column format
        old_columns = ["halaman", "bagian", "kegiatan", "waktu"]
        if all(column in header_cells for column in old_columns):
            index_map = {name: header_cells.index(name) for name in old_columns}
            blocks: list[TextBlock] = []
            last_semester = current_semester
            for row in rows[2:]:
                if is_table_separator_row(row):
                    continue
                cells = split_markdown_table_row(row)
                if len(cells) < len(header_cells):
                    cells = cells + [""] * (len(header_cells) - len(cells))
                page_text = cells[index_map["halaman"]].strip()
                section = cells[index_map["bagian"]].strip() or fallback_section
                activity = cells[index_map["kegiatan"]].strip()
                date_text = cells[index_map["waktu"]].strip()
                section = normalize_calendar_section(section)
                row_semester = current_semester or extract_semester_from_section(section)
                if row_semester:
                    last_semester = row_semester
                if not activity and not date_text:
                    continue
                page = int(page_text) if page_text.isdigit() else fallback_page
                enriched_activity = enrich_activity(activity)
                semester_str = f"Semester: {last_semester}\n" if last_semester else ""
                text = (
                    f"{semester_str}"
                    f"Bagian: {section}\n"
                    f"Kegiatan: {enriched_activity}\n"
                    f"Waktu: {date_text}"
                ).strip()
                block = make_block(
                    text=text,
                    source_file=source_file,
                    page=page,
                    chapter=fallback_chapter or "Kalender Akademik",
                    section=section,
                    subsection="",
                    block_type="calendar_row",
                )
                if block:
                    block.semester = last_semester
                    blocks.append(block)
            return blocks
        return []

    index_map = {name: header_cells.index(name) for name in required_columns}
    blocks: list[TextBlock] = []

    # Tracker untuk baris yang semesternya tidak terbaca/terpotong
    last_semester = current_semester

    for row in rows[2:]:
        if is_table_separator_row(row):
            continue

        cells = split_markdown_table_row(row)

        if len(cells) < len(header_cells):
            cells = cells + [""] * (len(header_cells) - len(cells))

        page_text = cells[index_map["halaman"]].strip()
        semester_text = cells[index_map["semester"]].strip()
        section = cells[index_map["bagian"]].strip() or fallback_section
        activity = cells[index_map["kegiatan"]].strip()
        date_text = cells[index_map["waktu"]].strip()

        section = normalize_calendar_section(section)

        # Update last_semester jika ada yang baru
        row_semester = semester_text or current_semester or extract_semester_from_section(section)
        if row_semester:
            last_semester = row_semester

        if not activity and not date_text:
            continue

        page = int(page_text) if page_text.isdigit() else fallback_page

        # Enrichment ke activity saja, SEBELUM formatting
        enriched_activity = enrich_activity(activity)
        
        semester_str = f"Semester: {last_semester}\n" if last_semester else ""
        text = (
            f"{semester_str}"
            f"Bagian: {section}\n"
            f"Kegiatan: {enriched_activity}\n"
            f"Waktu: {date_text}"
        ).strip()

        block = make_block(
            text=text,
            source_file=source_file,
            page=page,
            chapter=fallback_chapter or "Kalender Akademik",
            section=section,
            subsection="",
            block_type="calendar_row",
        )

        # Attach semester dari parameter (pass dari parent heading), fallback ke section
        if block:
            block.semester = last_semester

        if block:
            blocks.append(block)

    return blocks


# ============================================================
# PARSING MARKDOWN KE BLOK
# ============================================================

def normalize_paragraph_lines(lines: list[str]) -> str:
    """
    Menggabungkan baris paragraf yang terpotong karena wrapping PDF.
    """
    text = " ".join(line.strip() for line in lines if line.strip())
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def make_block(
    text: str,
    source_file: str,
    page: int | None,
    chapter: str,
    section: str,
    subsection: str,
    block_type: str,
) -> TextBlock | None:
    text = text.strip()

    if not text:
        return None

    return TextBlock(
        text=text,
        source_file=source_file,
        doc_type=infer_doc_type(source_file),
        page=page,
        chapter=chapter.strip(),
        section=section.strip(),
        subsection=subsection.strip(),
        block_type=block_type,
    )


def parse_markdown_to_blocks(markdown_text: str, fallback_source_file: str) -> list[TextBlock]:
    """
    Mengubah Markdown bersih menjadi blok-blok logis:
    - heading
    - paragraph
    - table

    Untuk Pedoman:
    - front matter dibuang,
    - daftar isi/tabel/gambar dibuang,
    - metadata chapter/section/subsection dipertahankan.

    Untuk Kalender:
    - tabel kalender dipecah menjadi satu kegiatan = satu block.
    - semester di-track dari heading parent untuk diattach ke setiap block.
    """
    blocks: list[TextBlock] = []

    current_source = fallback_source_file
    current_page: int | None = None
    current_chapter = ""
    current_section = ""
    current_subsection = ""
    current_semester: str | None = None  # Track semester untuk kalender
    paragraph_buffer: list[str] = []
    table_buffer: list[str] = []

    def current_doc_type() -> str:
        return infer_doc_type(current_source)

    def should_skip_current_content(line: str = "") -> bool:
        return is_excluded_pedoman_line(
            line=line,
            doc_type=current_doc_type(),
            page=current_page,
            current_chapter=current_chapter,
        )

    def flush_paragraph():
        nonlocal paragraph_buffer

        if not paragraph_buffer:
            return

        paragraph = normalize_paragraph_lines(paragraph_buffer)

        if should_skip_current_content(paragraph):
            paragraph_buffer = []
            return

        block = make_block(
            text=paragraph,
            source_file=current_source,
            page=current_page,
            chapter=current_chapter,
            section=current_section,
            subsection=current_subsection,
            block_type="paragraph",
        )

        if block:
            blocks.append(block)

        paragraph_buffer = []

    def flush_table():
        nonlocal table_buffer

        if not table_buffer:
            return

        table_text = "\n".join(table_buffer).strip()

        if should_skip_current_content(table_text):
            table_buffer = []
            return

        # Khusus Kalender Akademik, tabel dipecah per baris kegiatan.
        if infer_doc_type(current_source) == "kalender_akademik":
            calendar_blocks = calendar_table_to_blocks(
                table_text=table_text,
                source_file=current_source,
                fallback_page=current_page,
                fallback_chapter=current_chapter,
                fallback_section=current_section,
                current_semester=current_semester,  # Pass semester dari parent heading
            )

            if calendar_blocks:
                blocks.extend(calendar_blocks)
                table_buffer = []
                return

        block = make_block(
            text=table_text,
            source_file=current_source,
            page=current_page,
            chapter=current_chapter,
            section=current_section,
            subsection=current_subsection,
            block_type="table",
        )

        if block:
            blocks.append(block)

        table_buffer = []

    lines = markdown_text.splitlines()

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            flush_table()
            flush_paragraph()
            continue

        # Ambil metadata dari comment, tetapi jangan masukkan comment ke content chunk.
        if is_metadata_comment(line):
            meta = extract_metadata_from_comment(line)

            if meta:
                if meta["source_file"]:
                    current_source = meta["source_file"]

                if meta["page"] is not None:
                    current_page = meta["page"]

            continue

        # Heading halaman tidak perlu masuk ke content chunk, tetapi page-nya tetap dicatat.
        if is_page_heading(line):
            page_from_heading = get_page_from_heading(line)

            if page_from_heading is not None:
                current_page = page_from_heading

            flush_table()
            flush_paragraph()
            continue

        # Tabel Markdown harus dijaga sebagai satu blok.
        if is_markdown_table_line(line):
            flush_paragraph()
            table_buffer.append(line)
            continue

        # Kalau keluar dari tabel, flush dulu.
        if table_buffer:
            flush_table()

        doc_type = current_doc_type()
        heading_type = classify_heading(line, doc_type)

        if heading_type:
            flush_paragraph()

            heading_text = remove_toc_dots(strip_markdown_heading(line))

            if doc_type == "kalender_akademik":
                heading_text = normalize_calendar_section(heading_text)

            if should_skip_current_content(heading_text):
                continue

            if heading_type == "chapter":
                current_chapter = heading_text
                current_section = ""
                current_subsection = ""
                # Track semester jika chapter adalah "SEMESTER GASAL/GENAP"
                current_semester = extract_semester_from_section(heading_text)
            elif heading_type == "section":
                current_section = heading_text
                current_subsection = ""
                # Juga track semester jika section sendiri merupakan SEMESTER GASAL/GENAP
                semester_candidate = extract_semester_from_section(heading_text)
                if semester_candidate:
                    current_semester = semester_candidate
            elif heading_type == "subsection":
                current_subsection = heading_text

            block = make_block(
                text=heading_text,
                source_file=current_source,
                page=current_page,
                chapter=current_chapter,
                section=current_section,
                subsection=current_subsection,
                block_type="heading",
            )

            if block:
                blocks.append(block)

            continue

        if should_skip_current_content(line):
            continue

        paragraph_buffer.append(line)

    flush_table()
    flush_paragraph()

    return blocks


# ============================================================
# CHUNKING
# ============================================================

def split_long_text(text: str, target_chars: int, overlap_chars: int) -> list[str]:
    """
    Memecah teks yang terlalu panjang.
    Prioritas pemotongan:
    1. baris tabel,
    2. antar kalimat,
    3. fallback berdasarkan karakter.
    """
    text = text.strip()

    if len(text) <= target_chars:
        return [text]

    # Jika teks berupa tabel panjang, potong per baris tabel agar struktur tidak terlalu rusak.
    if "\n|" in text or text.startswith("|"):
        lines = text.splitlines()
        chunks = []
        current_lines = []
        current_len = 0

        for line in lines:
            line_len = len(line) + 1

            if current_lines and current_len + line_len > target_chars:
                chunks.append("\n".join(current_lines).strip())
                current_lines = []
                current_len = 0

            current_lines.append(line)
            current_len += line_len

        if current_lines:
            chunks.append("\n".join(current_lines).strip())

        return [chunk for chunk in chunks if chunk]

    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        if len(current) + len(sentence) + 1 <= target_chars:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)

            if len(sentence) > target_chars:
                start = 0
                step = max(target_chars - overlap_chars, 1)

                while start < len(sentence):
                    end = start + target_chars
                    part = sentence[start:end].strip()

                    if part:
                        chunks.append(part)

                    start += step

                current = ""
            else:
                current = sentence

    if current:
        chunks.append(current)

    if overlap_chars > 0 and len(chunks) > 1:
        overlapped = []

        for index, chunk in enumerate(chunks):
            if index == 0:
                overlapped.append(chunk)
                continue

            previous_tail = chunks[index - 1][-overlap_chars:]
            combined = f"{previous_tail}\n\n{chunk}".strip()
            overlapped.append(combined)

        return overlapped

    return chunks


def expand_oversized_blocks(blocks: list[TextBlock]) -> list[TextBlock]:
    """
    Jika ada satu blok yang lebih panjang dari TARGET_CHARS,
    pecah menjadi beberapa blok kecil agar chunking lebih stabil.
    """
    expanded: list[TextBlock] = []

    for block in blocks:
        if len(block.text) <= TARGET_CHARS:
            expanded.append(block)
            continue

        parts = split_long_text(block.text, TARGET_CHARS, OVERLAP_CHARS)

        for index, part in enumerate(parts, start=1):
            expanded.append(
                TextBlock(
                    text=part,
                    source_file=block.source_file,
                    doc_type=block.doc_type,
                    page=block.page,
                    chapter=block.chapter,
                    section=block.section,
                    subsection=block.subsection,
                    block_type=f"{block.block_type}_part_{index}",
                    semester=block.semester,
                )
            )

    return expanded


def get_overlap_blocks(blocks: list[TextBlock], overlap_chars: int) -> list[TextBlock]:
    """
    Mengambil potongan akhir teks sebagai overlap untuk chunk berikutnya.
    """
    if overlap_chars <= 0 or not blocks:
        return []

    tail_parts = []
    total = 0

    for block in reversed(blocks):
        if total >= overlap_chars:
            break

        needed = overlap_chars - total
        text_tail = block.text[-needed:]
        tail_parts.insert(0, text_tail)
        total += len(text_tail)

    overlap_text = " ".join(tail_parts)
    overlap_text = re.sub(r"\s+", " ", overlap_text).strip()

    if not overlap_text:
        return []

    last = blocks[-1]

    return [
        TextBlock(
            text=overlap_text,
            source_file=last.source_file,
            doc_type=last.doc_type,
            page=last.page,
            chapter=last.chapter,
            section=last.section,
            subsection=last.subsection,
            block_type="overlap",
            semester=last.semester,
        )
    ]


def format_pages(pages: list[int]) -> str:
    if not pages:
        return ""

    unique_pages = sorted(set(pages))

    if len(unique_pages) == 1:
        return str(unique_pages[0])

    return f"{unique_pages[0]}-{unique_pages[-1]}"


def create_chunk_id(source_file: str, chunk_index: int, text: str) -> str:
    source_stem = Path(source_file).stem.lower()
    source_stem = re.sub(r"[^a-z0-9]+", "_", source_stem).strip("_")

    digest = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]

    return f"{source_stem}_{chunk_index:04d}_{digest}"


def build_section_path(chapter: str, section: str, subsection: str) -> str:
    parts = [part for part in [chapter, section, subsection] if part]
    return " > ".join(parts)


def build_chunk_from_blocks(blocks: list[TextBlock], chunk_index: int) -> Chunk | None:
    if not blocks:
        return None

    text_parts = []

    for block in blocks:
        if block.block_type == "heading":
            text_parts.append(f"## {block.text}")
        else:
            text_parts.append(block.text)

    text = "\n\n".join(text_parts).strip()

    if len(text) < MIN_CHUNK_CHARS:
        has_table = any(block.block_type.startswith("table") for block in blocks)
        has_calendar_row = any(block.block_type == "calendar_row" for block in blocks)

        if not has_table and not has_calendar_row:
            return None

    pages = [block.page for block in blocks if block.page is not None]
    source_file = blocks[0].source_file
    doc_type = blocks[0].doc_type

    chapter_candidates = [block.chapter for block in blocks if block.chapter]
    section_candidates = [block.section for block in blocks if block.section]
    subsection_candidates = [block.subsection for block in blocks if block.subsection]
    semester_candidates = [block.semester for block in blocks if block.semester]

    chapter = chapter_candidates[-1] if chapter_candidates else ""
    section = section_candidates[-1] if section_candidates else ""
    subsection = subsection_candidates[-1] if subsection_candidates else ""
    semester = semester_candidates[-1] if semester_candidates else None

    current_heading = subsection or section or chapter
    section_path = build_section_path(chapter, section, subsection)

    chunk_id = create_chunk_id(source_file, chunk_index, text)

    metadata = {
        "source_file": source_file,
        "doc_type": doc_type,
        "page_start": min(pages) if pages else None,
        "page_end": max(pages) if pages else None,
        "pages": format_pages(pages),
        "chapter": chapter,
        "section": section,
        "subsection": subsection,
        "current_heading": current_heading,
        "section_path": section_path,
        "semester": semester,
        "chunk_index": chunk_index,
        "char_count": len(text),
    }

    return Chunk(
        id=chunk_id,
        text=text,
        metadata=metadata,
    )


def chunk_blocks(
    blocks: list[TextBlock],
    target_chars: int = TARGET_CHARS,
    overlap_chars: int = OVERLAP_CHARS,
) -> list[Chunk]:
    """
    Menggabungkan blok teks menjadi chunk.

    Khusus Kalender Akademik:
    - satu calendar_row = satu chunk,
    - tidak memakai overlap,
    - tidak digabung dengan kegiatan lain.

    Untuk Pedoman Akademik:
    - memakai target_chars dan overlap_chars,
    - overlap berupa potongan teks pendek, bukan block utuh.
    """
    blocks = expand_oversized_blocks(blocks)

    chunks: list[Chunk] = []
    buffer: list[TextBlock] = []
    buffer_chars = 0
    chunk_index = 1

    def flush_buffer():
        nonlocal buffer, buffer_chars, chunk_index

        if not buffer:
            return

        chunk = build_chunk_from_blocks(buffer, chunk_index)

        if chunk:
            chunks.append(chunk)
            chunk_index += 1

        buffer = []
        buffer_chars = 0

    for block in blocks:
        # ====================================================
        # KHUSUS KALENDER AKADEMIK
        # Satu baris kegiatan kalender langsung menjadi satu chunk.
        # ====================================================
        if block.doc_type == "kalender_akademik" and block.block_type == "calendar_row":
            flush_buffer()

            chunk = build_chunk_from_blocks([block], chunk_index)

            if chunk:
                chunks.append(chunk)
                chunk_index += 1

            continue

        block_len = len(block.text)

        # Jangan gabungkan dokumen berbeda dalam satu chunk.
        if buffer and block.source_file != buffer[0].source_file:
            flush_buffer()

        # Jika buffer sudah penuh, flush dulu.
        if buffer and buffer_chars + block_len > target_chars:
            chunk = build_chunk_from_blocks(buffer, chunk_index)

            if chunk:
                chunks.append(chunk)
                chunk_index += 1

            overlap_blocks = get_overlap_blocks(buffer, overlap_chars)
            buffer = overlap_blocks.copy()
            buffer_chars = sum(len(item.text) for item in buffer)

        buffer.append(block)
        buffer_chars += block_len

    flush_buffer()

    return chunks


# ============================================================
# PIPELINE UTAMA
# ============================================================

def process_markdown_file(markdown_path: Path) -> tuple[list[TextBlock], Path]:
    print(f"\n[INFO] Memproses Markdown: {markdown_path.name}")

    raw_markdown = read_text_file(markdown_path)
    cleaned_markdown = clean_markdown_for_rag(raw_markdown)

    cleaned_output_path = CLEANED_DIR / markdown_path.name
    write_text_file(cleaned_output_path, cleaned_markdown)

    blocks = parse_markdown_to_blocks(
        markdown_text=cleaned_markdown,
        fallback_source_file=markdown_path.name,
    )

    print(f"[INFO] File cleaned dibuat: {cleaned_output_path}")
    print(f"[INFO] Total blok terdeteksi: {len(blocks)}")

    return blocks, cleaned_output_path


def save_chunks(chunks: list[Chunk], output_path: Path) -> None:
    data = [
        {
            "id": chunk.id,
            "text": chunk.text,
            "metadata": chunk.metadata,
        }
        for chunk in chunks
    ]

    write_json_file(output_path, data)


def print_chunk_preview(chunks: list[Chunk], max_preview: int = 3) -> None:
    print("\n[INFO] Preview chunk:")

    for chunk in chunks[:max_preview]:
        print("=" * 80)
        print(f"ID      : {chunk.id}")
        print(f"Source  : {chunk.metadata['source_file']}")
        print(f"Doc Type: {chunk.metadata['doc_type']}")
        print(f"Pages   : {chunk.metadata['pages']}")
        print(f"Chapter : {chunk.metadata['chapter']}")
        print(f"Section : {chunk.metadata['section']}")
        print(f"Subsec. : {chunk.metadata['subsection']}")
        print(f"Semester: {chunk.metadata['semester']}")
        print(f"Chars   : {chunk.metadata['char_count']}")
        print("-" * 80)
        print(chunk.text[:700])
        print()


def print_summary(chunks: list[Chunk]) -> None:
    by_doc: dict[str, int] = {}
    too_long: list[Chunk] = []

    for chunk in chunks:
        doc_type = chunk.metadata["doc_type"]
        by_doc[doc_type] = by_doc.get(doc_type, 0) + 1

        # Batas longgar untuk menandai chunk yang masih terlalu panjang.
        if chunk.metadata["char_count"] > TARGET_CHARS + OVERLAP_CHARS + 100:
            too_long.append(chunk)

    print("\n[INFO] Ringkasan chunk per dokumen:")
    for doc_type, total in by_doc.items():
        print(f"- {doc_type}: {total} chunk")

    print(f"[INFO] Chunk yang masih sangat panjang: {len(too_long)}")

    if too_long:
        print("[INFO] Contoh chunk panjang:")
        for chunk in too_long[:5]:
            print(
                f"- {chunk.id} | {chunk.metadata['doc_type']} | "
                f"pages {chunk.metadata['pages']} | chars {chunk.metadata['char_count']}"
            )


def main() -> None:
    print("====================================================")
    print("PREPROCESSING & CHUNKING - SMART CAMPUS ASSISTANT")
    print("====================================================")
    print(f"Base directory    : {BASE_DIR}")
    print(f"Markdown directory: {MARKDOWN_DIR}")
    print(f"Cleaned directory : {CLEANED_DIR}")
    print(f"Chunks directory  : {CHUNKS_DIR}")

    all_blocks: list[TextBlock] = []

    for markdown_path in INPUT_MARKDOWN_FILES:
        check_file_exists(markdown_path)
        blocks, _ = process_markdown_file(markdown_path)
        all_blocks.extend(blocks)

    print("\n[INFO] Melakukan chunking...")
    chunks = chunk_blocks(
        blocks=all_blocks,
        target_chars=TARGET_CHARS,
        overlap_chars=OVERLAP_CHARS,
    )

    save_chunks(chunks, OUTPUT_CHUNKS_JSON)

    print(f"[INFO] Total semua blok : {len(all_blocks)}")
    print(f"[INFO] Total chunk      : {len(chunks)}")
    print(f"[INFO] Output chunks    : {OUTPUT_CHUNKS_JSON}")

    print_summary(chunks)
    print_chunk_preview(chunks)

    print("\n====================================================")
    print("[SELESAI] Cleaning lanjutan dan chunking selesai.")
    print("====================================================")


if __name__ == "__main__":
    main()