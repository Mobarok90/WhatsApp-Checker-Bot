import os
import time
import telebot
from telebot import types
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# --- কনফিগারেশন ---
# ⚠️ নিচে আপনার টেলিগ্রাম আইডি নম্বরটি বসিয়ে দিন (যেমন: ADMIN_ID = 12345678)
ADMIN_ID = 5165615512 

BOT_TOKEN = "8803328478:AAEpVHyLj4svKmfktuewTMZP_1ydvu9zdCQ"
bot = telebot.TeleBot(BOT_TOKEN)

driver = None

def get_driver():
    """ড্রাইভার সচল করার জন্য এবং অ্যান্টি-বট বাইপাস করার ফাংশন"""
    global driver
    if driver is None:
        options = Options()
        options.add_argument("--headless=new")  # আধুনিক হেডলেস মোড
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,800")  # কিউআর কোড স্পষ্ট দেখানোর জন্য উপযুক্ত রেজুলেশন
        
        # --- অ্যান্টি-বট সিকিউরিটি বাইপাস সেটিংস ---
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_argument("--user-data-dir=./whatsapp_session")
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(45)
        
        # ব্রাউজারের ভেতর থেকে সেলেনিয়াম রোবট ফ্ল্যাগ মুছে ফেলা
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
    return driver

# ১. স্টার্ট কমান্ড (কোনো বিলম্ব ছাড়াই বাটন চলে আসবে)
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_developer = types.KeyboardButton("👤 ডেভেলপার")
    btn_check_ws = types.KeyboardButton("🔍 চেক ডাবলু এস")
    markup.add(btn_developer, btn_check_ws)
    
    bot.send_message(
        message.chat.id, 
        "হোয়াটসঅ্যাপ নম্বর চেকার বটে আপনাকে স্বাগতম! নিচের বাটনগুলো ব্যবহার করুন:", 
        reply_markup=markup
    )

# ২. সুরক্ষিত অ্যাডমিন লগইন কমান্ড (শুধু আপনি কিউআর কোড পাবেন, অন্য কেউ দিলে রিজেক্ট হবে)
@bot.message_handler(commands=['login'])
def admin_login(message):
    # আইডি যাচাই করা
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ দুঃখিত, এই কমান্ডটি শুধুমাত্র বটের অ্যাডমিনের জন্য সংরক্ষিত।")
        return

    bot.send_message(message.chat.id, "⏳ হোয়াটসঅ্যাপ কানেকশন স্ট্যাটাস চেক করা হচ্ছে...")
    try:
        web_driver = get_driver()
        web_driver.get("https://web.whatsapp.com")
        time.sleep(12)  # কিউআর কোড জেনারেট হওয়ার জন্য পর্যাপ্ত সময়
        
        # সেশন সচল আছে কি না দেখা
        chat_list = web_driver.find_elements(By.XPATH, "//div[@id='pane-side']")
        if len(chat_list) > 0:
            bot.send_message(message.chat.id, "✅ হোয়াটসঅ্যাপ সেশন সফলভাবে লগইন করা আছে!")
        else:
            bot.send_message(message.chat.id, "⏳ সেশন সক্রিয় নেই। লগইন করার জন্য কিউআর কোড জেনারেট করা হচ্ছে...")
            web_driver.save_screenshot("qr_code.png")
            with open("qr_code.png", "rb") as qr_file:
                bot.send_photo(message.chat.id, qr_file, caption="আপনার হোয়াটসঅ্যাপ অ্যাপ দিয়ে এই কিউআর কোডটি স্ক্যান করে নিন।")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ ত্রুটি ঘটেছে: {e}")

# ৩. সাধারণ বাটন ক্লিক হ্যান্ডলার
@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    if message.text == "👤 ডেভেলপার":
        dev_info = (
            "👤 **ডেভেলপার ইনফরমেশন:**\n\n"
            "এই অটোমেশন সিস্টেমটি পাইথন দিয়ে তৈরি করা হয়েছে।"
        )
        bot.send_message(message.chat.id, dev_info, parse_mode="Markdown")
        
    elif message.text == "🔍 চেক ডাবলু এস":
        msg = bot.send_message(
            message.chat.id, 
            "অনুগ্রহ করে কান্ট্রি কোডসহ ফোন নম্বরটি পাঠান (যেমন: 88017XXXXXXXX):"
        )
        bot.register_next_step_handler(msg, process_phone)

# ৪. নম্বর যাচাই করার মূল লজিক
def process_phone(message):
    phone = message.text.strip()
    if phone in ["👤 ডেভেলপার", "🔍 চেক ডাবলু এস"]:
        handle_buttons(message)
        return

    bot.send_message(message.chat.id, f"⏳ {phone} নম্বরটি যাচাই করা হচ্ছে, অনুগ্রহ করে অপেক্ষা করুন...")
    
    try:
        web_driver = get_driver()
        url = f"https://web.whatsapp.com/send?phone={phone}"
        web_driver.get(url)
        
        # পেজ লোড হওয়ার জন্য অপেক্ষা
        time.sleep(10)
        
        # লগইন স্ট্যাটাস চেক
        qr_present = web_driver.find_elements(By.XPATH, "//canvas[@aria-label='Scan me!']")
        chat_pane = web_driver.find_elements(By.XPATH, "//div[@id='pane-side']")
        chat_input = web_driver.find_elements(By.XPATH, "//div[@contenteditable='true']")
        
        if len(qr_present) > 0 or (len(chat_pane) == 0 and len(chat_input) == 0):
            bot.send_message(
                message.chat.id, 
                "⚠️ বটটি এখনও আপনার হোয়াটসঅ্যাপের সাথে লিংক করা নেই!\n\n"
                "👉 দয়া করে প্রথমে বটের চ্যাটে `/login` কমান্ডটি লিখে কিউআর (QR) কোডটি স্ক্যান করে নিন।"
            )
            return

        # ইনভ্যালিড নম্বর চেক করা
        invalid_popup = web_driver.find_elements(By.XPATH, "//*[contains(text(), 'invalid') or contains(text(), 'অবৈধ') or contains(text(), 'Invalid')]")
        if len(invalid_popup) > 0:
            try:
                ok_button = web_driver.find_element(By.XPATH, "//button//span[contains(text(), 'OK') or contains(text(), 'ঠিক আছে')]")
                ok_button.click()
            except:
                pass
            bot.send_message(message.chat.id, f"❌ {phone} নম্বরটিতে কোনো হোয়াটসঅ্যাপ অ্যাকাউন্ট নেই।")
        else:
            # চ্যাট ইনপুট বক্স আছে কি না চেক করা (সঠিক নম্বর)
            if len(chat_input) > 0:
                bot.send_message(message.chat.id, f"✅ {phone} নম্বরটিতে একটি সক্রিয় হোয়াটসঅ্যাপ অ্যাকাউন্ট আছে।")
            else:
                bot.send_message(message.chat.id, "⚠️ নিশ্চিত হওয়া যায়নি। পেজ লোড হতে অতিরিক্ত সময় লেগেছে।")
                
    except Exception as e:
        print(f"Error: {e}")
        bot.send_message(message.chat.id, "❌ একটি অভ্যন্তরীণ ত্রুটি ঘটেছে। অনুগ্রহ করে আবার চেষ্টা করুন।")

# পোলিং স্টার্ট
if __name__ == "__main__":
    print("টেলিগ্রাম বট ব্যাকগ্রাউন্ডে সচল করা হচ্ছে...")
    bot.infinity_polling()
