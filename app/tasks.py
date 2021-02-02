from pathlib import Path
import pdfminer
from pdfminer.high_level import extract_text, extract_text_to_fp
import pytest
import json
from io import StringIO
import logging

# Reduce a heavy logging pdfminer...
logging.getLogger('pdfminer').setLevel(logging.WARNING)

PDF_FOLDER = "pdfs"
TASKS_FILE = 'tasks.json'

def get_pdfs():
    # Fetch all pdfs in folder
    if not Path(PDF_FOLDER).exists():
        Path(PDF_FOLDER).mkdir()
    pdfs = [f.name for f in Path(PDF_FOLDER).iterdir() if f.suffix == ".pdf"]
    return pdfs


def rename_files():
    # Folders are made out of the Temaoppgave_1-structure, while
    # pdf is using Temainnlevering. Renaming...
    # Rename files to remove spaces / replace spaces with _
    [
        f.rename(Path(PDF_FOLDER) / f.name.replace("innlevering ", "oppgave_"))
        for f in Path(PDF_FOLDER).iterdir()
        if f.suffix == ".pdf"
    ]

def get_pdf(filename):
    return (Path(PDF_FOLDER) / Path(filename + '.pdf'))

def pdf_to_text(html=False):
    # Returns a dictionary where keyword is the file,
    # and value is the TEXT content of the pdf
    rename_files()
    all_tasks = {}
    for pdf in get_pdfs():
        pdf = pdf.strip(".pdf")
        if html:
            output_string = StringIO()
            with open(Path(PDF_FOLDER) / Path(pdf + ".pdf"), 'rb') as fin:
                extract_text_to_fp(
                    fin,
                    output_string,
                    output_type='html',
                    codec=None,
                )
                all_tasks[pdf] = output_string.getvalue()

        else:
            text = extract_text(Path(PDF_FOLDER) / Path(pdf + ".pdf"))
            # Replace \n to html linebreaks:
            text = text.replace("\n", "<br />\n").strip()
            all_tasks[pdf] = text
    return all_tasks


def save_to_file():
    with open(TASKS_FILE, 'w') as f:
        json.dump(pdf_to_text(), f)


def get_assignments():
    save_to_file()
    with open(TASKS_FILE) as f:
        return json.load(f)

def process_files():
    save_to_file()

def test_get_pdfs():
    assert get_pdfs() == ["Temainnlevering 1.pdf"]

def test_get_assignments():
    process_files()
    assert get_assignments() == {'Temainnlevering_1': []}
