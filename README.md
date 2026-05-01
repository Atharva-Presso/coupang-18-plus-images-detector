# Coupang TW · 18+ Badge Scanner Dashboard

Local web dashboard to detect Coupang TW products where the PLP image is replaced by the High18.png age-gate placeholder.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the dashboard:
   ```
   python app.py
   ```
   Or double-click `run.bat` on Windows.

3. Open browser to: **http://127.0.0.1:5000**

## Usage

1. Paste your ScrapingBee API key (or set `SCRAPINGBEE_API_KEY` env var before launch)
2. Paste category URLs in the textarea, one per line
3. Click "Start Scan"
4. Watch live log on the right
5. Click "Download CSV" when done

## Output

CSV columns:
- `product_name`
- `product_url`
- `category_url_found_on`

Deduplicated per category. Pages 1 to 9 scanned per URL.

## Cost

Each page = 75 ScrapingBee credits (stealth_proxy + render_js + 5s wait).
Each category = 9 pages = 675 credits.

## Files

- `app.py` — Flask backend
- `templates/index.html` — frontend UI
- `requirements.txt` — Python dependencies
- `run.bat` — Windows launcher
