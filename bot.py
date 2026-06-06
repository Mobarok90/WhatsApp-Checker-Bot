import os
import time
import random
import telebot
from telebot import types
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# --- কনফিগারেশন ---
# ⚠️ নিচে আপনার টেলিগ্রাম আইডি নম্বরটি বসিয়ে দিন
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
        options.add_argument("--disable-gpu")  # গিটহাব অ্যাকশনের স্ট্যাবিলিটির জন্য জিপিইউ বন্ধ করা
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--window-size=1920,1080")  # ডেস্কটপ লেআউট নিশ্চিত করতে বড় রেজুলেশন
        
        # পেজ লোড স্ট্র্যাটেজি 'eager' (ভারী ইমেজের জন্য ব্রাউজার আটকে থাকবে না)
        options.page_load_strategy = 'eager'
        
        # --- অ্যান্টি-বট সিকিউরিটি বাইপাস সেটিংস ---
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_argument("--user-data-dir=./whatsapp_session")
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(120)
        
        # ব্রাউজারের ভেতর থেকে সেলেনিয়াম রোবট ফ্ল্যাগ মুছে ফেলা
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
    return driver

# মানুষের মতো অত্যন্ত ধীরে ধীরে টাইপ করার হেল্পার ফাংশন
def human_type(element, text):
    element.clear()
    for character in text:
        element.send_keys(character)
        time.sleep(random.uniform(0.25, 0.55))  # অত্যন্ত ধীরস্থির স্বাভাবিক কিবোর্ড টাইপ স্পিড

# মানুষের মতো ব্রাউজার স্ক্রোল করার হেল্পার ফাংশন
def human_scroll(web_driver):
    try:
        web_driver.execute_script("window.scrollTo(0, 200);")
        time.sleep(2.0)
        web_driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1.5)
    except:
        pass

# ব্যর্থ হলে লাইভ ডায়াগনস্টিক রিপোর্ট এবং বাস্তব স্ক্রিনশট পাঠানোর ফাংশন
def send_failure_diagnostic(message, error_msg, web_driver):
    try:
        # গিটহাবের ভার্চুয়াল ব্রাউজারের বর্তমান অবস্থার ছবি তোলা
        web_driver.save_screenshot("diagnostic.png")
        page_title = web_driver.title
        current_url = web_driver.current_url
        
        report = (
            "🔍 **[AI গভীর ডায়াগনস্টিক রিপোর্ট]**\n\n"
            f"❌ **ত্রুটির ধরণ:** `{error_msg}`\n"
            f"🌐 **লিঙ্ক:** {current_url}\n"
            f"📄 **টাইটেল:** {page_title}\n\n"
            "🤖 **AI এনালাইসিস ও সম্ভাব্য সমাধান:**\n"
            "১. ব্রাউজারটি হোয়াটসঅ্যাপের লোডিং পেজে আটকে থাকতে পারে।\n"
            "২. সেশন রিফ্রেশ বা কানেকশন জটিলতা তৈরি হতে পারে।\n\n"
            "👇 ব্রাউজারে ঠিক এই মুহূর্তে কী দেখা যাচ্ছে তার রিয়েল-টাইম স্ক্রিনশট নিচে পাঠানো হলো:"
        )
        with open("diagnostic.png", "rb") as diag_file:
            bot.send_photo(message.chat.id, diag_file, caption=report, parse_mode="Markdown")
    except Exception as diag_e:
        bot.send_message(message.chat.id, f"❌ AI ডায়াগনস্টিক রিপোর্ট তৈরি করতে ব্যর্থ হয়েছে: {diag_e}")

# ১. স্টার্ট কমান্ড (কোনো বিলম্ব ছাড়াই বাটন চলে আসবে)
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_developer = types.KeyboardButton("👤 ডেভেলপার")
    btn_check_ws = types.KeyboardButton("🔍 চেক ডাবলু এস")
    markup.add(btn_developer, btn_check_ws)
    
    bot.send_message(
        message.chat.id, 
        "হোয়াটসঅ্যাপ নম্বর চেকার বটে আপনাকে স্বাগত! নিচের বাটনগুলো ব্যবহার করুন:", 
        reply_markup=markup
    )

# ২. সুরক্ষিত অ্যাডমিন লগইন কমান্ড (লিঙ্ক কোড জেনারেশন)
@bot.message_handler(commands=['login'])
def admin_login(message):
    # আইডি যাচাই করা
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ দুঃখিত, এই কমান্ডটি শুধুমাত্র বটের অ্যাডমিনের জন্য সংরক্ষিত।")
        return

    msg = bot.send_message(
        message.chat.id, 
        "📱 দয়া করে আপনার নিজের হোয়াটসঅ্যাপ নম্বরটি কান্ট্রি কোডসহ পাঠান (যেমন: 88017XXXXXXXX):\n"
        "(এই নম্বরটি দিয়ে আপনার বটটি কানেক্ট বা লিঙ্ক হবে)"
    )
    bot.register_next_step_handler(msg, process_admin_phone)

# ফোন নম্বর প্রসেস এবং হোয়াটসঅ্যাপ থেকে লিঙ্ক কোড পাওয়ার ফাংশন
def process_admin_phone(message):
    raw_input = message.text.strip().replace(" ", "")
    
    # এআই ভিত্তিক পার্সিং ও আন্তর্জাতিক ফর্ম্যাটিং (+880XXXXXXXXX)
    if raw_input.startswith("0"):
        formatted_num = "+880" + raw_input[1:]
    elif raw_input.startswith("880"):
        formatted_num = "+" + raw_input
    elif raw_input.startswith("+"):
        formatted_num = raw_input
    else:
        formatted_num = "+880" + raw_input
        
    bot.send_message(message.chat.id, f"⏳ হোয়াটসঅ্যাপে আন্তর্জাতিক ফরম্যাটে ({formatted_num}) লিঙ্ক কোড তৈরি করা হচ্ছে...")
    
    try:
        web_driver = get_driver()
        bot.send_message(message.chat.id, "🤖 [AI এনালাইসিস]: ক্রোম সেশন শুরু করা হয়েছে। হোয়াটসঅ্যাপ পেজ লোড হচ্ছে...")
        web_driver.get("https://web.whatsapp.com")
        
        # পেজ লোড হওয়ার পর মানুষের মতো কিছুক্ষণ স্ক্রিন দেখা ও স্ক্রোল করা
        time.sleep(8)
        bot.send_message(message.chat.id, "🤖 [AI এনালাইসিস]: মানুষের মতো স্ক্রিন স্ক্রোল করা হচ্ছে...")
        human_scroll(web_driver)
        time.sleep(4)
        
        # 'Link with phone number' বাটনটি খোঁজা (প্যারেন্ট ম্যাচ এড়াতে সুনির্দিষ্ট XPath)
        button_xpath = "//*[contains(text(), 'Link with phone number') or contains(text(), 'Log in with phone number') or contains(text(), 'Link with Phone Number') or contains(text(), 'ফোন নম্বর দিয়ে লিঙ্ক করুন')]"
        
        try:
            link_btn = WebDriverWait(web_driver, 90).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath))
            )
            bot.send_message(message.chat.id, "🤖 [AI এনালাইসিস]: বাটনটি পাওয়া গেছে। মানুষের মতো ক্লিক করা হচ্ছে...")
            time.sleep(1.5)
            
            # ডাবল-লেয়ার ক্লিক মেথড (যাতে কোনো অবস্থায় ক্লিক মিস না হয়)
            try:
                link_btn.click()
            except Exception:
                web_driver.execute_script("arguments[0].click();", link_btn)
                
            bot.send_message(message.chat.id, "🤖 [AI এনালাইসিস]: বাটন ক্লিক করা হয়েছে। পেজ পরিবর্তন ও এনিমেশনের জন্য অপেক্ষা করা হচ্ছে...")
            time.sleep(8)  # পেজ পরিবর্তন ও লোডের জন্য মানুষের মতো ৮ সেকেন্ড সময় দেওয়া
        except Exception as e:
            # চ্যাট লিস্ট আছে কিনা চেক করি (অলরেডি লগইন থাকলে)
            chat_list = web_driver.find_elements(By.XPATH, "//div[@id='pane-side']")
            if len(chat_list) > 0:
                bot.send_message(message.chat.id, "✅ আপনার হোয়াটসঅ্যাপ সেশন ইতিপূর্বে সফলভাবে লগইন করা আছে!")
                return
            else:
                raise e
        
        bot.send_message(message.chat.id, "🤖 [AI এনালাইসিস]: দৃশ্যমান ও সক্রিয় ফোন নম্বর ইনপুট বক্সটি ফিল্টার করা হচ্ছে...")
        
        # প্রথম দৃশ্যমান ও সক্রিয় ইনপুট ফিল্ডটি খুঁজে বের করা (একটি মাত্র ইনপুট ফিল্ড থাকবে)
        phone_input = None
        start_input_time = time.time()
        while time.time() - start_input_time < 30:
            inputs = web_driver.find_elements(By.XPATH, "//input")
            for inp in inputs:
                if inp.is_displayed() and inp.is_enabled():
                    inp_type = inp.get_attribute("type")
                    if inp_type != "file" and inp_type != "hidden":
                        phone_input = inp
                        break
            if phone_input:
                break
            time.sleep(2)
            
        if phone_input is None:
            raise TimeoutException("ফোন নম্বর ইনপুট বক্সটি দৃশ্যমান অবস্থায় পাওয়া যায়নি।")
        
        # কান্ট্রি কোডসহ ডিফল্ট নম্বরটি সম্পূর্ণ মুছে ফেলা
        bot.send_message(message.chat.id, "🤖 [AI এনালাইসিস]: কিবোর্ডের মাধ্যমে ডিফল্ট কান্ট্রি কোডটি সম্পূর্ণ মুছে ফেলা হচ্ছে...")
        phone_input.send_keys(Keys.CONTROL + "a")
        phone_input.send_keys(Keys.BACKSPACE)
        time.sleep(1.5)
        
        # মানুষের মতো প্লাস (+) চিহ্ন ও সম্পূর্ণ নম্বরটি টাইপ করা
        bot.send_message(message.chat.id, f"🤖 [AI এনাসিস]: প্লাস (+) ও কান্ট্রি কোডসহ মানুষের মতো টাইপ করে {formatted_num} ইনপুট দেওয়া হচ্ছে...")
        human_type(phone_input, formatted_num)
        
        # সাবমিট করার আগে মানুষের মতো নম্বরটি রিভিউ করার বিরতি (৩ সেকেন্ড)
        time.sleep(3)
        
        # সবুজ 'Next' বাটন খুঁজে বের করে ক্লিক করা
        bot.send_message(message.chat.id, "🤖 [AI এনালাইসিস]: সবুজ 'Next' বাটনে ক্লিক করা হচ্ছে...")
        next_button_xpath = "//*[contains(text(), 'Next') or contains(text(), 'পরবর্তী') or contains(text(), 'NEXT')]"
        try:
            next_btn = WebDriverWait(web_driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, next_button_xpath))
            )
            try:
                next_btn.click()
            except Exception:
                web_driver.execute_script("arguments[0].click();", next_btn)
        except Exception:
            # যদি কোনো কারণে নেক্সট বাটন কাজ না করে, কিবোর্ড থেকে এন্টার প্রেস করা হবে
            bot.send_message(message.chat.id, "🤖 [AI এনালাইসিস]: 'Next' বাটনটি ক্লিকযোগ্য না থাকায় কিবোর্ডের এন্টার প্রেস করে সাবমিট করা হচ্ছে...")
            phone_input.send_keys(Keys.ENTER)
            
        time.sleep(12) # কোড সম্পূর্ণভাবে জেনারেট হয়ে স্ক্রিনে আসার সময়
        
        # স্ক্রিনশট নিয়ে উইন্ডো পাঠানো
        web_driver.save_screenshot("pairing_code.png")
        with open("pairing_code.png", "rb") as code_file:
            caption_text = (
                "🔑 ছবির মাঝখানে আপনার ৮-অক্ষরের লিঙ্ক কোডটি দেখতে পাবেন।\n\n"
                "👉 **এটি যেভাবে লিঙ্ক করবেন:**\n"
                "১. আপনার মোবাইলের WhatsApp-এ যান ➡️ ডানদিকের ৩টি ডট (বা সেটিংস) ➡️ Linked Devices (লিঙ্ক ডিভাইস) ➡️ Link a Device এ ক্লিক করুন।\n"
                "২. এবার নিচে থাকা 'Link with phone number instead' (ফোন নম্বর দিয়ে লিঙ্ক করুন) অপশনটিতে ক্লিক করুন।\n"
                "৩. ছবিতে দেখতে পাওয়া ৮ অক্ষরের লিঙ্ক কোডটি আপনার মোবাইলে সঠিকভাবে টাইপ করুন।"
            )
            bot.send_photo(message.chat.id, code_file, caption=caption_text)
            
        bot.send_message(message.chat.id, "⏳ আপনার মোবাইলে কোডটি প্রবেশ করার জন্য অপেক্ষা করছি (আমি ১ মিনিট চেক করব)...")
        linked = False
        for _ in range(20): # মোট ৬০ সেকেন্ড চেক করবে
            time.sleep(3)
            chat_list = web_driver.find_elements(By.XPATH, "//div[@id='pane-side']")
            if len(chat_list) > 0:
                linked = True
                break
                
        if linked:
            bot.send_message(message.chat.id, "🎉 অভিনন্দন! আপনার হোয়াটসঅ্যাপ অ্যাকাউন্টটি সফলভাবে লিঙ্ক হয়েছে। এখন যেকোনো ইউজার সরাসরি নম্বর চেক করতে পারবেন।")
        else:
            bot.send_message(message.chat.id, "⏱️ লিঙ্ক করার সময় শেষ হয়ে গেছে। যদি এখনও লিঙ্ক না হয়ে থাকে, তবে আবার `/login` লিখে চেষ্টা করুন।")
            
    except Exception as e:
        # জটিল এরর মেসেজগুলো মানুষের পাঠযোগ্য বাংলায় রূপান্তর করা
        error_msg = str(e).split("\n")[0]
        if "TimeoutException" in str(type(e)):
            error_msg = "হোয়াটসঅ্যাপ পেজ লোড হতে অতিরিক্ত সময় লেগেছে (সার্ভার স্লো)।"
        elif "WebDriverException" in str(type(e)):
            error_msg = "ব্রাউজার ব্যাকগ্রাউন্ডে চালু হতে ব্যর্থ হয়েছে।"
            
        # ব্যর্থতার প্রকৃত কারণ এবং বাস্তব স্ক্রিনশট সহ রিপোর্ট পাঠানো
        send_failure_diagnostic(message, error_msg, web_driver)

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
                "👉 দয়া করে প্রথমে বটের চ্যাটে `/login` কমান্ডটি ব্যবহার করে অ্যাকাউন্টটি কানেক্ট করুন।"
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
