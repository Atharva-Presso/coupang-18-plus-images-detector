"""
Coupang TW - 18+ Badge Scanner Dashboard
<<<<<<< HEAD
Local Flask app. Run: python app.py, then open http://127.0.0.1:5000
=======
Local: python app.py → http://127.0.0.1:5000
Render: gunicorn app:app (auto-configured via render.yaml)
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
"""

import csv
import io
import os
import random
<<<<<<< HEAD
import re
=======
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
import threading
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

import requests
<<<<<<< HEAD
=======
from bs4 import BeautifulSoup
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)

# ---------- CONFIG ----------
DELAY_MIN = 1.0
DELAY_MAX = 2.0
MAX_RETRIES = 3
<<<<<<< HEAD
=======
BADGE_SIGNATURE = "image2/test/High18.png"
PAGES_PER_CATEGORY = range(1, 10)  # pages 1 through 9
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b

# ---------- STATE ----------
state = {
    "running": False,
<<<<<<< HEAD
    "stop_requested": False,
=======
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
    "log": [],
    "rows": [],
    "started_at": None,
    "finished_at": None,
    "total_categories": 0,
    "current_category_index": 0,
<<<<<<< HEAD
    "total_pages_done": 0,
    "total_pages_planned": 0,
=======
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
}
state_lock = threading.Lock()


def log(msg):
<<<<<<< HEAD
=======
    """Append a timestamped message to the in-memory log."""
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with state_lock:
        state["log"].append(line)


def build_page_url(category_url, page):
    parsed = urlparse(category_url)
    qs = parse_qs(parsed.query)
    qs["page"] = [str(page)]
<<<<<<< HEAD
    qs.pop("traceId", None)
=======
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
    new_query = urlencode({k: v[0] for k, v in qs.items()})
    return urlunparse(parsed._replace(query=new_query))


<<<<<<< HEAD
def fetch_html(url, api_key):
    """Fetch via ScrapingBee stealth proxy + JS rendering."""
=======
def fetch(url, api_key):
    """Fetch HTML via ScrapingBee with stealth proxy + JS + wait."""
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
    params = {
        "api_key": api_key,
        "url": url,
        "stealth_proxy": "true",
        "country_code": "tw",
        "render_js": "true",
        "wait": "5000",
    }
    for attempt in range(MAX_RETRIES):
<<<<<<< HEAD
        with state_lock:
            if state["stop_requested"]:
                return None
=======
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
        try:
            resp = requests.get(
                "https://app.scrapingbee.com/api/v1/",
                params=params,
                timeout=180,
            )
<<<<<<< HEAD
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
=======
            if resp.status_code == 200:
                return resp.text
            log(f"   attempt {attempt+1}: ScrapingBee status {resp.status_code}")
            if resp.status_code in (400, 401, 402):
                log(f"   response: {resp.text[:200]}")
                return None
        except Exception as e:
            log(f"   attempt {attempt+1}: error {e}")
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
        time.sleep(2 ** attempt + random.random())
    return None


def extract_flagged_products(html):
<<<<<<< HEAD
    """
    Extract 18+ flagged products from Coupang TW category page HTML.

    Product data is embedded as a double-escaped JSON blob inside a <script> tag.
    Badge products have this structure:
      \\"imageAndTitleArea\\":{\\"defaultUrl\\":\\"...High18.png\\",\\"title\\":\\"PRODUCT NAME\\"}
      \\"itemId\\":607469466271745
    """
    found = {}  # product_url -> name

    raw_count = html.count('High18')
    log(f"      raw 'High18' refs in HTML: {raw_count}")

    for m in re.finditer(r'High18', html, re.IGNORECASE):
        start = max(0, m.start() - 500)
        end   = min(len(html), m.end() + 500)
        chunk = html[start:end]

        # Title: scoped to the imageAndTitleArea block containing the badge URL
        title = "(name not found)"
        area_m = re.search(
            r'\\"imageAndTitleArea\\":\{\\"defaultUrl\\":\\"[^"]*High18[^"]*\\"'
            r',\\"title\\":\\"(.*?)\\"',
            chunk, re.IGNORECASE
        )
        if area_m:
            raw = area_m.group(1)
            try:
                # Bytes were read as latin-1 codepoints — re-encode to recover UTF-8
                title = raw.encode('latin-1').decode('utf-8')
            except Exception:
                title = raw

        # Product URL via itemId (most reliable)
        item_m = re.search(r'\\"itemId\\":\s*(\d{10,})', chunk)
        if item_m:
            product_url = f"https://www.tw.coupang.com/products/{item_m.group(1)}"
        else:
            # Fallback: nearest /products/ href in chunk
            href_m = re.search(r'href["\s:]+(/products/[^\s"\'\\]+)', chunk)
            if href_m:
                product_url = urljoin("https://www.tw.coupang.com", href_m.group(1)).split("?")[0]
            else:
                product_url = f"https://www.tw.coupang.com/products/unknown_{m.start()}"

        if product_url not in found:
            found[product_url] = title
            log(f"      FLAGGED: {title[:70]}")

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
=======
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
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
        for item in flagged:
            if item["url"] in seen_urls:
                continue
            seen_urls.add(item["url"])
<<<<<<< HEAD
            row = {
                "product_name": item["name"],
                "product_url": item["url"],
                "category_url_found_on": category_url,
            }
            rows.append(row)
            new_rows.append(row)
            new_count += 1

        log(f"   page {page}: {len(flagged)} flagged, {new_count} new unique")

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
=======
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
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
            state["log"] = []
            state["rows"] = []
            state["started_at"] = datetime.now().isoformat()
            state["finished_at"] = None
            state["total_categories"] = len(category_urls)
            state["current_category_index"] = 0
<<<<<<< HEAD
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
=======

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
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
    finally:
        with state_lock:
            state["running"] = False


<<<<<<< HEAD
# ---------- ROUTES ----------

=======
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
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
<<<<<<< HEAD
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
=======

    if not api_key:
        return jsonify({"error": "ScrapingBee API key required"}), 400

    urls = [u.strip() for u in raw_urls.splitlines() if u.strip()]
    urls = [u for u in urls if u.startswith("http")]
    if not urls:
        return jsonify({"error": "No valid URLs provided"}), 400

    thread = threading.Thread(target=run_scan, args=(urls, api_key), daemon=True)
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
    thread.start()
    return jsonify({"status": "started", "url_count": len(urls)})


<<<<<<< HEAD
@app.route("/stop", methods=["POST"])
def stop_scan():
    with state_lock:
        if not state["running"]:
            return jsonify({"error": "No scan running"}), 400
        state["stop_requested"] = True
    log("Stop requested by user")
    return jsonify({"status": "stop_requested"})


=======
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
@app.route("/status")
def get_status():
    with state_lock:
        return jsonify({
            "running": state["running"],
<<<<<<< HEAD
            "stop_requested": state["stop_requested"],
            "log": state["log"][-300:],
=======
            "log": state["log"][-200:],  # last 200 lines
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
            "row_count": len(state["rows"]),
            "started_at": state["started_at"],
            "finished_at": state["finished_at"],
            "total_categories": state["total_categories"],
            "current_category_index": state["current_category_index"],
<<<<<<< HEAD
            "total_pages_done": state["total_pages_done"],
            "total_pages_planned": state["total_pages_planned"],
=======
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
        })


@app.route("/download")
def download_csv():
    with state_lock:
        rows = list(state["rows"])
    if not rows:
        return "No data to download", 404
<<<<<<< HEAD
    output = io.StringIO()
    output.write('\ufeff')  # BOM for Excel UTF-8
    writer = csv.DictWriter(output, fieldnames=["product_name", "product_url", "category_url_found_on"])
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)
    csv_bytes = io.BytesIO(output.getvalue().encode("utf-8"))
    filename = f"coupang_18plus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return send_file(csv_bytes, mimetype="text/csv", as_attachment=True, download_name=filename)
=======

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
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b


@app.route("/results")
def get_results():
    with state_lock:
        return jsonify({"rows": list(state["rows"])})


if __name__ == "__main__":
<<<<<<< HEAD
    print("=" * 50)
    print("Coupang 18+ Scanner Dashboard")
    print("Open: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host="127.0.0.1", port=5000, debug=False)
=======
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1"
    print("=" * 50)
    print("Coupang 18+ Scanner Dashboard")
    print(f"Open: http://{host}:{port}")
    print("=" * 50)
    app.run(host=host, port=port, debug=False)
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
