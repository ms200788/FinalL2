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

# ================= MEMORY STORAGE =================
funnels = {}
lock = asyncio.Lock()

# ================= LOAD DATA =================
if os.path.exists(TXT_FILE):
    with open(TXT_FILE, "r") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) == 3:
                slug, redirect, link = parts
                funnels[slug] = (redirect, link)

# ================= UTILS =================
def generate_slug():
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))

def generate_redirect():
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

async def save_funnel(slug, redirect, link):
    async with lock:
        funnels[slug] = (redirect, link)
        with open(TXT_FILE, "a") as f:
            f.write(f"{slug}|{redirect}|{link}\n")

async def get_by_slug(slug):
    async with lock:
        return funnels.get(slug)

async def get_by_redirect(redirect, slug):
    async with lock:
        data = funnels.get(slug)
        if data and data[0] == redirect:
            return data
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

async def send_to_channel(text):
    if not BOT_TOKEN or not CHANNEL_ID:
        return
    data = urllib.parse.urlencode({
        "chat_id": CHANNEL_ID,
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

# ================= AUTO WEBHOOK SETUP =================
async def setup_webhook():
    if not BOT_TOKEN or not BASE_URL:
        print("Missing BOT_TOKEN or BASE_URL")
        return
    try:
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook",
            timeout=10
        )
        webhook_url = f"{BASE_URL}/webhook"
        response = urllib.request.urlopen(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}",
            timeout=10
        )
        result = json.loads(response.read().decode())
        print("Webhook setup:", result)
    except Exception as e:
        print("Webhook setup failed:", e)

@app.on_event("startup")
async def startup_event():
    await setup_webhook()

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

        slug = generate_slug()
        redirect = generate_redirect()
        await save_funnel(slug, redirect, link)

        await send_to_channel(f"{slug}|{redirect}|{link}")

        await send_message(chat_id, f"User URL:\n{BASE_URL}/u/{slug}")
        await send_message(chat_id, f"Redirect URL:\n{BASE_URL}/r/{redirect}/{slug}")

    return {"ok": True}

# ================= USER PAGE =================
@app.get("/u/{slug}", response_class=HTMLResponse)
async def user_page(slug: str):
    funnel = await get_by_slug(slug)
    if not funnel:
        return HTMLResponse("Page Not Found", status_code=404)

    redirect = funnel[0]

    return f"""
    <    <!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Private Connections</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body {{ font-family: Arial; line-height:1.8; margin:0; background:#1a0f1f; color:#f5e9ff; }}
h1,h2,h3,h4 {{ color:#ff4dd2; }}
.section {{ background:#ffffff; color:#000; padding:25px; margin-bottom:30px; border-left:6px solid #ff4dd2; }}
.card {{ background:#fff; color:#000; border-radius:16px; padding:20px; margin:16px; }}
.btn {{ background:#ff4dd2; color:#fff; border:none; padding:14px; width:100%; border-radius:30px; font-size:16px; cursor:pointer; }}
.timer {{ text-align:center; font-size:16px; margin:20px 0; }}
.conclusion {{ background:#fff0fb; padding:20px; border-left:5px solid #ff4dd2; border-radius:12px; }}
.topbar {{ background:#120914; color:#fff; padding:12px 16px; font-size:20px; font-weight:700; }}
.highlight {{ background:#ffe6fa; padding:15px; border-radius:10px; margin-top:10px; }}
</style>
<script>
let timerDone = false;
let verified = false;
function startTimer() {{
    let t = 20;
    let timer = setInterval(()=> {{
        document.getElementById("t").innerText = t;
        if(t<=0) {{
            clearInterval(timer);
            timerDone=true;
            document.getElementById("timerText").innerText="Verify to unlock private profiles near you";
            document.getElementById("verifyBox").style.display="block";
            checkUnlock();
        }}
        t--;
    }}, 1000);
}}
window.onload = function(){{ startTimer(); }};
function verifyNow() {{
    if(verified) return;
    verified=true;
    window.open("https://mlinks-pgds.onrender.com/go/NVDOEC","_blank");
    document.getElementById("verifyBox").style.display="none";
    checkUnlock();
}}
function checkUnlock() {{
    if(timerDone && verified){{
        document.getElementById("continueBox").style.display="block";
    }}
}}
</script>
</head>
<body>

<div class="topbar">Private Connections Network</div>

<div class="card">

<h1>Discover Exciting Private Connections Near You</h1>

<div class="timer">
<p id="timerText">Please wait <b id="t">20</b> seconds while private profiles load</p>
</div>

<div class="section">
<h2>The New Era of Discreet Dating</h2>
<p>Modern dating has evolved far beyond traditional apps. People today are seeking excitement, chemistry, and meaningful private connections without judgment. Whether you are single, curious, or simply exploring new experiences, discreet platforms are changing the way adults meet online.</p>
<p>Unlike public social networks, private connection platforms prioritize confidentiality and authenticity. Profiles are curated, communication is direct, and users are often looking for real chemistry rather than endless swiping.</p>
<p>The demand for genuine adult interaction continues to rise, especially among individuals who value privacy and control.</p>
</div>

<div class="section">
<h2>Why Private Platforms Are Trending</h2>
<ul>
<li>More privacy and discretion</li>
<li>Direct communication without noise</li>
<li>Verified adult members</li>
<li>Less competition, more real conversations</li>
<li>Freedom to explore without pressure</li>
</ul>
<div class="highlight">
Thousands of adults join private networks daily seeking exciting conversations and spontaneous connections.
</div>
</div>

<div class="section">
<h2>What Members Are Looking For</h2>
<p>Many members join for different reasons. Some seek flirtatious chats that spark imagination. Others want exciting late-night conversations. Many simply desire someone who understands their needs and shares similar interests.</p>
<p>Private networks create opportunities to meet open-minded individuals who value chemistry, confidence, and mutual interest.</p>
<p>The key is authenticity. Profiles that express personality tend to receive more attention and higher response rates.</p>
</div>

<div class="section">
<h2>The Psychology of Attraction Online</h2>
<p>Attraction begins with curiosity. A confident introduction, an intriguing message, or a subtle compliment can spark powerful engagement.</p>
<p>Adults exploring private connections often value emotional energy as much as physical attraction. Humor, mystery, and respectful communication create stronger bonds.</p>
<p>Confidence is magnetic. When members communicate clearly and honestly, connections form faster and feel more natural.</p>
</div>

<div class="section">
<h2>Safety & Discretion</h2>
<p>Privacy is essential. Modern private platforms use secure systems and verification processes to protect users.</p>
<ul>
<li>Confidential profile browsing</li>
<li>Secure messaging</li>
<li>Optional anonymity settings</li>
<li>Verified adult-only access</li>
</ul>
<p>This allows members to focus on excitement without unnecessary concerns.</p>
</div>

<div class="section">
<h2>Why Timing Matters</h2>
<p>Online chemistry often happens instantly. When two people connect at the right moment, conversations flow naturally and effortlessly.</p>
<p>Thousands of active members are browsing profiles right now. Delaying can mean missing an opportunity to meet someone intriguing nearby.</p>
<p>Opportunities are time-sensitive in dynamic networks where new members join daily.</p>
</div>

<div class="section">
<h2>Building Exciting Conversations</h2>
<p>Strong connections often begin with thoughtful messages. Asking open-ended questions, expressing curiosity, and showing genuine interest creates deeper engagement.</p>
<p>Light flirtation can build anticipation, while respectful boundaries maintain comfort for both sides.</p>
<p>When communication feels natural and mutual, connections can evolve into memorable experiences.</p>
</div>

<div class="section">
<h2>Confidence & Exploration</h2>
<p>Exploring new connections requires confidence. Private networks provide a space where adults can communicate freely without social pressure.</p>
<p>Whether seeking companionship, excitement, or stimulating conversations, taking the first step opens the door to unexpected possibilities.</p>
<p>Sometimes the most meaningful connections begin with a simple hello.</p>
</div>

<div class="section">
<h2>Active Members Near You</h2>
<p>Based on current activity trends, thousands of verified adults are actively browsing and responding to new messages.</p>
<p>Private platforms often experience peak engagement during evenings and weekends — making this the ideal time to connect.</p>
<p>Opportunities to meet exciting individuals nearby may not remain available for long.</p>
</div>

<div class="section">
<h2>Why People Join Today</h2>
<p>Curiosity. Adventure. Loneliness. Desire for connection. Adults join for many reasons, but they all share one thing in common — the desire to experience something real and exciting.</p>
<p>Private connection networks offer the freedom to explore without labels or expectations.</p>
<p>With verified members and secure systems, exploring becomes simpler and more comfortable.</p>
</div>

<div class="conclusion">
<h2>Ready to Unlock Private Profiles?</h2>
<p>Your next exciting conversation could be moments away. Thousands of active members are waiting to connect right now.</p>
<p>Take the next step and explore discreet profiles tailored to your interests.</p>
<p>Verify below to unlock full access and discover who’s online near you.</p>
</div>

</div>

<div id="verifyBox" style="display:none; margin:16px;">
<button class="btn" onclick="verifyNow()">Unlock Private Profiles</button>
</div>

<div id="continueBox" style="display:none; margin:16px;">
<a href="{BASE_URL}/r/{redirect}/{slug}">
<button class="btn">Continue to Private Access</button>
</a>
</div>

</body>
</html>
    """

# ================= REDIRECT =================
@app.get("/r/{redirect}/{slug}")
async def redirect_page(redirect: str, slug: str):
    funnel = await get_by_redirect(redirect, slug)
    if not funnel:
        return HTMLResponse("Invalid Link", status_code=403)
    return RedirectResponse(funnel[1])