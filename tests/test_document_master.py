import pytest
import os
from tools.document_master import (
    pdf_processor,
    excel_master,
    docx_creator,
    ppt_generator,
    image_processor,
    video_processor,
    archive_manager,
)


def test_pdf_operations():
    # Create PDF
    res = pdf_processor("create", "memory_vault/test_doc.pdf")
    assert res["status"] == "SUCCESS"
    assert os.path.exists("memory_vault/test_doc.pdf")

    # Extract text from PDF
    read_res = pdf_processor("extract_text", "memory_vault/test_doc.pdf")
    assert read_res["status"] == "SUCCESS"
    assert "text" in read_res


def test_excel_operations():
    sample_data = [{"SKU": "A101", "Qty": 50, "Price": 19.99}]
    res = excel_master("create", "memory_vault/inventory.csv", data=sample_data)
    assert res["status"] == "SUCCESS"
    assert res["rows_written"] == 1

    read_res = excel_master("read", "memory_vault/inventory.csv")
    assert read_res["status"] == "SUCCESS"
    assert read_res["row_count"] == 1


def test_docx_creation():
    sections = [
        {"heading": "Executive Summary", "text": "Q3 Performance Overview"},
        {"heading": "Action Items", "bullets": ["Deploy v8.0", "Run test suite"]},
    ]
    res = docx_creator("memory_vault/briefing.docx", "Project Briefing", sections=sections)
    assert res["status"] == "SUCCESS"
    assert os.path.exists("memory_vault/briefing.docx")
    assert res["sections_count"] == 2


def test_ppt_generation():
    slides = [
        {"title": "Architecture", "bullets": ["Subagents", "RAG Memory", "Cross-Platform"]},
        {"title": "Conclusion", "bullets": ["Ready for production"]},
    ]
    res = ppt_generator("memory_vault/deck.pptx", "P.H.A.S.S Architecture", slides=slides)
    assert res["status"] == "SUCCESS"
    assert os.path.exists("memory_vault/deck.pptx")
    assert res["slides_count"] == 2


def test_image_processing():
    res = image_processor("resize", "memory_vault/sample.ppm", "memory_vault/resized.ppm", width=100, height=100)
    assert res["status"] == "SUCCESS"
    assert os.path.exists("memory_vault/resized.ppm")


def test_video_processing():
    res = video_processor("metadata", "memory_vault/demo.mp4")
    assert res["status"] == "SUCCESS"
    assert res["action"] == "metadata"


def test_archive_management():
    zip_res = archive_manager("create_zip", "memory_vault/bundle.zip", files_or_dir=["memory_vault/inventory.csv"])
    assert zip_res["status"] == "SUCCESS"
    assert os.path.exists("memory_vault/bundle.zip")

    list_res = archive_manager("list", "memory_vault/bundle.zip")
    assert list_res["status"] == "SUCCESS"
    assert len(list_res["entries"]) >= 1