import json
import re
from pathlib import Path

HTML_PATH = Path(__file__).parent / "index.html"
OUT_PATH = Path(__file__).parent / "Tailored_Group_Life_API.postman_collection.json"

html = HTML_PATH.read_text(encoding="utf-8")

def strip_html_tags(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    return re.sub(r'\s+', ' ', text).strip()

# Split by h3 sections
sections = re.split(r'<h3\s+id="(s\d+-\d+)"[^>]*>', html)

items = []
base_url = "https://appstaging.kaf.com.eg/api/tailored-group-life"

for i in range(1, len(sections), 2):
    section_id = sections[i]
    content = sections[i + 1]

    # Title
    title_match = re.search(r'^(.*?)<\/h3>', content, re.DOTALL)
    title = strip_html_tags(title_match.group(1)) if title_match else section_id

    # Method and path
    endpoint_match = re.search(
        r'<div\s+class="endpoint"[^>]*>\s*<span\s+class="method\s+method-([a-z]+)"[^>]*>([^<]+)</span>\s*([^<]+)',
        content,
    )
    method = endpoint_match.group(2).upper() if endpoint_match else "GET"
    path = endpoint_match.group(3).strip() if endpoint_match else "/"

    # First paragraph after endpoint as description
    desc_match = re.search(r'<\/div>\s*<p>(.*?)<\/p>', content, re.DOTALL)
    description = strip_html_tags(desc_match.group(1)) if desc_match else ""

    # Find request/response JSON blocks with their preceding labels
    blocks = []
    for m in re.finditer(r'(<p><strong>[^<]*<\/strong><\/p>\s*)?<pre\s+class="json">(.*?)<\/pre>', content, re.DOTALL):
        label_html = m.group(1) or ""
        label = strip_html_tags(label_html).lower()
        raw = m.group(2)
        raw = re.sub(r'<span\s+class="[^"]*">', '', raw)
        raw = raw.replace('</span>', '')
        raw = raw.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = raw.strip()
        blocks.append({"label": label, "data": data, "raw": raw.strip()})

    body = None
    for block in blocks:
        if "request" in block["label"] or "example" in block["label"]:
            body = block["data"]
            break

    request = {
        "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{access_token}}", "type": "string"}]},
        "method": method,
        "header": [],
        "url": {
            "raw": f"{{{{base_url}}}}{path}",
            "host": ["{{base_url}}"],
            "path": [p for p in path.split('/') if p] + ([""] if path.endswith('/') else []),
        },
        "description": description,
    }
    if body is not None and method in ("POST", "PATCH", "PUT"):
        request["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, indent=2, ensure_ascii=False),
            "options": {"raw": {"language": "json"}},
        }

    # Keep response examples if any block is labelled as response
    response_examples = []
    for block in blocks:
        if "response" in block["label"] or (not block["label"] and block["raw"]):
            response_examples.append({"name": "Example response", "originalRequest": request, "status": "OK", "code": 200, "body": block["raw"]})

    items.append({"name": title, "request": request, "response": response_examples})

# Group by top-level section number
groups = {}
for item in items:
    prefix = item["name"].split()[0]
    top = prefix.split(".")[0]
    groups.setdefault(top, []).append(item)

section_names = {
    "1": "Authentication",
    "2": "Lead Management",
    "3": "Quotations",
    "4": "Reference Data",
    "5": "Members",
    "6": "Purchase Requests",
    "7": "Endorsements",
}

folders = []
for top in sorted(groups.keys(), key=int):
    folders.append({
        "name": section_names.get(top, f"Section {top}"),
        "item": groups[top],
    })

collection = {
    "info": {
        "_postman_id": "tailored-group-life-api-v1",
        "name": "KAF Tailored Group Life API",
        "description": "Tailored Group Life API endpoints for leads, quotations, members, purchase requests, and endorsements. Generated from the API documentation.",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "item": folders,
    "variable": [
        {"key": "base_url", "value": base_url, "type": "string"},
        {"key": "access_token", "value": "", "type": "string"},
    ],
}

OUT_PATH.write_text(json.dumps(collection, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Written {OUT_PATH}")
