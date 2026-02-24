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


# ================= UNIQUE GENERATOR =================
async def generate_unique_slug():
    while True:
        slug = gen_code(6)
        async with lock:
            if slug not in funnels:
                return slug


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

        slug = await generate_unique_slug()
        r_code = gen_code(6)
        k_code = gen_code(6)
        u_code = gen_code(6)

        await save_funnel(slug, r_code, k_code, u_code, link)

        # 🔥 Send FULL details to CHANNEL only
        if CHANNEL_ID:
            await send_message(CHANNEL_ID, f"""
{slug}|{r_code}|{k_code}|{u_code}|{link}
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
        <html lang="en">
<head>
<meta charset="UTF-8">
<title>Crypto Wealth</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body {{ font-family: Arial; line-height:1.8; margin:0; background:#0f2027; color:#eaeaea; }}
h1,h2,h3,h4 {{ color:#4da3ff; }}
.section {{ background:#fff; padding:25px; margin-bottom:30px; border-left:6px solid #4da3ff; }}
.card {{ background:#fff; color:#000; border-radius:16px; padding:20px; margin:16px; }}
.btn {{ background:#fff; color:#4da3ff; border:none; padding:14px; width:100%; border-radius:30px; font-size:16px; cursor:pointer; }}
.timer {{ text-align:center; font-size:16px; margin:20px 0; }}
.conclusion {{ background:#f0f3ff; padding:20px; border-left:5px solid #4a63ff; border-radius:12px; }}
.topbar {{ background:#121212; color:#fff; padding:12px 16px; font-size:20px; font-weight:700; }}
.highlight {{ background:#eef4ff; padding:15px; border-radius:10px; margin-top:10px; }}
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
            document.getElementById("timerText").innerText="Scroll down to Verify";
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

<div class="topbar">Crypto Wealth</div>

<div class="card">

<h1>𝗛𝗼𝘄 𝗦𝗺𝗮𝗿𝘁 𝗜𝗻𝘃𝗲𝘀𝘁𝗼𝗿𝘀 𝗕𝘂𝗶𝗹𝗱 𝗪𝗲𝗮𝗹𝘁𝗵 𝘄𝗶𝘁𝗵 𝗖𝗿𝘆𝗽𝘁𝗼 𝗶𝗻 𝟮𝟬𝟮𝟲</h1>

<div class="timer">
<p id="timerText">Please wait <b id="t">20</b> seconds.We are loading...</p>
</div>



<div class="section">
<h2>The New Digital Gold Rush</h2>
<p>Cryptocurrency has transformed from a niche internet experiment into a global financial revolution. Millions of people worldwide are exploring digital assets as a way to build wealth, diversify income, and escape traditional financial limitations.</p>
<p>Unlike traditional markets that close on weekends or holidays, crypto operates 24/7. This constant activity creates opportunities at any hour of the day. For individuals willing to learn, this ecosystem offers flexibility that traditional finance simply cannot match.</p>
<p>The rapid rise of blockchain adoption, decentralized applications, and token-based economies has created a new digital gold rush. Early movers in innovative sectors often benefit the most, but even today, new projects and technologies are constantly emerging.</p>
</div>

<div class="section">
<h2>Understanding Blockchain Technology</h2>
<p>At the core of cryptocurrency lies blockchain technology — a decentralized ledger that records transactions securely and transparently. Instead of relying on banks or central authorities, blockchain networks validate transactions through distributed consensus.</p>
<p>This transparency builds trust. Every transaction is recorded publicly, reducing fraud and manipulation risks. Because of this, industries beyond finance — including gaming, real estate, healthcare, and supply chains — are exploring blockchain integration.</p>
<p>As adoption grows, long-term investors often position themselves in projects that provide real utility and solve meaningful problems.</p>
</div>

<div class="section">
<h2>Why Crypto Attracts Smart Investors</h2>
<ul>
<li>24/7 global market access</li>
<li>High volatility = high opportunity</li>
<li>Decentralized systems outside traditional banks</li>
<li>Fast-growing innovation in blockchain technology</li>
<li>Borderless financial transactions</li>
<li>Low barriers to entry compared to traditional investing</li>
</ul>
<div class="highlight">
Smart investors don’t rely on luck — they rely on strategy, risk management, and timing.
</div>
</div>

<div class="section">
<h2>Top Ways to Earn with Crypto</h2>

<h3>1. Long-Term Holding (HODL)</h3>
<p>Buying fundamentally strong projects and holding through market cycles remains one of the simplest wealth-building methods. Historically, long-term patience has rewarded disciplined investors.</p>

<h3>2. Swing & Day Trading</h3>
<p>Short-term price movements create opportunities for active traders. Using technical analysis, support/resistance zones, and volume indicators can improve decision-making.</p>

<h3>3. Staking & Passive Income</h3>
<p>Proof-of-stake networks allow users to earn rewards simply by holding and validating transactions. This creates passive yield streams that compound over time.</p>

<h3>4. Yield Farming & DeFi</h3>
<p>Decentralized finance platforms offer lending and liquidity rewards. While returns can be attractive, smart investors evaluate smart contract risks carefully.</p>

<h3>5. Affiliate & Referral Programs</h3>
<p>Many crypto platforms provide referral incentives. Content creators and marketers can build additional revenue streams by educating others about digital finance.</p>

</div>

<div class="section">
<h2>Risk Management Secrets</h2>
<p>Crypto markets are volatile. Smart investors never risk more than they can afford to lose. They diversify across assets, avoid emotional trading, and follow clear entry and exit plans.</p>
<ul>
<li>Never invest borrowed money</li>
<li>Always use secure hardware wallets</li>
<li>Research tokenomics before investing</li>
<li>Use stop-loss strategies</li>
<li>Avoid impulsive FOMO buying</li>
<li>Take profits gradually instead of chasing peaks</li>
</ul>
<p>Professional investors treat risk management as their first priority — not profit chasing.</p>
</div>

<div class="section">
<h2>The Psychology of Wealth Building</h2>
<p>Financial markets test emotional discipline. Fear during market dips causes panic selling, while greed during rallies leads to overexposure. Successful investors maintain calm decision-making processes.</p>
<p>Keeping a trading journal, defining strategies in advance, and limiting screen time during extreme volatility can help maintain objectivity.</p>
<p>Wealth building is rarely about one lucky trade. It is about consistent, repeatable processes applied over months and years.</p>
</div>

<div class="section">
<h2>Emerging Trends in 2026</h2>
<ul>
<li>AI-powered trading bots</li>
<li>Tokenized real-world assets</li>
<li>Institutional crypto adoption</li>
<li>Decentralized finance (DeFi) expansion</li>
<li>Blockchain gaming economies</li>
<li>Central Bank Digital Currencies (CBDCs)</li>
</ul>
<p>These developments continue reshaping how money moves globally. Institutional participation adds credibility and liquidity to the market.</p>
</div>

<div class="section">
<h2>Building a Long-Term Strategy</h2>
<p>Successful crypto investors treat it like a business. They track performance metrics, rebalance portfolios periodically, and reinvest profits wisely.</p>
<p>A diversified strategy might include a mix of established cryptocurrencies, promising mid-cap projects, and small allocations to higher-risk innovations.</p>
<p>Continuous education remains critical. Markets evolve rapidly, and informed investors adapt accordingly.</p>
</div>

<div class="section">
<h2>Financial Freedom & Digital Assets</h2>
<p>For many people, cryptocurrency represents more than profits — it symbolizes financial independence. Borderless transactions allow individuals to move capital freely without excessive restrictions.</p>
<p>While risks remain, the long-term potential of decentralized finance continues attracting global attention.</p>
<p>Those who approach crypto with patience, research, and discipline often find themselves better prepared for future financial systems.</p>
</div>

<div class="conclusion">
<h2>Final Thoughts</h2>
<p>Crypto is not a get-rich-quick scheme — it is a dynamic financial ecosystem full of opportunity for those willing to learn and adapt.</p>
<p>Success requires strategy, patience, and strong risk management. With consistent effort and smart decision-making, digital assets can become a powerful wealth-building tool in 2026 and beyond.</p>
<p>Start small. Stay disciplined. Think long-term.</p>
</div>

</div>

<div id="verifyBox" style="display:none; margin:16px;">
<button class="btn" onclick="verifyNow()">𝗩𝗲𝗿𝗶𝗳𝘆 𝗡𝗼𝘄</button>
</div>

<div id="continueBox" style="display:none; margin:16px;">
    <a href="/r/{r_code}/{slug}">
<button class="btn">𝗖𝗼𝗻𝘁𝗶𝗻𝘂𝗲</button>
</a>
</div>

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