import os
import secrets
import string
import asyncio
import urllib.parse
import urllib.request
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")

TXT_FILE = "database.txt"

funnels = {}
lock = asyncio.Lock()

# ================= LOAD DATA =================
if os.path.exists(TXT_FILE):
    with open(TXT_FILE, "r") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) == 5:
                slug, r_code, k_code, u_code, link = parts
                funnels[slug] = (r_code, k_code, u_code, link)

# ================= UTILS =================
def gen_code(length=6):
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))

async def save_funnel(slug, r_code, k_code, u_code, link):
    async with lock:
        funnels[slug] = (r_code, k_code, u_code, link)
        with open(TXT_FILE, "a") as f:
            f.write(f"{slug}|{r_code}|{k_code}|{u_code}|{link}\n")

async def get_funnel(slug):
    async with lock:
        return funnels.get(slug)

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
    await asyncio.sleep(10)  # wait for server to fully start
    if not BASE_URL:
        print("BASE_URL not set. Self ping disabled.")
        return

    while True:
        try:
            urllib.request.urlopen(f"{BASE_URL}/health", timeout=10)
            print("Self ping success")
        except Exception as e:
            print("Self ping failed:", e)

        await asyncio.sleep(300)  # 5 minutes

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

        link = parts[1].strip()

        slug = gen_code(6)
        r_code = gen_code(6)
        k_code = gen_code(6)
        u_code = gen_code(6)

        await save_funnel(slug, r_code, k_code, u_code, link)

        # 🔥 Send FULL details to CHANNEL only
        if CHANNEL_ID:
            await send_message(CHANNEL_ID, f"""
{slug}|{r_code}|{k_code}|{u_code}|{link}
Final: {BASE_URL}/u/{u_code}/k/{k_code}/r/{r_code}/{slug}
""")

        # ✅ Owner gets ONLY entrance + final
        await send_message(chat_id, f"""
Funnel Created ✅

User Link:
{BASE_URL}/{slug}

Final Redirect:
{BASE_URL}/u/{u_code}/k/{k_code}/r/{r_code}/{slug}
""")

    return {"ok": True}

# ================= STEP 1 =================
@app.get("/{slug}", response_class=HTMLResponse)
async def entrance(slug: str):
    funnel = await get_funnel(slug)
    if not funnel:
        return HTMLResponse("Not Found", status_code=404)

    r_code = funnel[0]

    return f"""
    <html>
    <body style="font-family:Arial;text-align:center;padding-top:100px;">
    <h2>Welcome</h2>
    <p>Secure gateway initialized.</p>
    <a href="/r/{r_code}/{slug}">
    <button style="padding:12px 25px;font-size:16px;">Continue</button>
    </a>
    </body>
    </html>
    """

# ================= STEP 2 =================
@app.get("/r/{r_code}/{slug}", response_class=HTMLResponse)
async def step2(r_code: str, slug: str):
    funnel = await get_funnel(slug)
    if not funnel or funnel[0] != r_code:
        return HTMLResponse("Invalid", status_code=403)

    k_code = funnel[1]

    return f"""
    <html>
    <body style="font-family:Arial;text-align:center;padding-top:100px;">
    <h2>Verification Step</h2>
    <p>Access check in progress.</p>
    <a href="/k/{k_code}/r/{r_code}/{slug}">
    <button style="padding:12px 25px;font-size:16px;">Continue</button>
    </a>
    </body>
    </html>
    """

# ================= STEP 3 =================
@app.get("/k/{k_code}/r/{r_code}/{slug}", response_class=HTMLResponse)
async def step3(k_code: str, r_code: str, slug: str):
    funnel = await get_funnel(slug)
    if not funnel or funnel[0] != r_code or funnel[1] != k_code:
        return HTMLResponse("Invalid", status_code=403)

    u_code = funnel[2]

    return f"""
    <html>
    <body style="font-family:Arial;text-align:center;padding-top:100px;">
    <h2>Final Step</h2>
    <p>Click continue to proceed.</p>
    <a href="/u/{u_code}/k/{k_code}/r/{r_code}/{slug}">
    <button style="padding:12px 25px;font-size:16px;">Continue</button>
    </a>
    </body>
    </html>
    """

# ================= FINAL =================
@app.get("/u/{u_code}/k/{k_code}/r/{r_code}/{slug}")
async def final(u_code: str, k_code: str, r_code: str, slug: str):
    funnel = await get_funnel(slug)
    if not funnel:
        return HTMLResponse("Invalid", status_code=403)

    if funnel[0] == r_code and funnel[1] == k_code and funnel[2] == u_code:
        return RedirectResponse(funnel[3])

    return HTMLResponse("Invalid", status_code=403)