<<<<<<< HEAD
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
=======
# Coupang TW · 18+ Badge Scanner

Detects products on Coupang TW category pages where the thumbnail is replaced by the `High18.png` age-gate placeholder.

---

## 🚀 Deploy on Render (for teammates)

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/coupang-18plus-scanner.git
git push -u origin main
```

### Step 2 — Create a Render Web Service

1. Go to [render.com](https://render.com) → **New** → **Web Service**
2. Connect your GitHub repo
3. Render will auto-detect `render.yaml` — confirm the settings:
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --workers 1 --threads 4 --timeout 300`
4. Under **Environment** → add:
   ```
   SCRAPINGBEE_API_KEY = your_key_here
   ```
5. Click **Deploy**

Your team can now access the dashboard at the Render URL (e.g. `https://coupang-18plus-scanner.onrender.com`).

> **Note:** The free Render tier spins down after 15 min of inactivity. Use the **Starter** plan ($7/mo) for always-on access, or just wake it up before a scan.

---

## 💻 Run Locally

```bash
pip install -r requirements.txt
python app.py
```

Open: **http://127.0.0.1:5000**

Or on Windows, double-click `run.bat`.

---

## Usage

1. Open the dashboard URL
2. Enter your **ScrapingBee API key** (or set `SCRAPINGBEE_API_KEY` env var on Render — then leave the field blank)
3. Paste **category URLs**, one per line
4. Click **Start Scan**
5. Watch the live log on the right
6. Click **Download CSV** when done

---

## Output CSV

| Column | Description |
|--------|-------------|
| `product_name` | Product title from the listing |
| `product_url` | Direct link to the product page |
| `category_url_found_on` | The category page where it was detected |

Deduplicated per category. Pages 1–9 scanned per URL.

---

## Cost (ScrapingBee)

| Setting | Value |
|---------|-------|
| Proxy mode | Stealth proxy |
| JS rendering | On + 5s wait |
| Cost per page | ~75 credits |
| Cost per category (9 pages) | ~675 credits |

---

## Files

```
├── app.py               Flask backend + scanner logic
├── templates/
│   └── index.html       Dashboard UI
├── requirements.txt     Python dependencies
├── render.yaml          Render deployment config
├── run.bat              Windows local launcher
└── README.md
```
>>>>>>> 0e643496f81c65e78f44eff2a97648c645b7662b
