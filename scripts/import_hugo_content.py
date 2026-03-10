import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT.parent / "kosli-sdlc"
OUTPUT = ROOT / "data" / "site_content.json"

SITE_META = {
    "title": "Car & General Software Development Lifecycle",
    "company": "Cargen",
    "company_label": "Car & General",
    "summary": "A Django-based secure software delivery framework migrated from the original Hugo implementation.",
    "repo_name": "cargen-sdlc",
}

PARAMS = {
    "company": SITE_META["company_label"],
    "csor": SITE_META["company"],
    "vcs": "Git",
    "vcsHost": "GitHub",
    "gitProvider": "GitHub Actions",
    "title": SITE_META["title"],
}

SECTIONS = {
    "build": "Build Controls",
    "release": "Release Controls",
    "runtime": "Runtime Controls",
    "lifecycle": "Lifecycle Controls",
}

TEXT_REPLACEMENTS = {
    "Kosli's": "Car & General's",
    "Kosli": "Car & General",
    "kosli": "cargen",
    "organisationâ€”": "organisation - ",
    "Reactive complianceâ€”": "Reactive compliance - ",
    "organisationâ€™s": "organisation's",
    "itâ€™s": "it's",
}


def read_markdown(path: Path):
    content = path.read_text(encoding="utf-8", errors="ignore")
    if not content.startswith("---"):
        return {}, content
    _, rest = content.split("---", 1)
    front_matter, body = rest.split("---", 1)
    return parse_yaml_subset(front_matter.strip("\n")), body.strip()


def parse_yaml_subset(source: str):
    lines = source.splitlines()
    index = 0

    def parse_scalar(value: str):
        value = value.strip()
        if not value:
            return ""
        if value[0] == value[-1] and value[0] in ("'", '"'):
            return value[1:-1]
        if value.isdigit():
            return int(value)
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        return value

    def current_indent(line: str):
        return len(line) - len(line.lstrip(" "))

    def parse_block(indent: int):
        nonlocal index
        while index < len(lines) and not lines[index].strip():
            index += 1
        if index >= len(lines):
            return {}

        if current_indent(lines[index]) == indent and lines[index].lstrip().startswith("- "):
            items = []
            while index < len(lines):
                line = lines[index]
                if not line.strip():
                    index += 1
                    continue
                if current_indent(line) != indent or not line.lstrip().startswith("- "):
                    break
                item_text = line.strip()[2:].strip()
                index += 1
                if not item_text:
                    items.append(parse_block(indent + 2))
                    continue
                if ":" in item_text:
                    key, _, remainder = item_text.partition(":")
                    item = {key.strip(): parse_scalar(remainder.strip()) if remainder.strip() else ""}
                    while index < len(lines):
                        peek = lines[index]
                        if not peek.strip():
                            index += 1
                            continue
                        peek_indent = current_indent(peek)
                        if peek_indent < indent + 2:
                            break
                        if peek_indent == indent + 2 and not peek.lstrip().startswith("- "):
                            nested_key, _, nested_remainder = peek.strip().partition(":")
                            index += 1
                            if nested_remainder.strip():
                                item[nested_key.strip()] = parse_scalar(nested_remainder.strip())
                            else:
                                item[nested_key.strip()] = parse_block(indent + 4)
                            continue
                        break
                    items.append(item)
                    continue
                items.append(parse_scalar(item_text))
            return items

        result = {}
        while index < len(lines):
            line = lines[index]
            if not line.strip():
                index += 1
                continue
            if current_indent(line) != indent:
                break
            key, _, remainder = line.strip().partition(":")
            index += 1
            if remainder.strip():
                result[key.strip()] = parse_scalar(remainder.strip())
                continue
            result[key.strip()] = parse_block(indent + 2)
        return result

    return parse_block(0)


def normalize_text(value: str):
    result = value
    for old, new in TEXT_REPLACEMENTS.items():
        result = result.replace(old, new)
    result = re.sub(r"https?://(?:app|docs|www)\.kosli\.com[^\s)\"]*", "#", result)
    result = re.sub(r"https?://github\.com/kosli-dev[^\s)\"]*", "#", result)
    return result


def resolve_ref(target: str, current_path: Path):
    cleaned = target.strip().strip('"').strip("'")
    if cleaned.endswith(".md"):
        target_path = (current_path.parent / cleaned).resolve()
        relative = target_path.relative_to(SOURCE / "content")
        parts = list(relative.parts)
        if parts[-1] == "_index.md":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1].replace(".md", "")
        return "/" + "/".join(parts) + "/"
    cleaned = cleaned.strip("/")
    return "/" + cleaned + "/"


def render_inline(text: str, current_path: Path, metadata: dict):
    text = normalize_text(text)
    text = re.sub(
        r"\{\{[%<]\s*param\s+\"([^\"]+)\"\s*[>%]\}\}",
        lambda match: str(PARAMS.get(match.group(1), metadata.get(match.group(1), ""))),
        text,
    )
    text = re.sub(
        r"\{\{<\s*ref\s+\"([^\"]+)\"\s*>\}\}",
        lambda match: resolve_ref(match.group(1), current_path),
        text,
    )
    text = re.sub(
        r"\{\{<\s*relref\s+\"([^\"]+)\"\s*>\}\}",
        lambda match: resolve_ref(match.group(1), current_path),
        text,
    )
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def render_markdown(body: str, current_path: Path, metadata: dict):
    body = normalize_text(body)
    body = re.sub(
        r"\{\{<\s*figure\s+src=\"([^\"]+)\"\s+alt=\"([^\"]*)\"\s*>\}\}",
        lambda match: (
            f'<figure><img src="/static/site/images/{Path(match.group(1)).name}" '
            f'alt="{html.escape(match.group(2))}">'
            f"<figcaption>{html.escape(match.group(2))}</figcaption></figure>"
        ),
        body,
    )
    body = re.sub(r"\{\{<\s*hint\s+(\w+)\s*>\}\}", r'<div class="hint \1">', body)
    body = body.replace("{{< /hint >}}", "</div>")
    body = re.sub(
        r"\{\{[%<]\s*param\s+\"([^\"]+)\"\s*[>%]\}\}",
        lambda match: str(PARAMS.get(match.group(1), metadata.get(match.group(1), ""))),
        body,
    )
    body = re.sub(
        r"\{\{<\s*ref\s+\"([^\"]+)\"\s*>\}\}",
        lambda match: resolve_ref(match.group(1), current_path),
        body,
    )
    body = re.sub(
        r"\{\{<\s*relref\s+\"([^\"]+)\"\s*>\}\}",
        lambda match: resolve_ref(match.group(1), current_path),
        body,
    )
    body = re.sub(r"\{\{<[^}]+>\}\}", "", body)
    body = re.sub(r"\{\{%[^}]+%\}\}", "", body)

    lines = [line.rstrip() for line in body.splitlines()]
    blocks = []
    index = 0

    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue

        if line.startswith("<figure"):
            blocks.append(line)
            index += 1
            continue

        if line.startswith("<div class=\"hint"):
            block_lines = [line]
            index += 1
            while index < len(lines):
                block_lines.append(lines[index].strip())
                if lines[index].strip() == "</div>":
                    index += 1
                    break
                index += 1
            blocks.append("".join(block_lines))
            continue

        if re.match(r"^#{1,3}\s", line):
            level = len(line) - len(line.lstrip("#"))
            text = render_inline(line[level:].strip(), current_path, metadata)
            blocks.append(f"<h{level}>{text}</h{level}>")
            index += 1
            continue

        if line.startswith("|") and index + 1 < len(lines) and lines[index + 1].strip().startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            rows = []
            for raw in table_lines:
                cells = [cell.strip() for cell in raw.strip("|").split("|")]
                rows.append(cells)
            header = rows[0]
            body_rows = rows[2:] if len(rows) > 2 else []
            html_rows = "".join(
                "<tr>"
                + "".join(f"<td>{render_inline(cell, current_path, metadata)}</td>" for cell in row)
                + "</tr>"
                for row in body_rows
            )
            html_header = "".join(f"<th>{render_inline(cell, current_path, metadata)}</th>" for cell in header)
            blocks.append(f"<table><thead><tr>{html_header}</tr></thead><tbody>{html_rows}</tbody></table>")
            continue

        if line.startswith(("- ", "* ")):
            items = []
            while index < len(lines) and lines[index].strip().startswith(("- ", "* ")):
                item = lines[index].strip()[2:].strip()
                items.append(f"<li>{render_inline(item, current_path, metadata)}</li>")
                index += 1
            blocks.append("<ul>" + "".join(items) + "</ul>")
            continue

        paragraph_lines = [line]
        index += 1
        while index < len(lines):
            next_line = lines[index].strip()
            if not next_line or re.match(r"^#{1,3}\s", next_line) or next_line.startswith(("- ", "* ", "|", "<figure", "<div class=\"hint", "{{")):
                break
            paragraph_lines.append(next_line)
            index += 1
        paragraph = " ".join(paragraph_lines)
        blocks.append(f"<p>{render_inline(paragraph, current_path, metadata)}</p>")

    return "\n".join(blocks)


def page_url(relative_path: Path):
    parts = list(relative_path.parts)
    if parts[-1] == "_index.md":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].replace(".md", "")
    return "/" + "/".join(parts) + "/"


def build_page(relative_path: Path):
    full_path = SOURCE / "content" / relative_path
    metadata, body = read_markdown(full_path)
    normalized = {}
    for key, value in metadata.items():
        if isinstance(value, str):
            normalized[key] = normalize_text(value)
        elif isinstance(value, list):
            normalized[key] = [
                {inner_key: normalize_text(inner_value) if isinstance(inner_value, str) else inner_value for inner_key, inner_value in item.items()}
                if isinstance(item, dict)
                else normalize_text(item)
                for item in value
            ]
        else:
            normalized[key] = value

    page = {
        **normalized,
        "slug": relative_path.stem if relative_path.stem != "_index" else relative_path.parent.name,
        "url": page_url(relative_path),
        "body_html": render_markdown(body, full_path, normalized),
    }
    if "section" in page:
        page["section_title"] = SECTIONS.get(page["section"], page["section"].title())
    return page


def sorted_pages(paths):
    built = []
    for path in paths:
        relative = path.relative_to(SOURCE / "content")
        built.append(build_page(relative))
    return sorted(built, key=lambda item: item.get("weight", 9999))


def main():
    pages = {
        "home": build_page(Path("_index.md")),
        "background_index": build_page(Path("background") / "_index.md"),
        "areas_index": {"title": "Delivery Areas", "body_html": ""},
        "controls_index": build_page(Path("controls") / "_index.md"),
        "risks_index": build_page(Path("risks") / "_index.md"),
        "control_sections": {},
    }

    background = [page for page in sorted_pages((SOURCE / "content" / "background").glob("*.md")) if page["slug"] != "_index"]
    areas = [page for page in sorted_pages((SOURCE / "content" / "areas").glob("**/*.md")) if page["slug"] != "_index"]
    risks = [page for page in sorted_pages((SOURCE / "content" / "risks").glob("*.md")) if page["slug"] != "_index"]

    control_sections = []
    controls = []
    for section in SECTIONS:
        section_index = build_page(Path("controls") / section / "_index.md")
        pages["control_sections"][section] = section_index
        control_sections.append(
            {
                "section": section,
                "title": section_index["title"],
                "description": f"Controls covering the {section} stage of delivery.",
                "url": section_index["url"],
            }
        )
        section_controls = sorted_pages((SOURCE / "content" / "controls" / section).glob("*.md"))
        controls.extend(page for page in section_controls if page["slug"] != "_index")

    pages["areas_index"]["body_html"] = "<p>Four operating areas define how Car & General structures secure delivery work.</p>"
    pages["home"]["control_count"] = len(controls)

    payload = {
        "site": SITE_META,
        "pages": pages,
        "background": background,
        "areas": areas,
        "risks": risks,
        "controls": controls,
        "control_sections": control_sections,
    }

    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
