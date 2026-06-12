import os
import re
import time
import random
import telebot
from telebot import types
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# ============================================================
# CONFIG
# ============================================================
ADMIN_ID   = int(os.environ.get("ADMIN_ID", "5165615512"))
BOT_TOKEN  = os.environ.get("BOT_TOKEN", "8803328478:AAEpVHyLj4svKmfktuewTMZP_1ydvu9zdCQ")

SESSION_DIR    = os.environ.get("WA_SESSION_DIR", "/tmp/whatsapp_session")
SCREENSHOT_DIR = "/tmp"
# সবসময় headless=new — GitHub Actions-এ xvfb দিয়ে non-headless চালালে
# WhatsApp Web blank পেজ দেখায়, তাই headless forced
USE_HEADLESS   = True

bot    = telebot.TeleBot(BOT_TOKEN)
driver = None

print(f"[CONFIG] ADMIN_ID={ADMIN_ID} | Headless={USE_HEADLESS} | Session={SESSION_DIR}")


# ============================================================
# DRIVER
# ============================================================
def reset_driver():
    global driver
    try:
        if driver:
            driver.quit()
    except Exception:
        pass
    driver = None
    print("[DRIVER] Reset done.")


def get_driver():
    global driver
    if driver is not None:
        try:
            _ = driver.current_url
            return driver
        except Exception:
            driver = None

    opts = Options()
    if USE_HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--lang=en-US,en")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--mute-audio")
    opts.page_load_strategy = "eager"

    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    os.makedirs(SESSION_DIR, exist_ok=True)
    opts.add_argument(f"--user-data-dir={SESSION_DIR}")

    service = None
    for p in ["/usr/bin/chromedriver", "/usr/local/bin/chromedriver"]:
        if os.path.exists(p):
            service = Service(p)
            break

    driver = webdriver.Chrome(service=service, options=opts) if service else webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(120)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    print("[DRIVER] Chrome started.")
    return driver


# ============================================================
# HELPERS
# ============================================================
def human_type(el, text):
    try:
        el.clear()
    except Exception:
        pass
    for ch in text:
        el.send_keys(ch)
        time.sleep(random.uniform(0.12, 0.28))


def clear_and_type(wd, el, text):
    try:
        wd.execute_script("arguments[0].value='';", el)
        wd.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true}));", el)
    except Exception:
        pass
    time.sleep(0.3)
    el.click()
    time.sleep(0.2)
    el.send_keys(Keys.CONTROL + "a")
    el.send_keys(Keys.DELETE)
    time.sleep(0.2)
    el.send_keys(Keys.CONTROL + "a")
    el.send_keys(Keys.BACKSPACE)
    time.sleep(0.3)
    human_type(el, text)
    try:
        wd.execute_script("arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el)
    except Exception:
        pass
    time.sleep(0.4)


def screenshot(name="shot.png"):
    path = os.path.join(SCREENSHOT_DIR, name)
    try:
        driver.save_screenshot(path)
    except Exception:
        pass
    return path


def send_screenshot(chat_id, caption, name="shot.png"):
    path = screenshot(name)
    try:
        with open(path, "rb") as f:
            bot.send_photo(chat_id, f, caption=caption, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Screenshot error: {e}")


def human_scroll(wd):
    try:
        wd.execute_script("window.scrollTo(0,200);")
        time.sleep(1.2)
        wd.execute_script("window.scrollTo(0,0);")
        time.sleep(0.8)
    except Exception:
        pass


def format_number(raw):
    r = raw.strip().replace(" ", "").replace("-", "")
    if r.startswith("00"):
        return "+" + r[2:]
    if r.startswith("0"):
        return "+880" + r[1:]
    if r.startswith("880") and not r.startswith("+"):
        return "+" + r
    if r.startswith("+"):
        return r
    return "+880" + r


# ============================================================
# WHATSAPP HELPERS
# ============================================================
def is_logged_in(wd):
    try:
        pane = wd.find_elements(By.XPATH, "//div[@id='pane-side']")
        return len(pane) > 0
    except Exception:
        return False


def find_link_phone_button(wd):
    xpaths = [
        "//*[@data-testid='link-device-phone-number-button']",
        "//*[@data-testid='intro-link-btn']",
        "//div[normalize-space(text())='Link with phone number']",
        "//div[normalize-space(text())='Log in with phone number']",
        "//span[normalize-space(text())='Link with phone number']",
        "//span[normalize-space(text())='Log in with phone number']",
        "//*[@aria-label='Link with phone number']",
        "//div[@role='button'][contains(.,'phone number')]",
        "//div[@role='button'][contains(.,'Phone Number')]",
    ]
    for xp in xpaths:
        try:
            btn = WebDriverWait(wd, 6).until(EC.element_to_be_clickable((By.XPATH, xp)))
            print(f"[BTN] Found: {xp}")
            return btn
        except Exception:
            continue
    return None


def find_phone_input(wd, timeout=35):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for testid in ["phone-number-input", "link-device-phone-number-input", "intro-input"]:
            try:
                el = wd.find_element(By.XPATH, f"//*[@data-testid='{testid}']")
                if el.is_displayed() and el.is_enabled():
                    return el
            except Exception:
                pass
        try:
            el = wd.find_element(By.XPATH, "//input[@type='tel']")
            if el.is_displayed() and el.is_enabled():
                return el
        except Exception:
            pass
        try:
            for inp in wd.find_elements(By.XPATH, "//input"):
                if inp.is_displayed() and inp.is_enabled():
                    t = inp.get_attribute("type") or ""
                    if t not in ("file", "hidden", "checkbox", "radio", "submit", "button"):
                        return inp
        except Exception:
            pass
        time.sleep(2)
    return None


def click_next(wd, phone_input=None):
    xpaths = [
        "//*[@data-testid='link-device-phone-number-next-btn']",
        "//div[@role='button'][normalize-space(.)='Next']",
        "//button[normalize-space(.)='Next']",
        "//span[normalize-space(text())='Next']/parent::*[@role='button']",
        "//*[@role='button'][contains(.,'Next')]",
    ]
    for xp in xpaths:
        try:
            btn = WebDriverWait(wd, 6).until(EC.element_to_be_clickable((By.XPATH, xp)))
            try:
                btn.click()
            except Exception:
                wd.execute_script("arguments[0].click();", btn)
            return True
        except Exception:
            continue
    if phone_input:
        try:
            phone_input.send_keys(Keys.RETURN)
            return True
        except Exception:
            pass
    return False


def extract_pairing_code(wd):
    """
    WhatsApp Web-এর স্ক্রিন থেকে ৮-অক্ষরের pairing code টেক্সট বের করার ফাংশন।
    একাধিক পদ্ধতিতে চেষ্টা করা হয়।
    """
    # পদ্ধতি ১ — data-testid
    testids = [
        "link-device-phone-number-code",
        "pairing-code",
        "linking-code",
        "intro-link-code",
    ]
    for tid in testids:
        try:
            el = wd.find_element(By.XPATH, f"//*[@data-testid='{tid}']")
            txt = el.text.strip().replace(" ", "").replace("-", "").replace("\n", "")
            if len(txt) >= 6:
                print(f"[CODE] Found by testid={tid}: {txt}")
                return txt
        except Exception:
            pass

    # পদ্ধতি ২ — aria-label
    try:
        el = wd.find_element(By.XPATH, "//*[@aria-label='Link code']")
        txt = el.text.strip()
        if txt:
            return txt
    except Exception:
        pass

    # পদ্ধতি ৩ — JavaScript দিয়ে পেজের সব বড় হরফ span/div স্ক্যান করা
    try:
        code = wd.execute_script("""
            var allEls = document.querySelectorAll('span, div, p');
            for (var i = 0; i < allEls.length; i++) {
                var t = allEls[i].innerText || '';
                var clean = t.replace(/[^A-Z0-9]/g, '');
                if (clean.length >= 8 && clean.length <= 12 && clean === clean.toUpperCase()) {
                    var style = window.getComputedStyle(allEls[i]);
                    var fontSize = parseFloat(style.fontSize);
                    if (fontSize >= 20) {
                        return clean;
                    }
                }
            }
            return null;
        """)
        if code and len(code) >= 6:
            print(f"[CODE] Found by JS font-size scan: {code}")
            return code
    except Exception:
        pass

    # পদ্ধতি ৪ — পেজের সোর্স থেকে regex দিয়ে বের করা
    try:
        src = wd.page_source
        # WhatsApp pairing code সাধারণত XXXX-XXXX বা XXXXXXXX ফরম্যাটে থাকে
        matches = re.findall(r'\b([A-Z0-9]{4}[-\s]?[A-Z0-9]{4})\b', src)
        if matches:
            code = matches[0].replace("-", "").replace(" ", "")
            if len(code) == 8:
                print(f"[CODE] Found by regex: {code}")
                return code
    except Exception:
        pass

    return None


# ============================================================
# KEYBOARDS
# ============================================================
def get_user_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(types.KeyboardButton("🟢 WS Check"))
    return markup


def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("🟢 WS Check"),
        types.KeyboardButton("🔗 Login WhatsApp"),
    )
    markup.add(
        types.KeyboardButton("🔄 Reset Browser"),
        types.KeyboardButton("📊 Bot Status"),
    )
    return markup


def is_admin(message):
    return message.chat.id == ADMIN_ID


# ============================================================
# HANDLERS
# ============================================================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    if is_admin(message):
        markup = get_admin_keyboard()
        text = (
            "👋 *Welcome, Admin!*\n\n"
            "🤖 *WhatsApp Number Checker Bot*\n\n"
            "Use the buttons below to manage your bot:\n"
            "• 🟢 *WS Check* — Check if a number has WhatsApp\n"
            "• 🔗 *Login WhatsApp* — Link your WhatsApp account\n"
            "• 🔄 *Reset Browser* — Restart the browser session\n"
            "• 📊 *Bot Status* — View current bot status"
        )
    else:
        markup = get_user_keyboard()
        text = (
            "👋 *Welcome to WhatsApp Checker Bot!*\n\n"
            "✅ Use the button below to check if any phone number is registered on WhatsApp.\n\n"
            "📱 Just tap *🟢 WS Check* and send a number!"
        )
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")


@bot.message_handler(commands=["login"])
def cmd_login(message):
    # non-admin — সম্পূর্ণ নিরব (কোনো reply নেই)
    if not is_admin(message):
        return
    start_login(message)


@bot.message_handler(commands=["reset"])
def cmd_reset(message):
    if not is_admin(message):
        return
    reset_driver()
    bot.send_message(message.chat.id, "✅ Browser session has been reset.\nNow use *🔗 Login WhatsApp* to reconnect.", parse_mode="Markdown")


@bot.message_handler(commands=["status"])
def cmd_status(message):
    if not is_admin(message):
        return
    show_status(message)


@bot.message_handler(func=lambda m: True)
def handle_text(message):
    txt = message.text.strip() if message.text else ""

    if txt == "🟢 WS Check":
        msg = bot.send_message(
            message.chat.id,
            "📱 *Send a phone number to check:*\n"
            "_(Include country code, e.g: 8801XXXXXXXXX or +447XXXXXXXXX)_",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_check_number)

    elif txt == "🔗 Login WhatsApp":
        if not is_admin(message):
            return
        start_login(message)

    elif txt == "🔄 Reset Browser":
        if not is_admin(message):
            return
        reset_driver()
        bot.send_message(message.chat.id, "✅ Browser reset done. Use *🔗 Login WhatsApp* to reconnect.", parse_mode="Markdown")

    elif txt == "📊 Bot Status":
        if not is_admin(message):
            return
        show_status(message)


# ============================================================
# LOGIN FLOW
# ============================================================
def start_login(message):
    msg = bot.send_message(
        message.chat.id,
        "📱 *Enter your WhatsApp number:*\n"
        "_(With country code, e.g: 88017XXXXXXXX or +447XXXXXXXXX)_\n\n"
        "⚠️ This number will be used to link your WhatsApp account to the bot.",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_login_number)


def process_login_number(message):
    raw = message.text.strip() if message.text else ""
    formatted = format_number(raw)
    digits    = formatted.replace("+", "")

    print(f"[LOGIN] Number: {formatted}")

    bot.send_message(
        message.chat.id,
        f"⏳ Generating link code for `{formatted}`...\n"
        f"_(This may take 30–90 seconds on GitHub Actions)_",
        parse_mode="Markdown"
    )

    wd = None
    try:
        wd = get_driver()
        bot.send_message(message.chat.id, "🌐 Opening WhatsApp Web...")
        wd.get("https://web.whatsapp.com")
        time.sleep(12)
        human_scroll(wd)
        time.sleep(3)

        if is_logged_in(wd):
            bot.send_message(message.chat.id, "✅ WhatsApp session is already active!")
            return

        bot.send_message(message.chat.id, "🔍 Looking for *Link with phone number* button...", parse_mode="Markdown")
        link_btn = find_link_phone_button(wd)

        # ── Attempt 2: wait 15s then retry ──
        if link_btn is None:
            bot.send_message(message.chat.id, "⏳ Still loading... waiting 15 more seconds.")
            time.sleep(15)
            link_btn = find_link_phone_button(wd)

        # ── Attempt 3: hard refresh then retry ──
        if link_btn is None:
            bot.send_message(message.chat.id, "🔄 Page refresh attempt 1/2...")
            wd.refresh()
            time.sleep(15)
            human_scroll(wd)
            time.sleep(3)
            link_btn = find_link_phone_button(wd)

        # ── Attempt 4: close driver fully, open fresh, retry ──
        if link_btn is None:
            bot.send_message(message.chat.id, "🔄 Page refresh attempt 2/2 (full restart)...")
            reset_driver()
            wd = get_driver()
            wd.get("https://web.whatsapp.com")
            time.sleep(18)
            human_scroll(wd)
            time.sleep(5)
            link_btn = find_link_phone_button(wd)

        if link_btn is None:
            send_screenshot(
                message.chat.id,
                "❌ *Could not find Link button after 4 attempts.*\n\n"
                "The screenshot above shows what the browser currently sees.\n\n"
                "If it's a *blank white page* → wait 2 minutes and try again.\n"
                "If it shows *QR code only* → WhatsApp may have changed their UI.\n\n"
                "👉 Try: *🔄 Reset Browser* → wait 2 min → *🔗 Login WhatsApp*",
                "no_button.png"
            )
            return

        bot.send_message(message.chat.id, "✅ Button found! Clicking...")
        time.sleep(random.uniform(1.0, 1.8))
        try:
            link_btn.click()
        except Exception:
            wd.execute_script("arguments[0].click();", link_btn)
        time.sleep(8)

        bot.send_message(message.chat.id, "🔍 Looking for phone number input field...")
        phone_input = find_phone_input(wd, timeout=35)

        if phone_input is None:
            send_screenshot(message.chat.id, "❌ Phone number input field not found.", "no_input.png")
            return

        bot.send_message(message.chat.id, f"✏️ Typing number: `{formatted}`", parse_mode="Markdown")
        clear_and_type(wd, phone_input, formatted)
        time.sleep(1.5)

        # যদি ভ্যালু না থাকে, শুধু digits দিয়ে চেষ্টা
        try:
            val = phone_input.get_attribute("value") or ""
            if len(val.replace("+", "").strip()) < 5:
                clear_and_type(wd, phone_input, digits)
                time.sleep(1.5)
        except Exception:
            pass

        time.sleep(2)
        bot.send_message(message.chat.id, "➡️ Clicking Next...")
        click_next(wd, phone_input)

        bot.send_message(message.chat.id, "⏳ Waiting for link code to appear...")
        time.sleep(15)

        # =============================
        # Pairing code টেক্সট বের করা
        # =============================
        code = extract_pairing_code(wd)

        if code:
            # কোডটি ৪+৪ ফরম্যাটে দেখানো
            formatted_code = f"{code[:4]}-{code[4:8]}" if len(code) >= 8 else code
            bot.send_message(
                message.chat.id,
                f"🔑 *Your WhatsApp Link Code:*\n\n"
                f"`{formatted_code}`\n\n"
                f"👆 Tap the code above to copy it.\n\n"
                f"*How to link:*\n"
                f"1. Open WhatsApp on your phone\n"
                f"2. Tap ⋮ (3 dots) → *Linked Devices* → *Link a Device*\n"
                f"3. Tap *Link with phone number instead* (at the bottom)\n"
                f"4. Enter the code above",
                parse_mode="Markdown"
            )
        else:
            # কোড না পেলে স্ক্রিনশট পাঠানো
            bot.send_message(
                message.chat.id,
                "⚠️ Could not extract code as text. Sending screenshot instead..."
            )

        # স্ক্রিনশটও পাঠানো (নিশ্চিতের জন্য)
        send_screenshot(
            message.chat.id,
            "📸 Screenshot of the link code screen.\n_(The 8-character code is visible in the image)_",
            "pairing_code.png"
        )

        # আরও ১০ সেকেন্ড পরে আপডেটেড স্ক্রিনশট
        time.sleep(10)
        code2 = extract_pairing_code(wd)
        if code2 and code2 != code:
            formatted_code2 = f"{code2[:4]}-{code2[4:8]}" if len(code2) >= 8 else code2
            bot.send_message(
                message.chat.id,
                f"🔄 *Updated code:* `{formatted_code2}`",
                parse_mode="Markdown"
            )
        send_screenshot(message.chat.id, "📸 Updated screenshot:", "pairing_code2.png")

        # লিঙ্ক হওয়ার জন্য অপেক্ষা — ২ মিনিট
        bot.send_message(
            message.chat.id,
            "⏳ Waiting up to *2 minutes* for you to enter the code on your phone...",
            parse_mode="Markdown"
        )
        linked = False
        for _ in range(24):
            time.sleep(5)
            try:
                if is_logged_in(wd):
                    linked = True
                    break
            except Exception:
                break

        if linked:
            bot.send_message(
                message.chat.id,
                "🎉 *WhatsApp linked successfully!*\n"
                "✅ You can now check any phone number using 🟢 *WS Check*",
                parse_mode="Markdown",
                reply_markup=get_admin_keyboard()
            )
        else:
            bot.send_message(
                message.chat.id,
                "⏱️ Timeout. If not linked yet, please try again:\n"
                "*🔄 Reset Browser* → *🔗 Login WhatsApp*",
                parse_mode="Markdown"
            )

    except Exception as e:
        err = str(e).split("\n")[0][:300]
        if "TimeoutException" in str(type(e)):
            err = "WhatsApp Web page took too long to load."
        elif "WebDriverException" in str(type(e)):
            err = "Chrome browser failed to start."
        print(f"[ERROR] login: {e}")
        if wd:
            send_screenshot(message.chat.id, f"❌ Error: `{err}`", "error.png")
        else:
            bot.send_message(message.chat.id, f"❌ Error: `{err}`", parse_mode="Markdown")
        reset_driver()


# ============================================================
# NUMBER CHECK — ফিক্সড লজিক
# ============================================================
def process_check_number(message):
    txt = message.text.strip() if message.text else ""

    # বাটন প্রেস হলে ফিরে যাওয়া
    if txt in ["🟢 WS Check", "🔗 Login WhatsApp", "🔄 Reset Browser", "📊 Bot Status"]:
        handle_text(message)
        return

    phone = txt.replace(" ", "").replace("-", "")

    bot.send_message(
        message.chat.id,
        f"⏳ Checking `{phone}` on WhatsApp...",
        parse_mode="Markdown"
    )

    try:
        wd = get_driver()

        # প্রথমে লগইন আছে কিনা চেক
        if not is_logged_in(wd):
            # main page-এ যাওয়া
            wd.get("https://web.whatsapp.com")
            time.sleep(12)

        if not is_logged_in(wd):
            bot.send_message(
                message.chat.id,
                "⚠️ *Bot is not linked to WhatsApp!*\n"
                "👉 Please use *🔗 Login WhatsApp* first.",
                parse_mode="Markdown"
            )
            return

        # নম্বর চেকের URL-এ যাওয়া
        url = f"https://web.whatsapp.com/send?phone={phone}&text&type=phone_number&app_absent=0"
        wd.get(url)

        # পেজ লোডের জন্য যথেষ্ট সময় দেওয়া
        time.sleep(8)

        # ————————————————————————————————————————
        # IMPROVED CHECK LOGIC
        # ————————————————————————————————————————

        # চেক ১ — invalid/not registered popup (সবচেয়ে নির্ভরযোগ্য)
        invalid_detected = False
        try:
            invalid_xpaths = [
                "//*[contains(@data-testid,'popup-contents')]",
                "//div[@role='dialog']",
                "//*[contains(@class,'popup')]",
            ]
            popup_texts = [
                "invalid phone number",
                "not registered",
                "phone number shared via url is invalid",
                "we couldn't find",
            ]
            for xp in invalid_xpaths:
                try:
                    popup = wd.find_element(By.XPATH, xp)
                    if popup.is_displayed():
                        popup_text = popup.text.lower()
                        if any(pt in popup_text for pt in popup_texts):
                            invalid_detected = True
                            # OK বাটন বন্ধ করা
                            try:
                                ok = wd.find_element(By.XPATH, ".//button[contains(.,'OK') or contains(.,'Ok')]")
                                ok.click()
                            except Exception:
                                pass
                            break
                except Exception:
                    pass
        except Exception:
            pass

        if invalid_detected:
            bot.send_message(
                message.chat.id,
                f"❌ *{phone}*\n`No WhatsApp account found on this number.`",
                parse_mode="Markdown"
            )
            return

        # চেক ২ — chat input box আছে মানে নম্বর ভ্যালিড
        # আরও কিছুটা সময় দেওয়া
        time.sleep(6)

        chat_input = wd.find_elements(
            By.XPATH,
            "//div[@contenteditable='true'][@data-tab='10'] | "
            "//div[@contenteditable='true'][contains(@class,'selectable-text')]"
        )

        if chat_input:
            bot.send_message(
                message.chat.id,
                f"✅ *{phone}*\n`WhatsApp account exists! ✓`",
                parse_mode="Markdown"
            )
            return

        # চেক ৩ — আরও বেশি সময় অপেক্ষা করে শেষবার চেক
        time.sleep(8)

        chat_input2 = wd.find_elements(By.XPATH, "//div[@contenteditable='true']")
        invalid2 = wd.find_elements(
            By.XPATH,
            "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'invalid') or "
            "contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'not registered')]"
        )

        if invalid2:
            try:
                ok = wd.find_element(By.XPATH, "//button[contains(.,'OK')]")
                ok.click()
            except Exception:
                pass
            bot.send_message(
                message.chat.id,
                f"❌ *{phone}*\n`No WhatsApp account found on this number.`",
                parse_mode="Markdown"
            )
        elif chat_input2:
            bot.send_message(
                message.chat.id,
                f"✅ *{phone}*\n`WhatsApp account exists! ✓`",
                parse_mode="Markdown"
            )
        else:
            # অস্পষ্ট ফলাফল — স্ক্রিনশট সহ জানানো
            send_screenshot(
                message.chat.id,
                f"⚠️ *{phone}* — Could not determine clearly.\n"
                f"_(Page may still be loading. Screenshot attached.)_",
                "check_unclear.png"
            )

    except Exception as e:
        print(f"[ERROR] check: {e}")
        bot.send_message(
            message.chat.id,
            "❌ An internal error occurred. Please try again.",
            parse_mode="Markdown"
        )
        reset_driver()


# ============================================================
# STATUS
# ============================================================
def show_status(message):
    driver_status = "❌ Stopped"
    wa_status     = "❌ Not Linked"
    url           = ""
    try:
        if driver:
            url = driver.current_url
            driver_status = "✅ Running"
            if is_logged_in(driver):
                wa_status = "✅ Linked"
            else:
                wa_status = "⚠️ Not Linked"
    except Exception:
        pass

    bot.send_message(
        message.chat.id,
        f"📊 *Bot Status*\n\n"
        f"🖥️ Headless: `{USE_HEADLESS}`\n"
        f"🌐 Browser: {driver_status}\n"
        f"📱 WhatsApp: {wa_status}\n"
        f"🔑 Admin ID: `{ADMIN_ID}`\n"
        f"📁 Session: `{SESSION_DIR}`\n"
        f"🔗 URL: `{url[:60] or 'N/A'}`",
        parse_mode="Markdown"
    )


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("WhatsApp Checker Bot starting...")
    print(f"ADMIN_ID : {ADMIN_ID}")
    print(f"Headless : {USE_HEADLESS}")
    print(f"Session  : {SESSION_DIR}")
    print("=" * 50)
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
