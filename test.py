import requests
from bs4 import BeautifulSoup
import re
import time
import json
import os

WEBHOOK_URL = "https://discord.com/api/webhooks/1493321874522898652/XJOBmy53KKF3msCUcnHkorqRv-oG4VHOIRojfEVeWrx_C-0kW0ioWmEej8v33Kx2TyTK"
MIN_PRICE = 2500
MAX_PRICE = 4000
BASE_URL = "https://gigatron.rs"
START_URL = BASE_URL + "/racunari-i-komponente/periferije/misevi"
SEEN_FILE = "seen.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "sr-RS,sr;q=0.9",
}


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def parse_price(text):
    text = re.sub(r'[Uu]šteda.*', '', text)
    text = re.sub(r',\d+', '', text)
    parts = re.split(r'RSD', text)
    prices = []
    for part in parts:
        digits = re.sub(r'[.\s\xa0]', '', part)
        digits = re.sub(r'[^\d]', '', digits)
        if digits:
            val = int(digits)
            if 100 <= val <= 500_000:
                prices.append(val)
    return prices[-1] if prices else None


def scrape_page(url, seen):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    deals = []

    for a in soup.find_all("a", href=re.compile(r'^/proizvod/')):
        name = a.get_text(strip=True)
        if not name or len(name) < 3:
            continue

        price_text = ""
        for sibling in a.next_siblings:
            sibling_text = sibling.get_text(strip=True) if hasattr(sibling, 'get_text') else str(sibling).strip()
            if not sibling_text:
                continue
            if "RSD" in sibling_text:
                price_text = sibling_text
                break
            if hasattr(sibling, 'name') and sibling.name == 'a' and sibling.get('href', '').startswith('/proizvod/'):
                break

        if not price_text:
            continue

        price = parse_price(price_text)
        if price is None:
            continue

        if not (MIN_PRICE <= price <= MAX_PRICE):
            continue

        href = a["href"]
        if href in seen:
            continue
        seen.add(href)

        product_url = BASE_URL + href
        deals.append(f"🖱 **{name}**\n💸 {price:,} RSD\n🔗 {product_url}".replace(",", "."))

    return deals


def send(deals):
    if not deals:
        print("No new deals found.")
        return
    header = f"🔥 **NEW DEALS ({MIN_PRICE}–{MAX_PRICE} RSD)**\n\n"
    chunk, char_count = [], 0
    for deal in deals:
        if char_count + len(deal) > 1800:
            requests.post(WEBHOOK_URL, json={"content": header + "\n\n".join(chunk)})
            chunk, char_count = [], 0
            time.sleep(1)
        chunk.append(deal)
        char_count += len(deal)
    if chunk:
        requests.post(WEBHOOK_URL, json={"content": header + "\n\n".join(chunk)})
    print(f"✅ Sent {len(deals)} deal(s).")


def run():
    seen = load_seen()
    print(f"  Scraping {START_URL}")
    try:
        deals = scrape_page(START_URL, seen)
        save_seen(seen)
        print(f"  → {len(deals)} new deal(s)")
        send(deals)
    except Exception as e:
        import traceback
        print(f"  ✗ Error: {e}")
        traceback.print_exc()


print(f"\n🔄 Scanning gigatron.rs mice {MIN_PRICE}–{MAX_PRICE} RSD...")
run()