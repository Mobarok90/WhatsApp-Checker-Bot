import os
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
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

# ==============================================================
# কনফিগারেশন
# GitHub Actions Secrets থেকে নেওয়া হবে, না পেলে নিচের ডিফল্ট ব্যবহার হবে
# ==============================================================
ADMIN_ID = int(os.environ.get("ADMIN_ID", "5165615512"))
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8803328478:AAEpVHyLj4svKmfktuewTMZP_1ydvu9zdCQ")

# GitHub Actions-এ /tmp সবসময় writable — session এখানে রাখা হবে
# /tmp-তে রাখলে Actions re-run-এ নতুন সেশন শুরু হবে (ভালো)
SESSION_DIR = os.environ.get("WA_SESSION_DIR", "/tmp/whatsapp_session")
SCREENSHOT_DIR = "/tmp"

bot = telebot.TeleBot(BOT_TOKEN)
driver = None

# GitHub Actions-এ DISPLAY environment variable xvfb-run সেট করে দেয়
# যদি DISPLAY না থাকে তাহলে headless মোড ব্যবহার হবে
USE_HEADLESS = os.environ.get("DISPLAY") is None

print(f"[CONFIG] ADMIN_ID: {ADMIN_ID}")
print(f"[CONFIG] Session Dir: {SESSION_DIR}")
print(f"[CONFIG] Headless Mode: {USE_HEADLESS}")
print(f"[CONFIG] DISPLAY: {os.environ.get('DISPLAY', 'not set')}")


def reset_driver():
    """ড্রাইভার বন্ধ করে রিসেট করার ফাংশন"""
    global driver
    try:
        if driver is not None:
            driver.quit()
    except Exception:
        pass
    driver = None
    print("[DRIVER] Driver reset done.")


def get_driver():
    """GitHub Actions-উপযোগী Chrome ড্রাইভার তৈরির ফাংশন"""
    global driver

    # ড্রাইভার চলছে কিনা যাচাই
    if driver is not None:
        try:
            _ = driver.current_url
            return driver
        except Exception:
            driver = None

    options = Options()

    # GitHub Actions-এ xvfb-run DISPLAY সেট করে, তাই headless লাগে না
    # কিন্তু headless থাকলে আরও stable — উভয় সাপোর্ট করা হয়েছে
    if USE_HEADLESS:
        options.add_argument("--headless=new")
        print("[DRIVER] Starting in HEADLESS mode")
    else:
        print(f"[DRIVER] Starting with DISPLAY={os.environ.get('DISPLAY')}")

    # GitHub Actions runner-এর জন্য অপরিহার্য অপশন
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument("--lang=en-US,en")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--mute-audio")

    # Page load strategy — ভারী WhatsApp পেজের জন্য 'eager' দ্রুততর
    options.page_load_strategy = 'eager'

    # অ্যান্টি-বট বাইপাস
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )

    # WhatsApp সেশন সংরক্ষণ (GitHub Actions-এ /tmp ব্যবহার করা হচ্ছে)
    os.makedirs(SESSION_DIR, exist_ok=True)
    options.add_argument(f"--user-data-dir={SESSION_DIR}")

    # GitHub Actions-এ chromedriver সাধারণত PATH-এ থাকে
    # না থাকলে নিচের পাথগুলো চেক করা হবে
    driver_paths = [
        "/usr/bin/chromedriver",
        "/usr/local/bin/chromedriver",
        "/opt/hostedtoolcache/chromedriver/chromedriver",
    ]

    service = None
    for path in driver_paths:
        if os.path.exists(path):
            service = Service(path)
            print(f"[DRIVER] Using chromedriver: {path}")
            break

    if service:
        driver = webdriver.Chrome(service=service, options=options)
    else:
        # PATH থেকে chromedriver খুঁজে নেবে
        print("[DRIVER] Using chromedriver from PATH")
        driver = webdriver.Chrome(options=options)

    driver.set_page_load_timeout(120)

    # Selenium webdriver ফ্ল্যাগ লুকানো
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    print("[DRIVER] Chrome started successfully.")
    return driver


def human_type(element, text):
    """মানুষের মতো ধীরে ধীরে টাইপ করার ফাংশন"""
    try:
        element.clear()
    except Exception:
        pass
    for character in text:
        element.send_keys(character)
        time.sleep(random.uniform(0.12, 0.28))


def clear_and_type(web_driver, element, text):
    """
    WhatsApp Web-এর React input-এ নম্বর দেওয়ার ফাংশন।
    তিন স্তরে ক্লিয়ার করে তারপর টাইপ করে।
    """
    # ধাপ ১: JavaScript দিয়ে ক্লিয়ার
    try:
        web_driver.execute_script("arguments[0].value = '';", element)
        web_driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", element
        )
    except Exception:
        pass
    time.sleep(0.4)

    # ধাপ ২: কিবোর্ড শর্টকাট দিয়ে ক্লিয়ার
    element.click()
    time.sleep(0.3)
    element.send_keys(Keys.CONTROL + "a")
    time.sleep(0.2)
    element.send_keys(Keys.DELETE)
    time.sleep(0.3)
    element.send_keys(Keys.CONTROL + "a")
    element.send_keys(Keys.BACKSPACE)
    time.sleep(0.4)

    # ধাপ ৩: মানুষের মতো টাইপ করা
    human_type(element, text)

    # React-এর জন্য change event dispatch
    try:
        web_driver.execute_script(
            "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", element
        )
    except Exception:
        pass
    time.sleep(0.5)


def human_scroll(web_driver):
    """মানুষের মতো স্ক্রোল করার ফাংশন"""
    try:
        web_driver.execute_script("window.scrollTo(0, 200);")
        time.sleep(1.5)
        web_driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1.0)
    except Exception:
        pass


def take_screenshot(filename="screenshot.png"):
    """স্ক্রিনশট তোলার ফাংশন — /tmp-তে সেভ করে"""
    path = os.path.join(SCREENSHOT_DIR, filename)
    try:
        driver.save_screenshot(path)
    except Exception:
        pass
    return path


def send_failure_diagnostic(message, error_msg, web_driver):
    """ব্যর্থ হলে স্ক্রিনশট সহ রিপোর্ট পাঠানোর ফাংশন"""
    try:
        path = take_screenshot("diagnostic.png")
        page_title = ""
        current_url = ""
        try:
            page_title = web_driver.title
            current_url = web_driver.current_url
        except Exception:
            pass

        report = (
            "🔍 *ডায়াগনস্টিক রিপোর্ট*\n\n"
            f"❌ *ত্রুটি:* `{error_msg[:300]}`\n"
            f"🌐 *URL:* {current_url}\n"
            f"📄 *টাইটেল:* {page_title}\n\n"
            "📸 ব্রাউজারের বর্তমান অবস্থা:"
        )
        with open(path, "rb") as f:
            bot.send_photo(message.chat.id, f, caption=report, parse_mode="Markdown")
    except Exception as ex:
        bot.send_message(message.chat.id, f"❌ ডায়াগনস্টিক তৈরি করতে ব্যর্থ: {ex}")


def find_link_phone_button(web_driver):
    """
    'Link with phone number' বাটন খোঁজার ফাংশন।
    একাধিক XPath স্ট্র্যাটেজি ব্যবহার করা হয়।
    """
    strategies = [
        # data-testid (সবচেয়ে নির্ভরযোগ্য)
        (By.XPATH, "//*[@data-testid='link-device-phone-number-button']"),
        (By.XPATH, "//*[@data-testid='intro-link-btn']"),
        # text-based
        (By.XPATH, "//div[normalize-space(text())='Link with phone number']"),
        (By.XPATH, "//div[normalize-space(text())='Log in with phone number']"),
        (By.XPATH, "//span[normalize-space(text())='Link with phone number']"),
        (By.XPATH, "//span[normalize-space(text())='Log in with phone number']"),
        (By.XPATH, "//*[contains(text(),'phone number') and (@role='button' or ancestor::*[@role='button'])]"),
        # aria-label
        (By.XPATH, "//*[@aria-label='Link with phone number']"),
        (By.XPATH, "//*[@aria-label='Log in with phone number']"),
        # broad fallback
        (By.XPATH, "//div[@role='button'][contains(.,'phone')]"),
    ]

    for by, xpath in strategies:
        try:
            btn = WebDriverWait(web_driver, 6).until(
                EC.element_to_be_clickable((by, xpath))
            )
            print(f"[BUTTON] Found with: {xpath}")
            return btn
        except Exception:
            continue
    return None


def find_phone_input(web_driver, timeout=35):
    """ফোন নম্বর ইনপুট ফিল্ড খোঁজার ফাংশন"""
    deadline = time.time() + timeout

    while time.time() < deadline:
        # পদ্ধতি ১: data-testid
        for testid in [
            "phone-number-input", "link-device-phone-number-input",
            "intro-input", "phone-input"
        ]:
            try:
                el = web_driver.find_element(By.XPATH, f"//*[@data-testid='{testid}']")
                if el.is_displayed() and el.is_enabled():
                    print(f"[INPUT] Found by data-testid: {testid}")
                    return el
            except Exception:
                pass

        # পদ্ধতি ২: type="tel"
        try:
            el = web_driver.find_element(By.XPATH, "//input[@type='tel']")
            if el.is_displayed() and el.is_enabled():
                print("[INPUT] Found by type=tel")
                return el
        except Exception:
            pass

        # পদ্ধতি ৩: placeholder দিয়ে
        for ph in ["phone", "Phone", "number", "Number"]:
            try:
                el = web_driver.find_element(By.XPATH, f"//input[contains(@placeholder, '{ph}')]")
                if el.is_displayed() and el.is_enabled():
                    print(f"[INPUT] Found by placeholder: {ph}")
                    return el
            except Exception:
                pass

        # পদ্ধতি ৪: যেকোনো দৃশ্যমান input
        try:
            inputs = web_driver.find_elements(By.XPATH, "//input")
            for inp in inputs:
                if inp.is_displayed() and inp.is_enabled():
                    t = inp.get_attribute("type") or ""
                    if t not in ("file", "hidden", "checkbox", "radio", "submit", "button", "image"):
                        print(f"[INPUT] Found generic input type={t}")
                        return inp
        except Exception:
            pass

        time.sleep(2)

    return None


def click_next_button(web_driver, phone_input=None):
    """Next বাটন খুঁজে ক্লিক করার ফাংশন"""
    strategies = [
        (By.XPATH, "//*[@data-testid='link-device-phone-number-next-btn']"),
        (By.XPATH, "//div[@role='button'][normalize-space(.)='Next']"),
        (By.XPATH, "//button[normalize-space(.)='Next']"),
        (By.XPATH, "//span[normalize-space(text())='Next']/parent::*[@role='button']"),
        (By.XPATH, "//span[normalize-space(text())='Next']/ancestor::button"),
        (By.XPATH, "//*[@role='button'][contains(.,'Next')]"),
    ]

    for by, xpath in strategies:
        try:
            btn = WebDriverWait(web_driver, 8).until(
                EC.element_to_be_clickable((by, xpath))
            )
            try:
                btn.click()
            except Exception:
                web_driver.execute_script("arguments[0].click();", btn)
            print(f"[NEXT] Clicked with: {xpath}")
            return True
        except Exception:
            continue

    # fallback: Enter key
    if phone_input:
        try:
            phone_input.send_keys(Keys.RETURN)
            print("[NEXT] Used Enter key")
            return True
        except Exception:
            pass

    return False


# ========================================
# টেলিগ্রাম কমান্ড হ্যান্ডলার
# ========================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("👤 ডেভেলপার"),
        types.KeyboardButton("🔍 চেক ডাবলু এস")
    )
    bot.send_message(
        message.chat.id,
        "হোয়াটসঅ্যাপ নম্বর চেকার বটে স্বাগত! নিচের বাটন ব্যবহার করুন:",
        reply_markup=markup
    )


@bot.message_handler(commands=['login'])
def admin_login(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ এই কমান্ড শুধুমাত্র অ্যাডমিনের জন্য।")
        return
    msg = bot.send_message(
        message.chat.id,
        "📱 হোয়াটসঅ্যাপ নম্বর পাঠান (যেমন: 88017XXXXXXXX বা 017XXXXXXXX):\n"
        "⚠️ GitHub Actions-এ প্রতিটি run-এ নতুন সেশন শুরু হয়।"
    )
    bot.register_next_step_handler(msg, process_admin_phone)


@bot.message_handler(commands=['reset'])
def reset_command(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ এই কমান্ড শুধুমাত্র অ্যাডমিনের জন্য।")
        return
    reset_driver()
    bot.send_message(message.chat.id, "✅ ব্রাউজার রিসেট হয়েছে। এখন `/login` দিয়ে আবার চেষ্টা করুন।")


@bot.message_handler(commands=['status'])
def status_command(message):
    """বটের বর্তমান অবস্থা চেক করার কমান্ড"""
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ এই কমান্ড শুধুমাত্র অ্যাডমিনের জন্য।")
        return

    status_lines = [
        "📊 *বট স্ট্যাটাস:*\n",
        f"🖥️ DISPLAY: `{os.environ.get('DISPLAY', 'না')}`",
        f"🤖 Headless: `{USE_HEADLESS}`",
        f"📁 Session: `{SESSION_DIR}`",
        f"🔑 Admin ID: `{ADMIN_ID}`",
    ]

    # ড্রাইভার চলছে কিনা
    try:
        if driver is not None:
            url = driver.current_url
            status_lines.append(f"🌐 ব্রাউজার: `চালু ({url[:50]}...)`")
        else:
            status_lines.append("🌐 ব্রাউজার: `বন্ধ`")
    except Exception:
        status_lines.append("🌐 ব্রাউজার: `ত্রুটি`")

    bot.send_message(message.chat.id, "\n".join(status_lines), parse_mode="Markdown")


def process_admin_phone(message):
    """ফোন নম্বর প্রসেস করে WhatsApp লিঙ্ক কোড আনার ফাংশন"""
    raw = message.text.strip().replace(" ", "").replace("-", "")

    # নম্বর ফরম্যাট করা
    if raw.startswith("00"):
        formatted = "+" + raw[2:]
    elif raw.startswith("0"):
        formatted = "+880" + raw[1:]
    elif raw.startswith("880") and not raw.startswith("+"):
        formatted = "+" + raw
    elif raw.startswith("+"):
        formatted = raw
    else:
        formatted = "+880" + raw

    print(f"[LOGIN] Formatted number: {formatted}")
    bot.send_message(
        message.chat.id,
        f"⏳ `{formatted}` নম্বরে লিঙ্ক কোড তৈরি হচ্ছে...\n"
        f"(GitHub Actions-এ ৩০-৯০ সেকেন্ড লাগতে পারে)",
        parse_mode="Markdown"
    )

    web_driver = None
    try:
        web_driver = get_driver()

        bot.send_message(message.chat.id, "🌐 WhatsApp Web খোলা হচ্ছে...")
        web_driver.get("https://web.whatsapp.com")
        time.sleep(12)
        human_scroll(web_driver)
        time.sleep(3)

        # ইতিমধ্যে লগইন আছে কিনা চেক
        chat_pane = web_driver.find_elements(By.XPATH, "//div[@id='pane-side']")
        if chat_pane:
            bot.send_message(message.chat.id, "✅ WhatsApp সেশন ইতিমধ্যে সক্রিয় আছে!")
            return

        # Link with phone number বাটন খোঁজা
        bot.send_message(message.chat.id, "🔍 'Link with phone number' বাটন খোঁজা হচ্ছে...")
        link_btn = find_link_phone_button(web_driver)

        if link_btn is None:
            bot.send_message(message.chat.id, "⏳ আরও ১৫ সেকেন্ড অপেক্ষা করা হচ্ছে...")
            time.sleep(15)
            link_btn = find_link_phone_button(web_driver)

        if link_btn is None:
            # স্ক্রিনশট দিয়ে রিপোর্ট
            path = take_screenshot("no_button.png")
            with open(path, "rb") as f:
                bot.send_photo(
                    message.chat.id, f,
                    caption=(
                        "❌ 'Link with phone number' বাটন পাওয়া যায়নি।\n\n"
                        "সম্ভাব্য কারণ:\n"
                        "• WhatsApp UI পরিবর্তন হয়েছে\n"
                        "• পেজ লোড হয়নি\n"
                        "• IP block হয়েছে\n\n"
                        "➡️ `/reset` দিয়ে রিসেট করুন, তারপর `/login` দিন।"
                    )
                )
            return

        bot.send_message(message.chat.id, "✅ বাটন পাওয়া গেছে! ক্লিক করা হচ্ছে...")
        time.sleep(random.uniform(1.0, 2.0))
        try:
            link_btn.click()
        except Exception:
            web_driver.execute_script("arguments[0].click();", link_btn)
        time.sleep(8)

        # ফোন ইনপুট খোঁজা
        bot.send_message(message.chat.id, "🔍 ফোন ইনপুট বক্স খোঁজা হচ্ছে...")
        phone_input = find_phone_input(web_driver, timeout=35)

        if phone_input is None:
            send_failure_diagnostic(message, "ফোন ইনপুট বক্স পাওয়া যায়নি", web_driver)
            return

        bot.send_message(message.chat.id, f"✏️ নম্বর টাইপ করা হচ্ছে: `{formatted}`", parse_mode="Markdown")

        # নম্বর দেওয়া — প্রথমে + সহ পূর্ণ নম্বর
        clear_and_type(web_driver, phone_input, formatted)
        time.sleep(1.5)

        # যদি input-এ কিছু না থাকে, শুধু digits চেষ্টা
        try:
            val = phone_input.get_attribute("value") or ""
            if len(val.replace("+", "").strip()) < 5:
                print("[INPUT] Value too short, trying digits only")
                digits = formatted.replace("+", "")
                clear_and_type(web_driver, phone_input, digits)
                time.sleep(1.5)
        except Exception:
            pass

        time.sleep(2)

        # Next বাটন ক্লিক
        bot.send_message(message.chat.id, "➡️ Next বাটন ক্লিক করা হচ্ছে...")
        click_next_button(web_driver, phone_input)

        bot.send_message(message.chat.id, "⏳ লিঙ্ক কোড আসছে (১৫ সেকেন্ড)...")
        time.sleep(15)

        # স্ক্রিনশট নেওয়া
        path = take_screenshot("pairing_code.png")
        with open(path, "rb") as f:
            caption = (
                "🔑 ছবিতে *৮ অক্ষরের লিঙ্ক কোড* দেখুন।\n\n"
                "*মোবাইলে কীভাবে দেবেন:*\n"
                "১. WhatsApp → ৩টি ডট → Linked Devices → Link a Device\n"
                "২. নিচে 'Link with phone number instead' চাপুন\n"
                "৩. ৮ অক্ষরের কোডটি টাইপ করুন"
            )
            bot.send_photo(message.chat.id, f, caption=caption, parse_mode="Markdown")

        # ১০ সেকেন্ড পরে আরেকটি আপডেটেড স্ক্রিনশট
        time.sleep(10)
        path2 = take_screenshot("pairing_code_2.png")
        with open(path2, "rb") as f2:
            bot.send_photo(message.chat.id, f2, caption="📸 আপডেটেড স্ক্রিনশট (কোড স্পষ্ট দেখা যাচ্ছে কিনা দেখুন):")

        # ২ মিনিট লিঙ্ক হওয়ার জন্য অপেক্ষা
        bot.send_message(
            message.chat.id,
            "⏳ মোবাইলে কোড দেওয়ার জন্য *২ মিনিট* অপেক্ষা করছি...",
            parse_mode="Markdown"
        )
        linked = False
        for i in range(24):
            time.sleep(5)
            try:
                pane = web_driver.find_elements(By.XPATH, "//div[@id='pane-side']")
                if pane:
                    linked = True
                    break
            except Exception:
                break

        if linked:
            bot.send_message(
                message.chat.id,
                "🎉 *অভিনন্দন!* WhatsApp সফলভাবে লিঙ্ক হয়েছে!\n"
                "এখন যেকোনো নম্বর চেক করা যাবে। ✅",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(
                message.chat.id,
                "⏱️ ২ মিনিট শেষ। লিঙ্ক না হলে আবার চেষ্টা করুন:\n"
                "1️⃣ `/reset` → 2️⃣ `/login`",
                parse_mode="Markdown"
            )

    except Exception as e:
        error_msg = str(e).split("\n")[0][:300]
        if "TimeoutException" in str(type(e)):
            error_msg = "WhatsApp Web পেজ লোড হতে বেশি সময় লেগেছে।"
        elif "WebDriverException" in str(type(e)):
            error_msg = "Chrome ব্রাউজার চালু হতে ব্যর্থ।"

        print(f"[ERROR] process_admin_phone: {e}")
        if web_driver:
            send_failure_diagnostic(message, error_msg, web_driver)
        else:
            bot.send_message(message.chat.id, f"❌ ত্রুটি: {error_msg}")

        reset_driver()


# ========================================
# বাটন হ্যান্ডলার
# ========================================

@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    if message.text == "👤 ডেভেলপার":
        bot.send_message(
            message.chat.id,
            "👤 *ডেভেলপার ইনফো:*\n\nPython + Selenium + GitHub Actions দিয়ে তৈরি।",
            parse_mode="Markdown"
        )
    elif message.text == "🔍 চেক ডাবলু এস":
        msg = bot.send_message(
            message.chat.id,
            "কান্ট্রি কোডসহ নম্বর পাঠান (যেমন: 88017XXXXXXXX):"
        )
        bot.register_next_step_handler(msg, process_phone)


def process_phone(message):
    """WhatsApp নম্বর যাচাই করার ফাংশন"""
    phone = message.text.strip()
    if phone in ["👤 ডেভেলপার", "🔍 চেক ডাবলু এস"]:
        handle_buttons(message)
        return

    bot.send_message(message.chat.id, f"⏳ `{phone}` যাচাই হচ্ছে...", parse_mode="Markdown")

    try:
        web_driver = get_driver()
        url = f"https://web.whatsapp.com/send?phone={phone}"
        web_driver.get(url)
        time.sleep(13)

        # লগইন স্ট্যাটাস চেক
        qr = web_driver.find_elements(By.XPATH, "//canvas[@aria-label='Scan me!'] | //*[@data-testid='qrcode']")
        pane = web_driver.find_elements(By.XPATH, "//div[@id='pane-side']")
        chat_input = web_driver.find_elements(By.XPATH, "//div[@contenteditable='true']")

        if qr or (not pane and not chat_input):
            bot.send_message(
                message.chat.id,
                "⚠️ বটটি WhatsApp-এর সাথে লিঙ্ক নেই!\n"
                "👉 প্রথমে `/login` কমান্ড ব্যবহার করুন।"
            )
            return

        # ইনভ্যালিড নম্বর চেক
        invalid = web_driver.find_elements(
            By.XPATH,
            "//*[contains(text(),'invalid') or contains(text(),'Invalid') "
            "or contains(text(),'not registered') or contains(text(),'অবৈধ')]"
        )
        if invalid:
            try:
                ok = web_driver.find_element(By.XPATH, "//button[contains(.,'OK')]")
                ok.click()
            except Exception:
                pass
            bot.send_message(message.chat.id, f"❌ `{phone}` নম্বরে WhatsApp নেই।", parse_mode="Markdown")
        elif chat_input:
            bot.send_message(message.chat.id, f"✅ `{phone}` নম্বরে সক্রিয় WhatsApp অ্যাকাউন্ট আছে।", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, f"⚠️ `{phone}` — নিশ্চিত করা যায়নি। পেজ লোড সম্পন্ন হয়নি।", parse_mode="Markdown")

    except Exception as e:
        print(f"[ERROR] process_phone: {e}")
        bot.send_message(message.chat.id, "❌ একটি ত্রুটি ঘটেছে। আবার চেষ্টা করুন।")
        reset_driver()


# ========================================
# মেইন
# ========================================
if __name__ == "__main__":
    print("=" * 50)
    print("টেলিগ্রাম বট চালু হচ্ছে...")
    print(f"ADMIN_ID: {ADMIN_ID}")
    print(f"SESSION_DIR: {SESSION_DIR}")
    print(f"Headless: {USE_HEADLESS}")
    print("=" * 50)
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
