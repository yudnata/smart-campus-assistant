import re
import hashlib
import json
import fitz
import pdfplumber
from pathlib import Path
from dataclasses import dataclass
from typing import Any, List, Dict, Tuple

# ============================================================
# CONFIGURATION CONSTANTS
# ============================================================
TARGET_CHARS = 1000
OVERLAP_CHARS = 150
MIN_CHUNK_CHARS = 120
PEDOMAN_BODY_START_PAGE = 25
ONLY_CORE_PEDOMAN_SECTIONS = False
CORE_PEDOMAN_CHAPTER_PREFIXES = ("BAGIAN 3.", "BAGIAN 4.", "BAGIAN 5.", "BAGIAN 10.")

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

CALENDAR_SECTION_RE = re.compile(
    r"^(SEMESTER\s+.+|[IVXLC]+\.\s+.+|KEGIATAN AKADEMIK LAINNYA.+)$",
    re.IGNORECASE,
)

MARKDOWN_TABLE_RE = re.compile(r"^\|.*\|$")

SOURCE_META_RE = re.compile(r"^<!--\s*(.*?)\s*-->$", re.IGNORECASE)
PAGE_HEADING_RE = re.compile(r"^#{1,3}\s*Halaman\s+(\d+)", re.IGNORECASE)

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

# ============================================================
# DATA STRUCTURES
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
    semester: str | None = None

@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict

# ============================================================
# TEXT CLEANING & NORMALIZATION FUNCTIONS
# ============================================================

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\x00", " ")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def normalize_pedoman_text(text: str) -> str:
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
            or re.match(r"^\d+(\.\d+)*\s+", line)
            or re.match(r"^[A-Z]\.\s+", line)
            or re.match(r"^\d+\.\s+", line)
            or re.match(r"^[a-z]\)\s+", line)
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
    if cell is None:
        return ""
    cell = str(cell)
    cell = cell.replace("\n", " ")
    cell = cell.replace("|", "\\|")
    cell = re.sub(r"\s+", " ", cell)
    return cell.strip()

def table_to_markdown(table) -> str:
    if not table:
        return ""
    cleaned_rows = []
    for row in table:
        if not row:
            continue
        cleaned_row = [clean_markdown_cell(cell) for cell in row]
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

def fix_doubled_char_line(line: str) -> str:
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
    line = fix_doubled_char_line(line)
    line = line.replace("\x00", " ")
    line = re.sub(r"[ \t]+", " ", line)
    line = line.strip()
    if EMPTY_EXTRACTION_RE.match(line):
        return ""
    line = FOOTER_INLINE_RE.sub(" ", line)
    return re.sub(r"\s+", " ", line).strip()

def normalize_blank_lines(lines: List[str]) -> List[str]:
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
    cleaned_lines = []
    for raw_line in markdown_text.splitlines():
        line = clean_markdown_line(raw_line)
        cleaned_lines.append(line)
    cleaned_lines = normalize_blank_lines(cleaned_lines)
    cleaned_text = "\n".join(cleaned_lines)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
    return cleaned_text.strip()

# ============================================================
# METADATA & PARSING UTILITIES
# ============================================================

def strip_markdown_heading(line: str) -> str:
    return re.sub(r"^#+\s*", "", line).strip()

def remove_toc_dots(line: str) -> str:
    return re.sub(r"\.{5,}\s*\d+\s*$", "", line).strip()

def normalize_calendar_section(section: str) -> str:
    section = section.strip()
    section = section.replace("ll.", "II.")
    section = section.replace("lll.", "III.")
    section = section.replace("Il.", "II.")
    section = re.sub(r"\s+", " ", section)
    return section.strip()

def classify_heading(line: str, doc_type: str) -> str | None:
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

def extract_metadata_from_comment(line: str) -> dict | None:
    match = SOURCE_META_RE.match(line.strip())
    if not match:
        return None
    content = match.group(1).strip()
    parts = [part.strip() for part in content.split("|") if part.strip()]
    metadata = {}
    for part in parts:
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        metadata[key.strip().lower()] = value.strip()
    return {
        "source_file": metadata.get("source", ""),
        "page": int(metadata["page"]) if metadata.get("page") and metadata["page"].isdigit() else None,
        "source_type": metadata.get("type", ""),
    }

def is_metadata_comment(line: str) -> bool:
    return line.strip().startswith("<!--") and line.strip().endswith("-->")

def is_page_heading(line: str) -> bool:
    return PAGE_HEADING_RE.match(line.strip()) is not None

def get_page_from_heading(line: str) -> int | None:
    match = PAGE_HEADING_RE.match(line.strip())
    return int(match.group(1)) if match else None

def is_markdown_table_line(line: str) -> bool:
    return MARKDOWN_TABLE_RE.match(line.strip()) is not None

def is_pedoman_front_matter(doc_type: str, page: int | None, total_pages: int = 100) -> bool:
    if total_pages < PEDOMAN_BODY_START_PAGE:
        return False
    return doc_type == "pedoman_akademik" and page is not None and page < PEDOMAN_BODY_START_PAGE

def is_excluded_pedoman_line(
    line: str,
    doc_type: str,
    page: int | None,
    current_chapter: str,
    total_pages: int = 100
) -> bool:
    if doc_type != "pedoman_akademik":
        return False
    text = strip_markdown_heading(line).strip()
    if is_pedoman_front_matter(doc_type, page, total_pages):
        return True
    if DAFTAR_SECTION_RE.match(text):
        return True
    if DAFTAR_SECTION_RE.match(current_chapter):
        return True
    if ONLY_CORE_PEDOMAN_SECTIONS:
        if current_chapter and not current_chapter.startswith(CORE_PEDOMAN_CHAPTER_PREFIXES):
            return True
    return False

# ============================================================
# CALENDAR PARSING UTILITIES
# ============================================================

def remove_event_prefix(line: str) -> str:
    line = clean_calendar_line(line)
    line = re.sub(r"^\d+\s*[|.)]\s*", "", line).strip()
    line = re.sub(r"^[A-Z][\.,]\s*", "", line).strip()
    line = re.sub(r"^[a-z]\)\s*", "", line).strip()
    return line

def is_calendar_subheading(line: str) -> bool:
    line = remove_event_prefix(line)
    return SUBHEADING_RE.match(line) is not None

def is_new_calendar_event_line(line: str) -> bool:
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
    if not line:
        return ""
    line = line.replace("—", "-")
    line = line.replace("–", "-")
    line = line.replace("~", "-")
    line = line.replace("\ufffd", "-")
    line = re.sub(r"^\s*\d+\s*[|.)]\s*", "", line)
    line = line.replace("|", " ")
    line = re.sub(r"^[,]\s*", "", line)
    line = re.sub(r"\s+", " ", line)
    return normalize_ocr_noise(line)

def is_calendar_noise_line(line: str) -> bool:
    if not line:
        return True
    lowered = line.lower().strip()
    known_noise_patterns = ["nio wa", "elniau", "w)r", "wa) w"]
    if any(pattern in lowered for pattern in known_noise_patterns):
        return True
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
    line = clean_calendar_line(line)
    matches = list(DATE_RE.finditer(line))
    if not matches:
        return line, None
    for match in reversed(matches):
        date_text = match.group(0).strip()
        activity_text = (line[:match.start()] + " " + line[match.end():]).strip()
        activity_text = clean_calendar_line(activity_text)
        is_at_end = (line[match.end():].strip() == "")
        if has_day_number(date_text) or is_at_end:
            date_text = reconstruct_missing_end_year(date_text)
            return activity_text, date_text
    if len(matches) == 1:
        match = matches[0]
        date_text = match.group(0).strip()
        activity_text = (line[:match.start()] + " " + line[match.end():]).strip()
        activity_text = clean_calendar_line(activity_text)
        if not activity_text:
            date_text = reconstruct_missing_end_year(date_text)
            return "", date_text
    return line, None

def split_markdown_table_row(row: str) -> List[str]:
    row = row.strip().strip("|")
    return [cell.strip() for cell in row.split("|")]

def is_table_separator_row(row: str) -> bool:
    cells = split_markdown_table_row(row)
    if not cells:
        return False
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)

def extract_semester_from_section(section: str) -> str | None:
    section_lower = section.lower()
    if "semester gasal" in section_lower or "gasal" in section_lower:
        return "gasal"
    elif "semester genap" in section_lower or "genap" in section_lower:
        return "genap"
    return None

def enrich_activity(activity: str) -> str:
    if not activity:
        return activity
    activity_lower = activity.lower()
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
) -> List[TextBlock]:
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
            blocks: List[TextBlock] = []
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
    blocks: List[TextBlock] = []
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
        
        row_semester = semester_text or current_semester or extract_semester_from_section(section)
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

def normalize_calendar_to_markdown_table(page_texts: List[dict]) -> str:
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

    def activity_to_text(activity_lines: List[str]) -> str:
        return clean_calendar_line(" ".join(activity_lines))

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

            rows.append({
                "page": page,
                "semester": semester,
                "section": section,
                "activity": activity,
                "date": date_text,
            })

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
                if current_activity and not current_date:
                    pending_activity_before_section = current_activity.copy()
                    pending_section_before_section = current_section
                    pending_page_before_section = current_page or page_number
                    pending_semester_before_section = current_semester
                    current_activity = []
                    current_date = None
                else:
                    flush_row()

                # Now update current_semester based on section headers
                if "SEMESTER GASAL" in upper_line:
                    current_semester = "gasal"
                elif "SEMESTER GENAP" in upper_line:
                    current_semester = "genap"

                current_section = line
                continue
            if is_calendar_subheading(line):
                flush_row()
                continue
            activity_part, date_part = split_activity_and_date(line)
            if date_part:
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
                    continue
                if current_date:
                    flush_row()
                if activity_part:
                    current_activity.append(activity_part)
                current_date = date_part
                current_page = page_number
                continue
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

# ============================================================
# BLOCK GENERATION & PARSING
# ============================================================

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

def infer_doc_type(filename: str) -> str:
    name = filename.lower()
    if "kalender" in name or "calendar" in name:
        return "kalender_akademik"
    if "pedoman" in name:
        return "pedoman_akademik"
    return "dokumen_akademik"

def normalize_paragraph_lines(lines: List[str]) -> str:
    text = " ".join(line.strip() for line in lines if line.strip())
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def parse_markdown_to_blocks(markdown_text: str, fallback_source_file: str, total_pages: int = 100) -> List[TextBlock]:
    blocks: List[TextBlock] = []
    current_source = fallback_source_file
    current_page: int | None = None
    current_chapter = ""
    current_section = ""
    current_subsection = ""
    current_semester: str | None = None
    paragraph_buffer: List[str] = []
    table_buffer: List[str] = []

    def current_doc_type() -> str:
        return infer_doc_type(current_source)

    def should_skip_current_content(line: str = "") -> bool:
        return is_excluded_pedoman_line(
            line=line,
            doc_type=current_doc_type(),
            page=current_page,
            current_chapter=current_chapter,
            total_pages=total_pages
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
        if infer_doc_type(current_source) == "kalender_akademik":
            calendar_blocks = calendar_table_to_blocks(
                table_text=table_text,
                source_file=current_source,
                fallback_page=current_page,
                fallback_chapter=current_chapter,
                fallback_section=current_section,
                current_semester=current_semester,
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
        if is_metadata_comment(line):
            meta = extract_metadata_from_comment(line)
            if meta:
                if meta["source_file"]:
                    current_source = meta["source_file"]
                if meta["page"] is not None:
                    current_page = meta["page"]
            continue
        if is_page_heading(line):
            page_from_heading = get_page_from_heading(line)
            if page_from_heading is not None:
                current_page = page_from_heading
            flush_table()
            flush_paragraph()
            continue
        if is_markdown_table_line(line):
            flush_paragraph()
            table_buffer.append(line)
            continue
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
                current_semester = extract_semester_from_section(heading_text)
            elif heading_type == "section":
                current_section = heading_text
                current_subsection = ""
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
# CHUNKING ALGORITHM
# ============================================================

def split_long_text(text: str, target_chars: int, overlap_chars: int) -> List[str]:
    text = text.strip()
    if len(text) <= target_chars:
        return [text]
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

def expand_oversized_blocks(blocks: List[TextBlock]) -> List[TextBlock]:
    expanded: List[TextBlock] = []
    for block in blocks:
        if len(block.text) <= TARGET_CHARS:
            expanded.append(block)
            continue
        parts = split_long_text(block.text, TARGET_CHARS, OVERLAP_CHARS)
        for index, part in enumerate(parts, start=1):
            expanded.append(TextBlock(
                text=part,
                source_file=block.source_file,
                doc_type=block.doc_type,
                page=block.page,
                chapter=block.chapter,
                section=block.section,
                subsection=block.subsection,
                block_type=f"{block.block_type}_part_{index}",
                semester=block.semester,
            ))
    return expanded

def get_overlap_blocks(blocks: List[TextBlock], overlap_chars: int) -> List[TextBlock]:
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
    return [TextBlock(
        text=overlap_text,
        source_file=last.source_file,
        doc_type=last.doc_type,
        page=last.page,
        chapter=last.chapter,
        section=last.section,
        subsection=last.subsection,
        block_type="overlap",
        semester=last.semester,
    )]

def format_pages(pages: List[int]) -> str:
    if not pages:
        return ""
    unique_pages = sorted(set(pages))
    if len(unique_pages) == 1:
        return str(unique_pages[0])
    return f"{unique_pages[0]}-{unique_pages[-1]}"

def create_chunk_id(source_file: str, chunk_index: int, text: str) -> str:
    source_stem = Path(source_file).name.lower()
    source_stem = re.sub(r"[^a-z0-9]+", "_", source_stem).strip("_")
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
    return f"{source_stem}_{chunk_index:04d}_{digest}"

def build_section_path(chapter: str, section: str, subsection: str) -> str:
    parts = [part for part in [chapter, section, subsection] if part]
    return " > ".join(parts)

def build_chunk_from_blocks(blocks: List[TextBlock], chunk_index: int) -> Chunk | None:
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
        "source": source_file,
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
    return Chunk(id=chunk_id, text=text, metadata=metadata)

def chunk_blocks(
    blocks: List[TextBlock],
    target_chars: int = TARGET_CHARS,
    overlap_chars: int = OVERLAP_CHARS,
) -> List[Chunk]:
    blocks = expand_oversized_blocks(blocks)
    chunks: List[Chunk] = []
    buffer: List[TextBlock] = []
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
        if block.doc_type == "kalender_akademik" and block.block_type == "calendar_row":
            flush_buffer()
            chunk = build_chunk_from_blocks([block], chunk_index)
            if chunk:
                chunks.append(chunk)
                chunk_index += 1
            continue

        block_len = len(block.text)
        if buffer and block.source_file != buffer[0].source_file:
            flush_buffer()
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
# OCR FALLBACK ENGINE
# ============================================================

def ocr_page_with_pymupdf(page, zoom: int = 3, config: str = "") -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:
        raise ImportError("Library OCR (pytesseract/pillow) tidak ditemukan.") from e

    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    import os
    tesseract_win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_win_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_win_path

    try:
        text = pytesseract.image_to_string(image, lang="ind+eng", config=config)
    except Exception:
        text = pytesseract.image_to_string(image, lang="eng", config=config)
    return clean_text(text)

# ============================================================
# PIPELINE ENTRY POINT FOR PDF
# ============================================================

def parse_pdf_to_pipeline_chunks(file_content: bytes, filename: str) -> Tuple[List[Chunk], str]:
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    try:
        doc_type = infer_doc_type(filename)
        
        # Check if PDF contains digital text
        with fitz.open(tmp_path) as doc:
            total_pages = len(doc)
            pages_data = []
            for page_index, page in enumerate(doc, start=1):
                text = clean_text(page.get_text("text") or "")
                pages_data.append({
                    "page": page_index,
                    "text": text,
                    "char_count": len(text)
                })
            total_chars = sum(p["char_count"] for p in pages_data)
            
        is_scanned = total_chars < 500

        # Create markdown string using the exact pipeline representation
        if doc_type == "kalender_akademik":
            markdown_parts = ["# Kalender Akademik", f"<!-- source: {filename} -->"]
            if not is_scanned:
                markdown_parts.append("## Tabel Kalender Akademik")
                markdown_parts.append(f"<!-- source: {filename} | type: reconstructed_table_from_text -->")
                calendar_table = normalize_calendar_to_markdown_table(pages_data)
                markdown_parts.append(calendar_table)
            else:
                ocr_pages = []
                with fitz.open(tmp_path) as doc:
                    for page_index, page in enumerate(doc, start=1):
                        ocr_text = ocr_page_with_pymupdf(page)
                        
                        # Layout restoration for specific PDF OCR anomalies
                        if page_index == 1:
                            if "1 - 8 Agustus 2026" in ocr_text and "bagi Mahasiswa Baru)" in ocr_text:
                                ocr_text = ocr_text.replace("1 - 8 Agustus 2026", "")
                                ocr_text = ocr_text.replace("bagi Mahasiswa Baru)", "bagi Mahasiswa Baru) 1 - 8 Agustus 2026")
                        
                        ocr_pages.append({
                            "page": page_index,
                            "text": ocr_text,
                            "char_count": len(ocr_text)
                        })
                markdown_parts.append("## Tabel Kalender Akademik")
                markdown_parts.append(f"<!-- source: {filename} | type: reconstructed_table_from_ocr -->")
                calendar_table = normalize_calendar_to_markdown_table(ocr_pages)
                markdown_parts.append(calendar_table)
            markdown_text = "\n\n".join(markdown_parts)
            
        else:
            # Pedoman Akademik or other PDF
            if is_scanned:
                markdown_parts = ["# Pedoman Akademik", f"<!-- source: {filename} -->"]
                with fitz.open(tmp_path) as doc:
                    for page_index, page in enumerate(doc, start=1):
                        ocr_text = ocr_page_with_pymupdf(page)
                        markdown_parts.append(f"## Halaman {page_index}")
                        markdown_parts.append(f"<!-- source: {filename} | page: {page_index} | type: text -->")
                        markdown_parts.append(ocr_text)
                markdown_text = "\n\n".join(markdown_parts)
            else:
                markdown_parts = []
                with pdfplumber.open(tmp_path) as pdf:
                    for page_number, page in enumerate(pdf.pages, start=1):
                        raw_text = page.extract_text() or ""
                        text = clean_text(raw_text)
                        text = normalize_pedoman_text(text)
                        
                        markdown_parts.append(f"# Halaman {page_number}")
                        markdown_parts.append(f"<!-- source: {filename} | page: {page_number} | type: text -->")
                        if text:
                            markdown_parts.append(text)
                        else:
                            markdown_parts.append("_Tidak ada teks yang berhasil diekstrak pada halaman ini._")
                            
                        try:
                            tables = page.extract_tables() or []
                        except Exception:
                            tables = []
                        for table_index, table in enumerate(tables, start=1):
                            md_table = table_to_markdown(table)
                            if md_table:
                                markdown_parts.append(f"<!-- source: {filename} | page: {page_number} | type: table | table_index: {table_index} -->")
                                markdown_parts.append(md_table)
                markdown_text = "\n\n".join(markdown_parts)

        # Run high-quality processing and chunking
        cleaned_markdown = clean_markdown_for_rag(markdown_text)
        blocks = parse_markdown_to_blocks(
            markdown_text=cleaned_markdown,
            fallback_source_file=filename,
            total_pages=total_pages
        )
        chunks = chunk_blocks(blocks, TARGET_CHARS, OVERLAP_CHARS)
        return chunks, doc_type

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
