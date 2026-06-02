from pathlib import Path
import re
import json
import hashlib
from dataclasses import dataclass
from typing import Any


# ============================================================
# KONFIGURASI PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

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

TARGET_CHARS = 1200
OVERLAP_CHARS = 200
MIN_CHUNK_CHARS = 150


# ============================================================
# DATA STRUCTURE
# ============================================================

@dataclass
class TextBlock:
    text: str
    source_file: str
    doc_type: str
    page: int | None
    section: str
    block_type: str


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


def fix_doubled_char_line(line: str) -> str:
    """
    Memperbaiki kasus PDF yang mengekstrak teks menjadi huruf dobel:
    Contoh:
    'PPuujjii ssyyuukkuurr' -> 'Puji syukur'

    Fungsi ini hanya aktif jika pola huruf dobelnya dominan dalam satu baris,
    sehingga tidak terlalu agresif terhadap kata normal.
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
    # Contoh yang dibersihkan:
    # "132 Pedoman Akademik Program Sarjana Fakultas Teknik Universitas Udayana 2024"
    # "Pedoman Akademik Program Sarjana Fakultas Teknik Universitas Udayana 2024 295"
    # "294 Pedoman Akademik Program Sarjana Fakultas Teknik Universitas Udayana 2022"
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

# Metadata comment dibuat oleh data_loading.py, contohnya:
# <!-- source: Buku Pedoman Akademik Sarjana FT 2024.pdf | page: 49 | type: text -->
# Parsing dilakukan dengan split "|", bukan regex lazy, agar source_file tidak terpotong menjadi "B" atau "K".
SOURCE_META_RE = re.compile(r"^<!--\s*(.*?)\s*-->$", re.IGNORECASE)

PAGE_HEADING_RE = re.compile(r"^#{1,3}\s*Halaman\s+(\d+)", re.IGNORECASE)

SECTION_HEADING_RE = re.compile(
    r"^("
    r"BAGIAN\s+\d+\.?\s+.+|"
    r"LAMPIRAN\s+[A-Z]\.?\s+.+|"
    r"\d+(?:\.\d+)+\.?\s+.+|"      # contoh: 4.2 Cuti Akademik, 10.7 Jalur Kelulusan
    r"SEMESTER\s+.+|"
    r"[IVXLC]+\.\s+.+|"            # contoh: II. PERKULIAHAN DAN PEMBELAJARAN
    r"KEGIATAN AKADEMIK LAINNYA.+"
    r")$",
    re.IGNORECASE,
)

MARKDOWN_TABLE_RE = re.compile(r"^\|.*\|$")


def extract_metadata_from_comment(line: str) -> dict[str, Any] | None:
    """
    Membaca metadata dari komentar HTML.

    Masalah sebelumnya:
    Regex lama memakai pola lazy dan optional group, sehingga source:
    "Buku Pedoman Akademik Sarjana FT 2024.pdf" bisa terbaca hanya menjadi "B".

    Fungsi ini lebih aman karena membaca pasangan key-value berdasarkan pemisah "|".
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


def is_section_heading(line: str) -> bool:
    line = line.strip()

    if not line:
        return False

    if line.startswith("#"):
        return True

    return SECTION_HEADING_RE.match(line) is not None


def is_markdown_table_line(line: str) -> bool:
    return MARKDOWN_TABLE_RE.match(line.strip()) is not None


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


def calendar_table_to_blocks(
    table_text: str,
    source_file: str,
    fallback_page: int | None,
    fallback_section: str,
) -> list[TextBlock]:
    """
    Khusus kalender akademik:
    tabel tidak disimpan sebagai satu blok besar, tetapi dipecah per baris kegiatan.

    Format input yang diharapkan:
    | Halaman | Bagian | Kegiatan | Waktu |
    |---|---|---|---|
    | 2 | II. PERKULIAHAN DAN PEMBELAJARAN | Pembayaran UKT | 17 Juli - 15 Agustus 2025 |
    """
    rows = [row.strip() for row in table_text.splitlines() if row.strip()]
    if len(rows) < 3:
        return []

    header_cells = [cell.lower() for cell in split_markdown_table_row(rows[0])]

    required_columns = ["halaman", "bagian", "kegiatan", "waktu"]
    if not all(column in header_cells for column in required_columns):
        return []

    index_map = {name: header_cells.index(name) for name in required_columns}
    blocks: list[TextBlock] = []

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

        if not activity and not date_text:
            continue

        page = int(page_text) if page_text.isdigit() else fallback_page

        text = (
            f"Bagian: {section}\n"
            f"Kegiatan: {activity}\n"
            f"Waktu: {date_text}"
        ).strip()

        block = make_block(
            text=text,
            source_file=source_file,
            page=page,
            section=section,
            block_type="calendar_row",
        )

        if block:
            blocks.append(block)

    return blocks


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
    section: str,
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
        section=section,
        block_type=block_type,
    )


def parse_markdown_to_blocks(markdown_text: str, fallback_source_file: str) -> list[TextBlock]:
    """
    Mengubah Markdown bersih menjadi blok-blok logis:
    - heading
    - paragraph
    - table

    Blok ini nanti digabung menjadi chunk.
    """
    blocks: list[TextBlock] = []

    current_source = fallback_source_file
    current_page: int | None = None
    current_section = ""
    paragraph_buffer: list[str] = []
    table_buffer: list[str] = []

    def flush_paragraph():
        nonlocal paragraph_buffer

        if not paragraph_buffer:
            return

        paragraph = normalize_paragraph_lines(paragraph_buffer)
        block = make_block(
            text=paragraph,
            source_file=current_source,
            page=current_page,
            section=current_section,
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

        # Khusus Kalender Akademik, tabel dipecah per baris kegiatan
        # supaya satu kegiatan dan waktunya tidak terpotong saat chunking.
        if infer_doc_type(current_source) == "kalender_akademik":
            calendar_blocks = calendar_table_to_blocks(
                table_text=table_text,
                source_file=current_source,
                fallback_page=current_page,
                fallback_section=current_section,
            )

            if calendar_blocks:
                blocks.extend(calendar_blocks)
                table_buffer = []
                return

        block = make_block(
            text=table_text,
            source_file=current_source,
            page=current_page,
            section=current_section,
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

        # Heading section disimpan sebagai blok dan menjadi metadata section aktif.
        if is_section_heading(line):
            flush_paragraph()
            current_section = re.sub(r"^#+\s*", "", line).strip()

            block = make_block(
                text=current_section,
                source_file=current_source,
                page=current_page,
                section=current_section,
                block_type="heading",
            )

            if block:
                blocks.append(block)

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
    1. antar kalimat,
    2. fallback berdasarkan karakter.
    """
    text = text.strip()

    if len(text) <= target_chars:
        return [text]

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

                while start < len(sentence):
                    end = start + target_chars
                    part = sentence[start:end].strip()

                    if part:
                        chunks.append(part)

                    start = max(end - overlap_chars, end)

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
                    section=block.section,
                    block_type=f"{block.block_type}_part_{index}",
                )
            )

    return expanded


def get_overlap_blocks(blocks: list[TextBlock], overlap_chars: int) -> list[TextBlock]:
    """
    Mengambil beberapa block terakhir sebagai overlap untuk chunk berikutnya.
    """
    if overlap_chars <= 0:
        return []

    selected = []
    total_chars = 0

    for block in reversed(blocks):
        selected.insert(0, block)
        total_chars += len(block.text)

        if total_chars >= overlap_chars:
            break

    return selected


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
        if not has_table:
            return None

    pages = [block.page for block in blocks if block.page is not None]
    source_file = blocks[0].source_file
    doc_type = blocks[0].doc_type

    section_candidates = [block.section for block in blocks if block.section]
    section = section_candidates[-1] if section_candidates else ""

    chunk_id = create_chunk_id(source_file, chunk_index, text)

    metadata = {
        "source_file": source_file,
        "doc_type": doc_type,
        "page_start": min(pages) if pages else None,
        "page_end": max(pages) if pages else None,
        "pages": format_pages(pages),
        "section": section,
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
    Menggabungkan blok-blok teks menjadi chunk berukuran target_chars
    dengan overlap berbasis block terakhir.
    """
    blocks = expand_oversized_blocks(blocks)

    chunks: list[Chunk] = []
    buffer: list[TextBlock] = []
    buffer_chars = 0
    chunk_index = 1

    for block in blocks:
        block_len = len(block.text)

        # Jangan gabungkan dokumen berbeda dalam satu chunk.
        if buffer and block.source_file != buffer[0].source_file:
            chunk = build_chunk_from_blocks(buffer, chunk_index)

            if chunk:
                chunks.append(chunk)
                chunk_index += 1

            buffer = []
            buffer_chars = 0

        # Jika buffer sudah penuh, flush dulu.
        if buffer and buffer_chars + block_len > target_chars:
            chunk = build_chunk_from_blocks(buffer, chunk_index)

            if chunk:
                chunks.append(chunk)
                chunk_index += 1

            # Kalender tidak memakai overlap agar baris kegiatan tidak terduplikasi
            # di beberapa chunk berbeda.
            if buffer and buffer[0].doc_type == "kalender_akademik":
                overlap_blocks = []
            else:
                overlap_blocks = get_overlap_blocks(buffer, overlap_chars)

            buffer = overlap_blocks.copy()
            buffer_chars = sum(len(item.text) for item in buffer)

        buffer.append(block)
        buffer_chars += block_len

    if buffer:
        chunk = build_chunk_from_blocks(buffer, chunk_index)

        if chunk:
            chunks.append(chunk)

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
        print(f"Section : {chunk.metadata['section']}")
        print(f"Chars   : {chunk.metadata['char_count']}")
        print("-" * 80)
        print(chunk.text[:700])
        print()


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

    print_chunk_preview(chunks)

    print("\n====================================================")
    print("[SELESAI] Cleaning lanjutan dan chunking selesai.")
    print("====================================================")


if __name__ == "__main__":
    main()
