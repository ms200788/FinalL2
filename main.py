import os
import secrets
import string
import asyncio
import urllib.parse
import urllib.request
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")

TXT_FILE = "database.txt"
lock = asyncio.Lock()

# ================= UTILS =================
def gen_code(length=6):
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))

async def save_funnel(final_url, target_url):
    async with lock:
        with open(TXT_FILE, "a") as f:
            f.write(f"{final_url}|{target_url}\n")

async def get_target(final_url):
    async with lock:
        if not os.path.exists(TXT_FILE):
            return None
        with open(TXT_FILE, "r") as f:
            for line in f:
                parts = line.strip().split("|", 1)
                if len(parts) == 2 and parts[0] == final_url:
                    return parts[1]
    return None

# ================= TELEGRAM =================
async def send_message(chat_id, text):
    if not BOT_TOKEN:
        return
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text
    }).encode()
    try:
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=data,
            timeout=10
        )
    except:
        pass

# ================= SELF PING =================
async def self_ping():
    await asyncio.sleep(10)
    if not BASE_URL:
        return
    while True:
        try:
            urllib.request.urlopen(f"{BASE_URL}/health", timeout=10)
        except:
            pass
        await asyncio.sleep(300)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(self_ping())

# ================= HEALTH =================
@app.get("/health")
async def health():
    return {"status": "alive"}

# ================= WEBHOOK =================
@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()

    if "message" not in data:
        return {"ok": True}

    message = data["message"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")

    if user_id != OWNER_ID:
        await send_message(chat_id, "Not authorized.")
        return {"ok": True}

    if text.startswith("/create"):
        parts = text.split(" ", 1)
        if len(parts) != 2:
            await send_message(chat_id, "Usage:\n/create https://example.com")
            return {"ok": True}

        target = parts[1].strip()

        slug = gen_code()
        r_code = gen_code()
        k_code = gen_code()
        u_code = gen_code()

        final_url = f"{BASE_URL}/u/{u_code}/k/{k_code}/r/{r_code}/{slug}"

        await save_funnel(final_url, target)

        # ✅ Channel receives ONLY final|target
        if CHANNEL_ID:
            await send_message(CHANNEL_ID, f"{final_url}|{target}")

        # ✅ Owner gets entrance + final
        await send_message(chat_id, f"""
Funnel Created ✅

User Link:
{BASE_URL}/{slug}

Final Link:
{final_url}
""")

    return {"ok": True}

# ================= STEP 1 =================
@app.get("/{slug}", response_class=HTMLResponse)
async def entrance(slug: str):
    return f"""
    <html>
    <body style="font-family:Arial;text-align:center;padding-top:100px;">
    <h2>Welcome</h2>
    <p>Secure gateway initialized.</p>
    <a href="#" onclick="history.forward()"></a>
    </body>
    </html>
    """

# ================= STEP 2 =================
@app.get("/r/{r_code}/{slug}", response_class=HTMLResponse)
async def step2(r_code: str, slug: str):
    return f"""
    <html>
    <body style="font-family:Arial;text-align:center;padding-top:100px;">
    <h2>Verification Step</h2>
    <a href="/k/{gen_code()}/r/{r_code}/{slug}">
    <button style="padding:12px 25px;">Continue</button>
    </a>
    </body>
    </html>
    """

# ================= STEP 3 =================
@app.get("/k/{k_code}/r/{r_code}/{slug}", response_class=HTMLResponse)
async def step3(k_code: str, r_code: str, slug: str):
    return f"""
    <html>
    <body style="font-family:Arial;text-align:center;padding-top:100px;">
    <h2>Final Step</h2>
    <a href="/u/{gen_code()}/k/{k_code}/r/{r_code}/{slug}">
    <button style="padding:12px 25px;">Continue</button>
    </a>
    </body>
    </html>
    """

# ================= FINAL =================
@app.get("/u/{u_code}/k/{k_code}/r/{r_code}/{slug}")
async def final(u_code: str, k_code: str, r_code: str, slug: str):

    final_url = f"{BASE_URL}/u/{u_code}/k/{k_code}/r/{r_code}/{slug}"

    target = await get_target(final_url)

    if target:
        return RedirectResponse(target)

    return HTMLResponse("Invalid", status_code=403)