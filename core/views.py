import html
import mimetypes
from pathlib import Path
import re
from xml.etree import ElementTree
from zipfile import ZipFile

from django.http import FileResponse
from django.http import Http404
from django.shortcuts import render

from .content import SOURCE, load_site_content
from .document_templates import DOCUMENT_TEMPLATES, TEMPLATES_LIBRARY


POLICY_FILENAME = "SDLCP.docx"


def extract_docx_html(file_path: Path):
    namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(file_path) as archive:
        with archive.open("word/document.xml") as document:
            root = ElementTree.parse(document).getroot()

    blocks = []
    for paragraph in root.findall(".//w:body/w:p", namespaces):
        texts = [node.text for node in paragraph.findall(".//w:t", namespaces) if node.text]
        if not texts:
            continue
        paragraph_text = html.escape("".join(texts).strip())
        if not paragraph_text:
            continue
        if re.match(r"^\d+(\.\d+)*\s+[A-Z]", paragraph_text):
            blocks.append(f"<h2>{paragraph_text}</h2>")
        else:
            blocks.append(f"<p>{paragraph_text}</p>")
    return "\n".join(blocks)


def home(request):
    data = load_site_content()
    return render(
        request,
        "core/home.html",
        {
            "page": data["pages"]["home"],
            "areas": data["areas"],
            "control_sections": data["control_sections"],
            "risks": data["risks"],
            "background": data["background"],
        },
    )


def policy(request):
    policy_path = Path(__file__).resolve().parent.parent / "static" / "templates" / POLICY_FILENAME
    if not policy_path.exists():
        raise Http404(POLICY_FILENAME)
    return render(
        request,
        "core/policy.html",
        {
            "page": {
                "title": "SDLC Policy",
                "body_html": extract_docx_html(policy_path),
            },
            "policy_download_url": "/policy/download/",
        },
    )


def policy_download(request):
    file_path = Path(__file__).resolve().parent.parent / "static" / "templates" / POLICY_FILENAME
    if not file_path.exists():
        raise Http404(POLICY_FILENAME)
    content_type, _ = mimetypes.guess_type(file_path.name)
    return FileResponse(
        file_path.open("rb"),
        as_attachment=True,
        filename=file_path.name,
        content_type=content_type
        or "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def background_index(request):
    data = load_site_content()
    return render(
        request,
        "core/section_index.html",
        {
            "page": data["pages"]["background_index"],
            "items": data["background"],
            "item_type": "background",
        },
    )


def background_detail(request, slug):
    data = load_site_content()
    page = data["background_lookup"].get(slug)
    if not page:
        raise Http404(slug)
    return render(
        request,
        "core/detail.html",
        {"page": page, "meta_items": [("Section", "Background")]},
    )


def area_index(request):
    data = load_site_content()
    return render(
        request,
        "core/section_index.html",
        {
            "page": data["pages"]["areas_index"],
            "items": data["areas"],
            "item_type": "area",
        },
    )


def area_detail(request, slug):
    data = load_site_content()
    page = data["area_lookup"].get(slug)
    if not page:
        raise Http404(slug)
    return render(
        request,
        "core/detail.html",
        {
            "page": page,
            "meta_items": [("Section", "Area"), ("Key", page["section"])],
        },
    )


def controls_index(request):
    data = load_site_content()
    return render(
        request,
        "core/controls_index.html",
        {
            "page": data["pages"]["controls_index"],
            "sections": data["control_sections"],
            "controls_by_section": data["controls_by_section"],
        },
    )


def control_section(request, section):
    data = load_site_content()
    page = data["pages"]["control_sections"].get(section)
    if not page:
        raise Http404(section)
    return render(
        request,
        "core/section_index.html",
        {
            "page": page,
            "items": data["controls_by_section"].get(section, []),
            "item_type": "control",
        },
    )


def control_detail(request, section, slug):
    data = load_site_content()
    page = data["control_lookup"].get((section, slug))
    if not page:
        raise Http404(f"{section}/{slug}")
    meta_items = [
        ("Control Code", page.get("control_code", "Not set")),
        ("Section", page["section_title"]),
        ("Level", str(page.get("level", "Not set"))),
    ]
    return render(
        request,
        "core/detail.html",
        {"page": page, "meta_items": meta_items},
    )


def risk_index(request):
    data = load_site_content()
    return render(
        request,
        "core/section_index.html",
        {
            "page": data["pages"]["risks_index"],
            "items": data["risks"],
            "item_type": "risk",
        },
    )


def risk_detail(request, slug):
    data = load_site_content()
    page = data["risk_lookup"].get(slug)
    if not page:
        raise Http404(slug)
    meta_items = [("Risk ID", page.get("risk_id", "Not set"))]
    return render(
        request,
        "core/detail.html",
        {"page": page, "meta_items": meta_items},
    )


def templates_index(request):
    return render(
        request,
        "core/templates_index.html",
        {"page": TEMPLATES_LIBRARY, "items": DOCUMENT_TEMPLATES},
    )


def template_download(request, slug):
    template_item = next((item for item in DOCUMENT_TEMPLATES if item["slug"] == slug), None)
    if not template_item:
        raise Http404(slug)
    file_path = Path(__file__).resolve().parent.parent / "static" / "templates" / template_item["filename"]
    if not file_path.exists():
        raise Http404(template_item["filename"])
    content_type, _ = mimetypes.guess_type(file_path.name)
    return FileResponse(
        file_path.open("rb"),
        as_attachment=True,
        filename=template_item["filename"],
        content_type=content_type or "application/octet-stream",
    )


def asset(request, filename):
    asset_name = Path(filename).name
    if asset_name == "favicon.ico":
        asset_path = SOURCE / "static" / "favicon.ico"
    else:
        asset_path = SOURCE / "static" / "images" / asset_name
    if not asset_path.exists():
        raise Http404(asset_name)
    content_type, _ = mimetypes.guess_type(asset_path.name)
    return FileResponse(asset_path.open("rb"), content_type=content_type or "application/octet-stream")
