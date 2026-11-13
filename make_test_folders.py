"""Fixture generator: builds test_folders/ tree with 2 demo files per type.

All content is synthetic and PII-free by construction (uses example.com etc.).
Real PDF/DOCX/XLSX binary types are attempts with real libs, mini formats.
Usage: .venv/Scripts/python make_test_folders.py
"""
from __future__ import annotations
import random
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "test_folders"

FOLDERS = [
    "my_documents",
    "c_user/Desktop",
    "c_user/Downloads",
    "c_user/Documents/Sub notes",
    "one_drive_sync-root",
    "one_drive_sync-root/nested business docs",
    "romantic_backup_ USB-thumb",  # a weird name to prove path robustness
]

MD_TEXTS = [
    "# Napkin sketch\n\nIdea: relate the meeting notes to the invoice numbers.\n"
    "Contact: alice.f.framework.nine@example.com\nstatus: draft\n",
    "# Personal journal\n\nWent through the old folders.\n"
    "Saw a phone (555) 000-1111 that looks like a test number, kept as example.\n",
]
TXT_TEXTS = [
    "Plain text note.\nAddress: 42 Example Lane, Springfield, IL 62704 (synthetic).\n",
    "Setup instructions for router RE-3:\nthread count 6, num_ctx 8192.\n",
]
HTML_TEXTS = [
    "<html><body><h1>Team charter</h1><p>Owner: web-team@example.org</p></body></html>",
    "<html><body><h1>Reading list</h1><p>Book one, book two.</p></body></html>",
]
CSV_TEXTS = [
    "name,amount,kind\nsynthetic,alpha,1\nsynthetic,beta,2\n",
    "week,hours\n1,10\n2,12\n",
]
JSON_TEXTS = [
    '{"purpose":"demo json one","author":"agent","refs":["firefly"]}',
    '{"purpose":"demo json two","tasks":["a","b"]}',
]
EML_TEXTS = [
    ("From: p one <p1@example.org>\nTo: q two <q2@example.com>\n"
     "Subject: demo eml one\nDate: Fri, 13 Nov 2026 09:00:00 -0500\n\n"
     "Body eml one. IBAN DE89370400440532013000 for scrub test.\n"),
    ("From: r three <r3@example.net>\nTo: s four <s4@example.com>\n"
     "Subject: demo eml two\nDate: Sat, 14 Nov 2026 09:00:00 -0500\n\n"
     "Body eml two. Phone (555) 222-3456.\n"),
]
# dangerous fixtures — should be refused
DENY_TEXTS = {
    "leaky.env": "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\n",
    "backup_key.pem": "-----BEGIN PRIVATE KEY-----\nFAKEFAKE\n-----END PRIVATE KEY-----\n",
    "client-credentials.txt": "password=FakeOnlyNotReal123!\n",
}


def _tiny_pdf(text: str) -> bytes:
    """Minimal valid one-page PDF with an uncompressed content stream."""
    text = text.encode("cp1252", errors="replace")
    stream = (b"BT /F1 12 Tf 50 750 Td (" + text.replace(b"(", b"\\(").replace(b")", b"\\)")
              + b") Tj ET")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objs)+1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n").encode()
    return out


def _tiny_docx(text: str) -> bytes:
    """Minimal DOCX (zip + [Content_Types].xml + document.xml with the text)."""
    import zipfile
    import io
    buf = io.BytesIO()
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    doc = (f'<?xml version="1.0" encoding="UTF-8"?>'
           f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f'<w:body><w:p><w:r><w:t>{escaped}</w:t></w:r></w:p></w:body></w:document>').encode()
    ct = (b'<?xml version="1.0" encoding="UTF-8"?>'
          b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          b'<Default Extension="xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          b'</Types>')
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("word/document.xml", doc)
    return buf.getvalue()


def _tiny_xlsx(text: str) -> bytes:
    """Minimal readable XLSX with one sheet, one cell (via zipfile; xlrd not needed)."""
    import zipfile
    import io
    buf = io.BytesIO()
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    shared = (f'<?xml version="1.0" encoding="UTF-8"?>'
              f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="1" uniqueCount="1">'
              f'<si><t>{escaped}</t></si></sst>').encode()
    sheet = (b'<?xml version="1.0" encoding="UTF-8"?>'
             b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             b'<sheetData><row r="1"><c r="A1" t="s"><v>0</v></c></row></sheetData></worksheet>')
    wb = (b'<?xml version="1.0" encoding="UTF-8"?>'
          b'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          b'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          b'<sheets><sheet name="demo" sheetId="1" r:id="rId1"/></sheets></workbook>')
    ct = (b'<?xml version="1.0" encoding="UTF-8"?>'
          b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          b'<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
          b'<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
          b'<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet+xml"/>'
          b'</Types>')
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("xl/sharedStrings.xml", shared)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/workbook.xml", wb)
    return buf.getvalue()

def _tiny_pptx(text: str) -> bytes:
    import zipfile, io
    buf = io.BytesIO()
    slide = (f'<?xml version="1.0"?>'
             f'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
             f'<p:txBody><a:p xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
             f'<a:t>{text}</a:t></a:p></p:txBody></p:sld>').encode()
    ct = (b'<?xml version="1.0"?>'
          b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          b'<Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
          b'</Types>')
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("ppt/slides/slide1.xml", slide)
    return buf.getvalue()


def plant_all(randomize: bool = False) -> dict:
    """Create the tree, 2 files per type per folder, plus deny-listed traps."""
    import shutil
    if ROOT.exists():
        shutil.rmtree(ROOT)
    planted = {}
    rng = random.Random(42)
    for folder in FOLDERS:
        d = ROOT / folder
        d.mkdir(parents=True, exist_ok=True)
        files = {
            "note-one.md": MD_TEXTS[0], "note-two.md": MD_TEXTS[1],
            "note-one.txt": TXT_TEXTS[0], "note-two.txt": TXT_TEXTS[1],
            "page-one.html": HTML_TEXTS[0], "page-two.html": HTML_TEXTS[1],
            "table-one.csv": CSV_TEXTS[0], "table-two.csv": CSV_TEXTS[1],
            "data-one.json": JSON_TEXTS[0], "data-two.json": JSON_TEXTS[1],
            "mail-one.eml": EML_TEXTS[0], "mail-two.eml": EML_TEXTS[1],
            "doc-one.pdf": _tiny_pdf("Demo PDF one: contract A with alice@example.com"),
            "doc-two.pdf": _tiny_pdf("Demo PDF two: receipt B for bob@example.org"),
            "report-one.docx": _tiny_docx("Demo DOCX one: policy text with (555) 010-2030."),
            "report-two.docx": _tiny_docx("Demo DOCX two: meeting minutes, ledger sheet."),
            "sheet-one.xlsx": _tiny_xlsx("Demo XLSX one: budget row, card 4111 1111 1111 1111."),
            "deck-one.pptx": _tiny_pptx("Demo PPTX one: title slide with iban DE89370400440532013000."),
        }
        for name, content in files.items():
            if isinstance(content, bytes):
                (d / name).write_bytes(content)
            else:
                (d / name).write_text(content, encoding="utf-8")
        # deny-list traps: 2 per folder
        for name, content in list(DENY_TEXTS.items())[:2]:
            folder_is_trap = folder.endswith("USB-thumb") or "Desktop" in folder
            if folder_is_trap or rng.random() < 0.5:
                (d / name).write_text(content, encoding="utf-8")
        planted[folder] = len(files) + 2
    return planted


if __name__ == "__main__":
    counts = plant_all()
    total = sum(counts.values())
    for folder, n in counts.items():
        print(f"{n:3d} files  {folder}")
    print(f"total files planted: {total}")
    print(f"tree root: {ROOT}")
