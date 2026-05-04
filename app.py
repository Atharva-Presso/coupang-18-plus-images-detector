import os, re, json, csv, io, time, random, threading
from flask import Flask, render_template, request, jsonify, send_file
import requests

app = Flask(__name__)

# ── Global scan state ──────────────────────────────────────────────────────────
scan_state = {
    "running": False,
    "logs": [],
    "results": [],
    "progress": 0,
    "total_pages": 0,
    "pages_done": 0,
    "flagged_count": 0,
    "error": None,
}
state_lock = threading.Lock()

def log(msg):
    with state_lock:
        scan_state["logs"].append(msg)

# ── Extraction logic ──────────────────────────────────────────────────────────
def _extract_all_links(html):
    """
    Extract all product link positions from the embedded JSON using str.find.
    The HTML contains JSON-serialised data where product links look like:
      \\"link\\":\\"/products/SLUG?itemId=X\\u0026vendorItemId=Y...\\\"
    Returns list of (position, full_decoded_url).
    """
    results = []
    search     = '\\"link\\":\\"'
    end_marker = '\\"'
    pos = 0
    while True:
        idx = html.find(search, pos)
        if idx == -1:
            break
        val_start = idx + len(search)
        val_end   = html.find(end_marker, val_start)
        if val_end == -1:
            break
        url = html[val_start:val_end]
        if url.startswith('/products/'):
            decoded = url.replace('\\u0026', '&')
            results.append((idx, decoded))
        pos = val_end + 1
    return results


def extract_flagged_products(html, category_url):
    found = {}
    all_links = _extract_all_links(html)

    for m in re.finditer(r'High18', html, re.IGNORECASE):
        badge_pos = m.start()
        start = max(0, badge_pos - 500)
        end   = min(len(html), m.end() + 500)
        chunk = html[start:end]

        # Product name
        title = "(name not found)"
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

        # Full product URL — find the nearest link field to this badge
        if all_links:
            closest_pos, closest_url = min(all_links, key=lambda x: abs(x[0] - badge_pos))
            product_url = "https://www.tw.coupang.com" + closest_url
        else:
            # Fallback: itemId-only URL
            item_m = re.search(r'\\"itemId\\":\s*(\d{10,})', chunk)
            pid = item_m.group(1) if item_m else f"unknown_{badge_pos}"
            product_url = f"https://www.tw.coupang.com/products/{pid}"

        if product_url not in found:
            found[product_url] = {"name": title, "url": product_url, "category_url": category_url}

    return list(found.values())

# ── ScrapingBee fetch ──────────────────────────────────────────────────────────
def fetch_page(api_key, url, retries=3):
    for attempt in range(retries):
        try:
            resp = requests.get(
                "https://app.scrapingbee.com/api/v1/",
                params={
                    "api_key": api_key,
                    "url": url,
                    "stealth_proxy": "true",
                    "country_code": "tw",
                    "render_js": "true",
                    "wait": "5000",
                },
                timeout=180,
            )
            cost = resp.headers.get("Spb-Cost", "?")
            credits_remaining = resp.headers.get("Spb-Available", "?")
            if resp.status_code == 200:
                log(f"    💳 Credits remaining: {credits_remaining} (cost this page: {cost})")
                return resp.text, cost
            log(f"    ⚠ HTTP {resp.status_code} (attempt {attempt+1}) — {url}")
            if resp.status_code == 401:
                log(f"    ⚠ 401 body: {resp.text[:200]}")
        except Exception as e:
            log(f"    ✗ Exception attempt {attempt+1}: {e}")
        time.sleep(2 ** attempt)
    return None, 0

# ── Scanner thread ─────────────────────────────────────────────────────────────
def run_scan(api_key, category_urls, page_from=1, page_to=9):
    total_pages = len(category_urls) * (page_to - page_from + 1)
    with state_lock:
        scan_state.update({"running": True, "logs": [], "results": [],
                           "progress": 0, "flagged_count": 0,
                           "pages_done": 0, "total_pages": total_pages,
                           "error": None})

    all_results = []
    pages_done = 0
    total_credits = 0

    try:
        for cat_url in category_urls:
            clean = cat_url.split("?")[0]
            log(f"\n📂 Category: {clean}")
            seen_in_cat = set()
            cat_flagged = 0

            for page in range(page_from, page_to + 1):
                page_url = f"{clean}?page={page}"
                log(f"  🔍 Fetching page {page}/{page_to} …")

                html, cost = fetch_page(api_key, page_url)
                try:
                    total_credits += int(cost)
                except:
                    pass

                pages_done += 1
                with state_lock:
                    scan_state["pages_done"] = pages_done
                    scan_state["progress"] = int(pages_done / total_pages * 100)

                if html is None:
                    log(f"    ✗ Failed after retries — skipping page {page}")
                    continue

                products = extract_flagged_products(html, clean)
                new_on_page = 0
                for p in products:
                    if p["url"] not in seen_in_cat:
                        seen_in_cat.add(p["url"])
                        all_results.append(p)
                        new_on_page += 1
                        cat_flagged += 1

                log(f"    ✅ Page {page}: {html.count('High18')} badge(s) found, {new_on_page} new unique")

                with state_lock:
                    scan_state["results"] = list(all_results)
                    scan_state["flagged_count"] = len(all_results)

                delay = random.uniform(1.0, 2.0)
                time.sleep(delay)

            log(f"  → Category total: {cat_flagged} flagged products")

        log(f"\n✅ Scan complete! Total flagged: {len(all_results)} | Credits used: ~{total_credits}")

    except Exception as e:
        with state_lock:
            scan_state["error"] = str(e)
        log(f"\n✗ Scan error: {e}")

    finally:
        with state_lock:
            scan_state["running"] = False

# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start_scan():
    data = request.json
    api_key = data.get("api_key", "").strip()
    # Fall back to environment variable if not provided in UI
    if not api_key:
        api_key = os.environ.get("SCRAPINGBEE_API_KEY", "")
    urls_raw = data.get("urls", "").strip()

    if not api_key:
        return jsonify({"error": "ScrapingBee API key is required"}), 400

    # Debug: log first/last 4 chars of key to verify it's arriving
    key_preview = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "too_short"
    print(f"[DEBUG] API key received: {key_preview} (len={len(api_key)})")

    category_urls = [u.strip() for u in urls_raw.splitlines() if u.strip()]
    if not category_urls:
        return jsonify({"error": "At least one category URL is required"}), 400

    page_from = max(1, min(9, int(data.get("page_from", 1))))
    page_to   = max(1, min(9, int(data.get("page_to", 9))))
    if page_from > page_to:
        page_from, page_to = page_to, page_from

    with state_lock:
        if scan_state["running"]:
            return jsonify({"error": "Scan already running"}), 400

    t = threading.Thread(target=run_scan, args=(api_key, category_urls, page_from, page_to), daemon=True)
    t.start()
    return jsonify({"ok": True, "pages": len(category_urls) * (page_to - page_from + 1)})

@app.route("/status")
def status():
    with state_lock:
        return jsonify({
            "running": scan_state["running"],
            "progress": scan_state["progress"],
            "pages_done": scan_state["pages_done"],
            "total_pages": scan_state["total_pages"],
            "flagged_count": scan_state["flagged_count"],
            "logs": list(scan_state["logs"]),
            "results": list(scan_state["results"]),
            "error": scan_state["error"],
        })

@app.route("/reset", methods=["POST"])
def reset():
    with state_lock:
        scan_state.update({"running": False, "logs": [], "results": [],
                           "progress": 0, "flagged_count": 0,
                           "pages_done": 0, "total_pages": 0, "error": None})
    return jsonify({"ok": True})

@app.route("/download")
def download():
    with state_lock:
        results = list(scan_state["results"])

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["name", "url", "category_url"])
    writer.writeheader()
    writer.writerows(results)
    buf.seek(0)

    return send_file(
        io.BytesIO(buf.read().encode("utf-8-sig")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"coupang_18plus_flagged_{int(time.time())}.csv",
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000)
