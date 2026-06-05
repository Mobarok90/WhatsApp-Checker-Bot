import os
import time
import telebot
from telebot import types
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- কনফিগারেশন ---
BOT_TOKEN = "8803328478:AAEpVHyLj4svKmfktuewTMZP_1ydvu9zdCQ"
bot = telebot.TeleBot(BOT_TOKEN)

driver = None
admin_chat_id = None  # কিউআর কোড পাঠানো এবং স্ট্যাটাস জানানোর জন্য

def init_driver():
    """সেলেনিয়াম ক্রোম ড্রাইভার সচল করার ফাংশন"""
    global driver
    print("[INFO] ক্রোম ড্রাইভার চালু করার চেষ্টা করা হচ্ছে...")
    
    options = Options()
    options.add_argument("--headless")  # গিটহাব অ্যাকশন্সের জন্য হেডলেস রান করা আবশ্যক
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # হোয়াটসঅ্যাপ ব্লক এড়াতে ক্রোম ইউজার এজেন্ট
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    # সেশন ডেটা সেভ রাখার ডিরেক্টরি (যাতে গিটহাবে সেশন ক্যাশ করা যায়)
    options.add_argument("--user-data-dir=./whatsapp_session")
    
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(60)
        print("[SUCCESS] ক্রোম ড্রাইভার সফলভাবে চালু হয়েছে।")
    except Exception as e:
        print(f"[ERROR] ড্রাইভার চালুর সময় ত্রুটি: {e}")
        time.sleep(5)
        init_driver()  # সেলফ-হিলিং রিট্রাই

def log_to_telegram(message_text):
    """বটের বর্তমান অবস্থা টেলিগ্রামে জানানো"""
    global admin_chat_id
    if admin_chat_id:
        try:
            bot.send_message(admin_chat_id, f"⚙️ [System Log]: {message_text}")
        except Exception:
            pass

def check_login_status():
    """হোয়াটসঅ্যাপ লগইন স্ট্যাটাস চেক করা"""
    global driver
    try:
        driver.get("https://web.whatsapp.com")
        # ১৫ সেকেন্ড অপেক্ষা করে দেখবে চ্যাট লিস্ট লোড হয় কিনা
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//div[@id='pane-side']"))
        )
        return "LOGGED_IN"
    except Exception:
        # চ্যাট লিস্ট না আসলে চেক করবে কিউআর কোড এসেছে কিনা
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//canvas[@aria-label='Scan me!']"))
            )
            return "NEEDS_QR"
        except:
            return "UNKNOWN"

def safe_whatsapp_check(phone):
    """হোয়াটসঅ্যাপ নম্বর যাচাই করার মূল ফাংশন (স্মার্ট রিকভারি সহ)"""
    global driver
    retries = 2
    for attempt in range(retries):
        try:
            print(f"[PROCESS] নম্বর চেক করা হচ্ছে: {phone} (চেষ্টা: {attempt + 1})")
            url = f"https://web.whatsapp.com/send?phone={phone}"
            driver.get(url)
            
            # পেজ লোড হওয়ার জন্য ১০ সেকেন্ড সময় দেওয়া
            time.sleep(10)
            
            # ১. ইনভ্যালিড নম্বর পপ-আপ আছে কিনা চেক করা
            invalid_popup = driver.find_elements(By.XPATH, "//*[contains(text(), 'invalid') or contains(text(), 'অবৈধ') or contains(text(), 'Invalid')]")
            if len(invalid_popup) > 0:
                try:
                    # পপ-আপ বন্ধ করা যাতে পরের রিকোয়েস্টে সমস্যা না হয়
                    ok_button = driver.find_element(By.XPATH, "//button//span[contains(text(), 'OK') or contains(text(), 'ঠিক আছে')]")
                    ok_button.click()
                    time.sleep(1)
                except:
                    pass
                return f"❌ {phone} নম্বরটিতে কোনো হোয়াটসঅ্যাপ অ্যাকাউন্ট নেই।"
            
            # ২. চ্যাট ইনপুট বক্স আছে কিনা চেক করা (সঠিক নম্বর)
            chat_input = driver.find_elements(By.XPATH, "//div[@contenteditable='true']")
            if len(chat_input) > 0:
                return f"✅ {phone} নম্বরটিতে একটি সক্রিয় হোয়াটসঅ্যাপ অ্যাকাউন্ট আছে।"
            
            # ৩. কোনোটিই না পাওয়া গেলে সেশন বা লোড সমস্যা হতে পারে
            return "⚠️ নিশ্চিত হওয়া যায়নি। পেজ লোড হতে অতিরিক্ত সময় লেগেছে বা সেশন সমস্যা।"
            
        except Exception as e:
            log_to_telegram(f"ব্রাউজারে ত্রুটি ঘটেছে: {e}। ড্রাইভার রিস্টার্ট করা হচ্ছে...")
            try:
                driver.quit()
            except:
                pass
            init_driver()
            driver.get("https://web.whatsapp.com")
            time.sleep(5)
            
    return "❌ কারিগরি সমস্যার কারণে নম্বরটি চেক করা যায়নি। অনুগ্রহ করে আবার চেষ্টা করুন।"

# --- টেলিগ্রাম কমান্ডস ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    global admin_chat_id
    admin_chat_id = message.chat.id
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_developer = types.KeyboardButton("👤 ডেভেলপার")
    btn_check_ws = types.KeyboardButton("🔍 চেক ডাবলু এস")
    markup.add(btn_developer, btn_check_ws)
    
    bot.send_message(message.chat.id, "⏳ হোয়াটসঅ্যাপ কানেকশন স্ট্যাটাস যাচাই করা হচ্ছে...")
    
    status = check_login_status()
    if status == "LOGGED_IN":
        bot.send_message(
            message.chat.id, 
            "✅ হোয়াটসঅ্যাপ সেশন সক্রিয় আছে! নিচের বাটনগুলো ব্যবহার করুন:", 
            reply_markup=markup
        )
    elif status == "NEEDS_QR":
        bot.send_message(message.chat.id, "⚠️ হোয়াটসঅ্যাপ লগইন করা নেই। আমি কিউআর কোড পাঠাচ্ছি, দয়া করে স্ক্যান করুন...")
        # কিউআর কোডের স্ক্রিনশট নেওয়া
        driver.save_screenshot("qr_code.png")
        with open("qr_code.png", "rb") as qr_img:
            bot.send_photo(message.chat.id, qr_img, caption="৪৫ সেকেন্ডের মধ্যে এই QR কোডটি আপনার হোয়াটসঅ্যাপ দিয়ে স্ক্যান করুন।")
        
        # স্ক্যান করার জন্য অপেক্ষা করা এবং লুপে চেক করা
        scanned = False
        for _ in range(15):
            time.sleep(3)
            try:
                driver.find_element(By.XPATH, "//div[@id='pane-side']")
                scanned = True
                break
            except:
                pass
        
        if scanned:
            bot.send_message(
                message.chat.id, 
                "🎉 লগইন সফল হয়েছে! এখন আপনি বাটনগুলো ব্যবহার করতে পারবেন।", 
                reply_markup=markup
            )
        else:
            bot.send_message(message.chat.id, "❌ স্ক্যান করার সময় শেষ হয়ে গেছে। আবার চেষ্টা করতে /start লিখুন।")
    else:
        bot.send_message(message.chat.id, "❌ সংযোগ স্থাপন করা যাচ্ছে না। দয়া করে /start লিখে আবার চেষ্টা করুন।")

@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    global admin_chat_id
    admin_chat_id = message.chat.id
    
    if message.text == "👤 ডেভেলপার":
        dev_info = "👤 **ডেভেলপার ইনফরমেশন:**\n\nএই বটটি ২৪/৭ গিটহাব অ্যাকশন্সে সচল রাখার জন্য অপ্টিমাইজড করা হয়েছে।"
        bot.send_message(message.chat.id, dev_info, parse_mode="Markdown")
        
    elif message.text == "🔍 চেক ডাবলু এস":
        msg = bot.send_message(
            message.chat.id, 
            "অনুগ্রহ করে কান্ট্রি কোডসহ ফোন নম্বরটি পাঠান (যেমন: 88017XXXXXXXX):"
        )
        bot.register_next_step_handler(msg, process_phone)

def process_phone(message):
    phone = message.text.strip()
    if phone in ["👤 ডেভেলপার", "🔍 চেক ডাবলু এস"]:
        handle_buttons(message)
        return

    bot.send_message(message.chat.id, f"⏳ {phone} নম্বরটি যাচাই করা হচ্ছে, অনুগ্রহ করে অপেক্ষা করুন...")
    result = safe_whatsapp_check(phone)
    bot.send_message(message.chat.id, result)

# ড্রাইভার চালু করে বটের পোলিং চালু করা
init_driver()
print("টেলিগ্রাম বট অ্যাক্টিভ করা হচ্ছে...")
bot.infinity_polling()
