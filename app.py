"""
Coupang TW - 18+ Badge Scanner Dashboard
Local: python app.py → http://127.0.0.1:5000
Render: gunicorn app:app (auto-configured via render.yaml)
"""

import csv
import io
import os
import random
import threading
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)

# ---------- CONFIG ----------
DELAY_MIN = 1.0
DELAY_MAX = 2.0
MAX_RETRIES = 3
BADGE_SIGNATURE = "image2/test/High18.png"
PAGES_PER_CATEGORY = range(1, 10)  # pages 1 through 9

# ---------- STATE ----------
state = {
    "running": False,
    "log": [],
    "rows": [],
    "started_at": None,
    "finished_at": None,
    "total_categories": 0,
    "current_category_index": 0,
}
state_lock = threading.Lock()


def log(msg):
    """Append a timestamped message to the in-memory log."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with state_lock:
        state["log"].append(line)


def build_page_url(category_url, page):
    parsed = urlparse(category_url)
    qs = parse_qs(parsed.query)
    qs["page"] = [str(page)]
    new_query = urlencode({k: v[0] for k, v in qs.items()})
    return urlunparse(parsed._replace(query=new_query))


def fetch(url, api_key):
    """Fetch HTML via ScrapingBee with stealth proxy + JS + wait."""
    params = {
        "api_key": api_key,
        "url": url,
        "stealth_proxy": "true",
        "country_code": "tw",
        "render_js": "true",
        "wait": "5000",
    }
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(
                "https://app.scrapingbee.com/api/v1/",
                params=params,
                timeout=180,
            )
            if resp.status_code == 200:
                return resp.text
            log(f"   attempt {attempt+1}: ScrapingBee status {resp.status_code}")
            if resp.status_code in (400, 401, 402):
                log(f"   response: {resp.text[:200]}")
                return None
        except Exception as e:
            log(f"   attempt {attempt+1}: error {e}")
        time.sleep(2 ** attempt + random.random())
    return None


def extract_flagged_products(html):
    soup = BeautifulSoup(html, "html.parser")
    flagged = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if "/products/" not in href:
            continue
        img = anchor.find("img")
        if img is None:
            continue
        src = img.get("src", "") or img.get("data-src", "")
        if BADGE_SIGNATURE not in src:
            continue
        name = (img.get("alt") or "").strip()
        if not name:
            name = anchor.get_text(strip=True)[:200]
        product_url = urljoin("https://www.tw.coupang.com", href)
        product_url = product_url.split("?")[0]
        flagged.append({"name": name, "url": product_url})
    return flagged


def scan_category(category_url, api_key):
    seen_urls = set()
    rows = []
    for page in PAGES_PER_CATEGORY:
        page_url = build_page_url(category_url, page)
        log(f"   page {page}: fetching")
        html = fetch(page_url, api_key)
        if html is None:
            log(f"   page {page}: fetch failed, skipping")
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            continue
        flagged = extract_flagged_products(html)
        new_count = 0
        for item in flagged:
            if item["url"] in seen_urls:
                continue
            seen_urls.add(item["url"])
            rows.append({
                "product_name": item["name"],
                "product_url": item["url"],
                "category_url_found_on": category_url,
            })
            new_count += 1
        log(f"   page {page}: {len(flagged)} flagged, {new_count} new")
        # Save partial results so the user can see live progress
        with state_lock:
            state["rows"].extend([r for r in rows if r not in state["rows"]])
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    return rows


def run_scan(category_urls, api_key):
    """Background worker that scans all categories."""
    try:
        with state_lock:
            state["running"] = True
            state["log"] = []
            state["rows"] = []
            state["started_at"] = datetime.now().isoformat()
            state["finished_at"] = None
            state["total_categories"] = len(category_urls)
            state["current_category_index"] = 0

        log(f"Starting scan of {len(category_urls)} categories")
        log(f"Pages per category: 1-9")
        log(f"Estimated cost: {len(category_urls) * 9 * 75} ScrapingBee credits")

        all_rows = []
        for i, cat_url in enumerate(category_urls, 1):
            with state_lock:
                state["current_category_index"] = i
            log(f"")
            log(f"[{i}/{len(category_urls)}] {cat_url}")
            cat_rows = scan_category(cat_url, api_key)
            log(f"   total unique flagged: {len(cat_rows)}")
            all_rows.extend(cat_rows)

        with state_lock:
            state["rows"] = all_rows
            state["finished_at"] = datetime.now().isoformat()

        log(f"")
        log(f"=== SCAN COMPLETE ===")
        log(f"Total flagged products: {len(all_rows)}")
    except Exception as e:
        log(f"ERROR in scan: {e}")
    finally:
        with state_lock:
            state["running"] = False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/scan", methods=["POST"])
def start_scan():
    with state_lock:
        if state["running"]:
            return jsonify({"error": "Scan already running"}), 400

    data = request.get_json()
    raw_urls = data.get("urls", "").strip()
    api_key = data.get("api_key", "").strip() or os.environ.get("SCRAPINGBEE_API_KEY", "")

    if not api_key:
        return jsonify({"error": "ScrapingBee API key required"}), 400

    urls = [u.strip() for u in raw_urls.splitlines() if u.strip()]
    urls = [u for u in urls if u.startswith("http")]
    if not urls:
        return jsonify({"error": "No valid URLs provided"}), 400

    thread = threading.Thread(target=run_scan, args=(urls, api_key), daemon=True)
    thread.start()
    return jsonify({"status": "started", "url_count": len(urls)})


@app.route("/status")
def get_status():
    with state_lock:
        return jsonify({
            "running": state["running"],
            "log": state["log"][-200:],  # last 200 lines
            "row_count": len(state["rows"]),
            "started_at": state["started_at"],
            "finished_at": state["finished_at"],
            "total_categories": state["total_categories"],
            "current_category_index": state["current_category_index"],
        })


@app.route("/download")
def download_csv():
    with state_lock:
        rows = list(state["rows"])
    if not rows:
        return "No data to download", 404

    output = io.StringIO()
    output.write('\ufeff')  # BOM for Excel UTF-8
    writer = csv.DictWriter(
        output, fieldnames=["product_name", "product_url", "category_url_found_on"]
    )
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)

    csv_bytes = io.BytesIO(output.getvalue().encode("utf-8"))
    filename = f"coupang_18plus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return send_file(
        csv_bytes,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/results")
def get_results():
    with state_lock:
        return jsonify({"rows": list(state["rows"])})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1"
    print("=" * 50)
    print("Coupang 18+ Scanner Dashboard")
    print(f"Open: http://{host}:{port}")
    print("=" * 50)
    app.run(host=host, port=port, debug=False)
