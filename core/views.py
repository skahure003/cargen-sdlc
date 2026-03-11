import mimetypes
from pathlib import Path

from django.http import FileResponse
from django.http import Http404
from django.shortcuts import render

from .content import SOURCE, load_site_content
from .document_templates import DOCUMENT_TEMPLATES, TEMPLATES_LIBRARY


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
    data = load_site_content()
    return render(
        request,
        "core/policy.html",
        {
            "page": {
                "title": "SDLC Policy",
                "body_html": data["pages"]["home"]["body_html"],
            }
        },
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
