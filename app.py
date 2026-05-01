"""
Coupang TW - 18+ Badge Scanner Dashboard
Local Flask app. Run: python app.py, then open http://127.0.0.1:5000
"""

import csv
import io
import os
import random
import re
import threading
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

import requests
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)

DELAY_MIN = 1.0
DELAY_MAX = 2.0
MAX_RETRIES = 3

state = {
    "running": False,
    "stop_requested": False,
    "log": [],
    "rows": [],
    "started_at": None,
    "finished_at": None,
    "total_categories": 0,
    "current_category_index": 0,
    "total_pages_done": 0,
    "total_pages_planned": 0,
}
state_lock = threading.Lock()


def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with state_lock:
        state["log"].append(line)


def build_page_url(category_url, page):
    parsed = urlparse(category_url)
    qs = parse_qs(parsed.query)
    qs["page"] = [str(page)]
    qs.pop("traceId", None)
    new_query = urlencode({k: v[0] for k, v in qs.items()})
    return urlunparse(parsed._replace(query=new_query))


def fetch_html(url, api_key):
    params = {
        "api_key": api_key,
        "url": url,
        "stealth_proxy": "true",
        "country_code": "tw",
        "render_js": "true",
        "wait": "5000",
    }
    for attempt in range(MAX_RETRIES):
        with state_lock:
            if state["stop_requested"]:
                return None
        try:
            resp = requests.get(
                "https://app.scrapingbee.com/api/v1/",
                params=params,
                timeout=180,
            )
            cost = resp.headers.get("Spb-Cost", "?")
            if resp.status_code == 200:
                log(f"      fetched ok (cost: {cost} credits, {len(resp.text)} chars)")
                return resp.text
            log(f"      attempt {attempt+1}: HTTP {resp.status_code} (cost: {cost})")
            if resp.status_code in (400, 401, 402):
                log(f"      fatal: {resp.text[:300]}")
                return None
        except Exception as e:
            log(f"      attempt {attempt+1}: exception {e}")
        time.sleep(2 ** attempt + random.random())
    return None


def extract_flagged_products(html):
    """
    Extract 18+ flagged products. Coupang renders each product twice:
      - Once in a JSON blob (has itemId + title, double-escaped)
      - Once in the DOM as an <img alt="..."> tag
    We use the JSON blob as primary (has itemId for clean URL), 
    falling back to DOM alt text if name not found.
    Final dedup is by product URL.
    """
    found = {}  # product_url -> name

    raw_count = html.count('High18')
    log(f"      raw 'High18' refs in HTML: {raw_count}")

    for m in re.finditer(r'High18', html, re.IGNORECASE):
        start = max(0, m.start() - 500)
        end   = min(len(html), m.end() + 500)
        chunk = html[start:end]

        # --- Try JSON blob first (double-escaped, has itemId) ---
        title = None
        product_url = None

        area_m = re.search(
            r'\\"imageAndTitleArea\\":\{\\"defaultUrl\\":\\"[^"]*High18[^"]*\\"'
            r',\\"title\\":\\"(.*?)\\"',
            chunk, re.IGNORECASE
        )
        if area_m:
            raw = area_m.group(1)
            try:
                title = raw.encode('latin-1').decode('utf-8')
            except Exception:
                title = raw

        item_m = re.search(r'\\"itemId\\":\s*(\d{10,})', chunk)
        if item_m:
            product_url = f"https://www.tw.coupang.com/products/{item_m.group(1)}"

        # --- Fallback: DOM <img alt="..."> with src=High18 ---
        if not title or not product_url:
            # alt text from <img ... src="...High18..." alt="...">
            dom_alt_m = re.search(
                r'alt="([^"]+)"[^>]*src="[^"]*High18[^"]*"'
                r'|src="[^"]*High18[^"]*"[^>]*alt="([^"]+)"',
                chunk, re.IGNORECASE
            )
            if dom_alt_m:
                title = title or (dom_alt_m.group(1) or dom_alt_m.group(2) or "").strip()

            # product URL from href near the DOM hit
            if not product_url:
                # look for itemId in href: /products/NNN or itemId=NNN
                href_item_m = re.search(r'/products/(\d{10,})', chunk)
                if href_item_m:
                    product_url = f"https://www.tw.coupang.com/products/{href_item_m.group(1)}"
                else:
                    # vendorItemId or itemId in query string
                    qitem_m = re.search(r'itemId=(\d{10,})', chunk)
                    if qitem_m:
                        product_url = f"https://www.tw.coupang.com/products/{qitem_m.group(1)}"

        if not title:
            title = "(name not found)"
        if not product_url:
            product_url = f"https://www.tw.coupang.com/products/unknown_{m.start()}"

        # Dedup: if URL already found, prefer the entry that has a real name
        if product_url not in found or found[product_url] == "(name not found)":
            found[product_url] = title

    # Log only unique results
    for url, name in found.items():
        log(f"      FLAGGED: {name[:70]}")

    return [{"name": v, "url": k} for k, v in found.items()]


def scan_category(category_url, api_key, pages_range):
    seen_urls = set()
    rows = []

    for page in pages_range:
        with state_lock:
            if state["stop_requested"]:
                log(f"   Stop requested, halting")
                break

        page_url = build_page_url(category_url, page)
        log(f"   page {page}: fetching...")
        html = fetch_html(page_url, api_key)

        with state_lock:
            state["total_pages_done"] += 1

        if html is None:
            with state_lock:
                if state["stop_requested"]:
                    break
            log(f"   page {page}: fetch failed, skipping")
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            continue

        flagged = extract_flagged_products(html)
        new_count = 0
        new_rows = []
        for item in flagged:
            if item["url"] in seen_urls:
                continue
            seen_urls.add(item["url"])
            row = {
                "product_name": item["name"],
                "product_url": item["url"],
                "category_url_found_on": category_url,
            }
            rows.append(row)
            new_rows.append(row)
            new_count += 1

        log(f"   page {page}: {len(flagged)} flagged ({new_count} new unique)")

        if new_rows:
            with state_lock:
                state["rows"].extend(new_rows)

        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    return rows


def run_scan(category_urls, api_key, start_page, end_page):
    pages_range = range(start_page, end_page + 1)
    total_pages = len(category_urls) * len(pages_range)

    try:
        with state_lock:
            state["running"] = True
            state["stop_requested"] = False
            state["log"] = []
            state["rows"] = []
            state["started_at"] = datetime.now().isoformat()
            state["finished_at"] = None
            state["total_categories"] = len(category_urls)
            state["current_category_index"] = 0
            state["total_pages_done"] = 0
            state["total_pages_planned"] = total_pages

        est_credits = total_pages * 75
        log(f"Starting: {len(category_urls)} categories x pages {start_page}-{end_page}")
        log(f"Total pages: {total_pages} | Est. cost: {est_credits} credits")
        log(f"")

        for i, cat_url in enumerate(category_urls, 1):
            with state_lock:
                if state["stop_requested"]:
                    log(f"Scan stopped after {i-1} categories")
                    break
                state["current_category_index"] = i

            log(f"[{i}/{len(category_urls)}] {cat_url}")
            cat_rows = scan_category(cat_url, api_key, pages_range)
            log(f"   => {len(cat_rows)} unique flagged in this category")
            log(f"")

        with state_lock:
            total_found = len(state["rows"])
            state["finished_at"] = datetime.now().isoformat()

        log(f"=== SCAN COMPLETE: {total_found} flagged products ===")

    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        log(traceback.format_exc())
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
    start_page = int(data.get("start_page", 1))
    end_page = int(data.get("end_page", 9))

    if not api_key:
        return jsonify({"error": "ScrapingBee API key required"}), 400
    urls = [u.strip() for u in raw_urls.splitlines() if u.strip() and u.strip().startswith("http")]
    if not urls:
        return jsonify({"error": "No valid URLs provided"}), 400
    if start_page < 1 or end_page < start_page or end_page > 100:
        return jsonify({"error": "Invalid page range (1-100, start <= end)"}), 400

    thread = threading.Thread(target=run_scan, args=(urls, api_key, start_page, end_page), daemon=True)
    thread.start()
    return jsonify({"status": "started", "url_count": len(urls)})


@app.route("/stop", methods=["POST"])
def stop_scan():
    with state_lock:
        if not state["running"]:
            return jsonify({"error": "No scan running"}), 400
        state["stop_requested"] = True
    log("Stop requested by user")
    return jsonify({"status": "stop_requested"})


@app.route("/status")
def get_status():
    with state_lock:
        return jsonify({
            "running": state["running"],
            "stop_requested": state["stop_requested"],
            "log": state["log"][-300:],
            "row_count": len(state["rows"]),
            "started_at": state["started_at"],
            "finished_at": state["finished_at"],
            "total_categories": state["total_categories"],
            "current_category_index": state["current_category_index"],
            "total_pages_done": state["total_pages_done"],
            "total_pages_planned": state["total_pages_planned"],
        })


@app.route("/download")
def download_csv():
    with state_lock:
        rows = list(state["rows"])
    if not rows:
        return "No data to download", 404
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.DictWriter(output, fieldnames=["product_name", "product_url", "category_url_found_on"])
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)
    csv_bytes = io.BytesIO(output.getvalue().encode("utf-8"))
    filename = f"coupang_18plus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return send_file(csv_bytes, mimetype="text/csv", as_attachment=True, download_name=filename)


@app.route("/results")
def get_results():
    with state_lock:
        return jsonify({"rows": list(state["rows"])})


if __name__ == "__main__":
    print("=" * 50)
    print("Coupang 18+ Scanner Dashboard")
    print("Open: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host="127.0.0.1", port=5000, debug=False)
