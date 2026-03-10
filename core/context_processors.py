from core.content import load_site_content


def site_context(_request):
    data = load_site_content()
    return {
        "site_meta": data["site"],
        "control_sections": data["control_sections"],
    }
