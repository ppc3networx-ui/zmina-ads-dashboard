"""
generate.py - чистый рендер дашбордов из уже сохранённого JSON.
Доступа к Google Ads НЕТ и быть не должно - только чтение data/*.json
и template.html, запись dashboard_<key>.html и index.html в docs/
(папка docs/ - это то, что раздаёт GitHub Pages).

Запуск: python3 generate.py
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TEMPLATE_PATH = os.path.join(BASE_DIR, "template.html")
DOCS_DIR = os.path.join(BASE_DIR, "docs")  # GitHub Pages раздаёт именно эту папку


def render_product(key: str, name: str) -> str:
    data_path = os.path.join(DATA_DIR, f"compact_{key}.json")
    with open(data_path, "r", encoding="utf-8") as f:
        data_raw = f.read()  # уже компактный JSON от sync.py, вставляем как есть

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    html = template.replace(
        "__PRODUCT_NAME__", json.dumps(name, ensure_ascii=False)
    ).replace("__DATA_JSON__", data_raw)

    os.makedirs(DOCS_DIR, exist_ok=True)
    out_path = os.path.join(DOCS_DIR, f"dashboard_{key}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


def render_index(manifest) -> str:
    items = "\n".join(
        f'<li><a href="dashboard_{m["key"]}.html">{m["name"]}</a>'
        f'<span class="upd">обновлено {m.get("updated", "-")}</span></li>'
        for m in manifest
    )
    html = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Google Ads - дашборды</title>
<style>
  body{{font-family:-apple-system,'Segoe UI',Arial,sans-serif;background:#f5f7f6;color:#1f2a24;max-width:640px;margin:60px auto;padding:0 20px}}
  h1{{color:#2f6f4f;font-size:20px}}
  ul{{list-style:none;padding:0}}
  li{{padding:14px 18px;background:#fff;border-radius:14px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.06);
      border:1px solid #e3e8e5;display:flex;justify-content:space-between;align-items:center;gap:12px}}
  a{{color:#2f6f4f;text-decoration:none;font-weight:600}}
  .upd{{color:#8a9791;font-size:12px;white-space:nowrap}}
</style></head>
<body>
<h1>Дашборды Google Ads</h1>
<ul>{items}</ul>
</body></html>"""
    os.makedirs(DOCS_DIR, exist_ok=True)
    out_path = os.path.join(DOCS_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


def main():
    manifest_path = os.path.join(DATA_DIR, "manifest.json")
    if not os.path.exists(manifest_path):
        raise SystemExit(
            f"Не найден {manifest_path}. Сначала запустите sync.py, "
            "чтобы получить данные из Google Ads."
        )
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for m in manifest:
        path = render_product(m["key"], m["name"])
        print(f"OK: {path}")

    idx_path = render_index(manifest)
    print(f"OK: {idx_path}")


if __name__ == "__main__":
    main()
