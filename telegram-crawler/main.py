import os
import pickle
import time
import base64
import requests
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

# تنظیمات ثابت
PHONE_NUMBER = "9919982706"  # شماره تلفن ثابت (بدون کد کشور)
SOURCE_CHANNEL = "@BINNER_IRAN"  # کانال مبدأ
TARGET_CHANNEL = "@amiralitesttesttestbotbotbot"  # کانال مقصد

COOKIES_FILE_PATH = 'telegram_cookies.pkl'
driver = None


def initialize_driver():
    """Initialize WebDriver"""
    global driver
    if driver is None:
        print("[+] Initializing WebDriver...")
        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(service=service, options=options)
        driver.maximize_window()


def save_cookies(driver, path):
    """Save cookies after login"""
    print("[+] Saving cookies...")
    with open(path, 'wb') as filehandler:
        pickle.dump(driver.get_cookies(), filehandler)
    print(f"[+] Cookies saved to {path}")


def load_cookies(driver, path):
    """Load cookies to maintain session"""
    if os.path.exists(path):
        print("[+] Loading cookies...")
        with open(path, 'rb') as cookiesfile:
            cookies = pickle.load(cookiesfile)
            # driver.get('https://web.telegram.org/')
            driver.delete_all_cookies()
            for cookie in cookies:
                if 'domain' in cookie:
                    if not cookie['domain'].startswith('.'):
                        cookie['domain'] = '.' + cookie['domain']
                driver.add_cookie(cookie)
            print("[+] Cookies loaded successfully.")
            driver.refresh()  # Refresh to apply cookies
    else:
        print(f"[-] Cookie file not found: {path}")


@app.route('/login_and_verify', methods=['GET'])
def login_and_verify():
    """تابع جدید برای لاگین و ورود با شماره تلفن ثابت"""
    global driver
    try:
        initialize_driver()
        driver.get('https://web.telegram.org/a/')
        load_cookies(driver, COOKIES_FILE_PATH)
        driver.refresh()
        print("[+] Opening Telegram Web...")
        time.sleep(2)
        
        # اگر قبلاً لاگین شده باشد، این مرحله را رد می‌کند
        try:
            button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@class='Button smaller primary text']"))
            )
            button.click()
            print("[+] Login button clicked")

            time.sleep(2)
            code_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "sign-in-phone-code"))
            )
            code_input.clear()
            code_input.send_keys("IR")

            element = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[contains(@class, 'MenuItem') and contains(@class, 'compact')]"))
            )
            element.click()

            number_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "sign-in-phone-number"))
            )
            number_input.send_keys(PHONE_NUMBER)
            print(f"[+] Phone number {PHONE_NUMBER} entered")

            time.sleep(0.5)
            submit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
            )
            submit_button.click()
            print("[+] Phone submitted")
            
            return jsonify({'message': 'شماره تلفن ارسال شد. لطفاً کد OTP را با استفاده از آدرس /verify_otp?otp=CODE وارد کنید.'})
        
        except Exception as e:
            print(f"[!] احتمالاً قبلاً لاگین شده‌اید یا خطایی رخ داده: {str(e)}")
            return jsonify({'message': 'احتمالاً قبلاً لاگین شده‌اید یا خطایی رخ داده است.'})
            
    except Exception as e:
        print(f"[X] Login error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/verify_otp', methods=['GET'])
def verify_otp():
    """Verify OTP code"""
    global driver
    otp_code = request.args.get('otp')
    if not otp_code:
        return jsonify({'error': 'OTP is required! Use: /verify_otp?otp=CODE'}), 400

    try:
        print(f"[+] Entering OTP: {otp_code}")
        otp_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@id='sign-in-code']"))
        )
        otp_input.send_keys(otp_code)
        time.sleep(2)
        save_cookies(driver, COOKIES_FILE_PATH)
        print("[+] Successfully logged in!")

        return jsonify({'success': True, 'message': 'Logged in successfully!'})
    except Exception as e:
        print(f"[X] OTP verification error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/forward_messages', methods=['GET'])
def forward_messages():
    """Fetch unread messages from a Telegram channel and forward them to target channel"""
    global driver
    if driver is None:
        initialize_driver()
        driver.get('https://web.telegram.org/a/')
        load_cookies(driver, COOKIES_FILE_PATH)
        time.sleep(2)

    try:
        search_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@id='telegram-search-input']"))
        )
        search_input.click()
        search_input.clear()
        search_input.send_keys(SOURCE_CHANNEL)
        print(f"[+] Searching for source channel: {SOURCE_CHANNEL}")

        first_item = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "(//div[contains(@class, 'ChatInfo')])[1]"))
        )
        ActionChains(driver).move_to_element(first_item).click().perform()
        print(f"[+] Channel {SOURCE_CHANNEL} opened")

        try:
            try:
                # تلاش برای پیدا کردن نشانگر پیام‌های خوانده نشده
                unread_divider = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@class='unread-divider local-action-message']"))
                )
                print("✅ unread divider found")

                driver.execute_script("arguments[0].scrollIntoView();", unread_divider)
                time.sleep(0.5)

                first_message = unread_divider.find_element(By.XPATH, "./following::div[contains(@class, 'Message')][1]")
                print("✅ first message found")

                driver.execute_script("arguments[0].scrollIntoView();", first_message)
                time.sleep(0.5)
                print("scrolled")
                ActionChains(driver).context_click(first_message).perform()

                select_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//div[@class='MenuItem compact' and text()='Select']")
                    )
                )
                select_button.click()

                messages_in_group = first_message.find_elements(By.XPATH,
                                                               "./following::div[contains(@class, 'Message')]")
                for msg in messages_in_group:
                    driver.execute_script("arguments[0].scrollIntoView();", msg)

                    location = msg.location
                    size = msg.size

                    x_offset = size['width'] * 0.8
                    y_offset = size['height'] / 2

                    # کلیک در مختصات تنظیم‌شده
                    ActionChains(driver).move_to_element_with_offset(msg, x_offset, y_offset).click().perform()

                message_group_first_unread = driver.find_element(By.XPATH,
                                                                "//div[contains(@class, 'message-date-group')]//div[contains(@class, 'unread-divider')]")
                message_groups = message_group_first_unread.find_elements(By.XPATH,
                                                                         "./following::div[contains(@class, 'message-date-group')]")
                if not message_groups:
                    print("❌ هیچ گروه پیامی پیدا نشد!")
                    return jsonify({'message': 'No message groups found'}), 404
                
                for message_group in message_groups:
                    messages_in_group = message_group.find_elements(By.XPATH,
                                                                   ".//div[contains(@class, 'Message') and not(contains(@class, 'is-selected'))]")
                    for msg in messages_in_group:
                        driver.execute_script("arguments[0].scrollIntoView();", msg)

                        location = msg.location
                        size = msg.size

                        x_offset = size['width'] * 0.8
                        y_offset = size['height'] / 2

                        # کلیک در مختصات تنظیم‌شده
                        ActionChains(driver).move_to_element_with_offset(msg, x_offset, y_offset).click().perform()


            except Exception as e:
                print(f"[X] خطا در انتخاب پیام‌ها: {str(e)}")
                return jsonify({'error': f'Error selecting messages: {str(e)}'}), 500

            forward_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[@role='button' and @title='Forward Messages']"))
            )
            forward_button.click()
            print("[+] Forward button clicked")

            search_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@class='form-control']"))
            )
            search_input.send_keys(TARGET_CHANNEL)
            print(f"[+] Searching for target channel: {TARGET_CHANNEL}")

            first_result = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@class='ripple-container']"))
            )
            first_result.click()
            print(f"[+] Selected target channel: {TARGET_CHANNEL}")

            send_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'send') and contains(@class, 'Button')]"))
            )
            send_button.click()
            print("[+] Messages forwarded successfully!")

            return jsonify({'success': 'Messages forwarded successfully!'}), 200

        except Exception as e:
            print(f"[X] Error forwarding messages: {str(e)}")
            return jsonify({'error': str(e)}), 500

    except Exception as e:
        print(f"[X] Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/', methods=['GET'])
def index():
    """صفحه اصلی و راهنما"""
    return """
    <h1>راهنمای استفاده از کرالر تلگرام</h1>
    <ul>
        <li><a href="/login_and_verify">لاگین با شماره تلفن</a> - برای ورود با شماره تلفن تنظیم شده</li>
        <li><a href="/verify_otp?otp=CODE">تأیید کد OTP</a> - برای تأیید کد ارسال شده (CODE را با کد واقعی جایگزین کنید)</li>
        <li><a href="/forward_messages">فوروارد پیام‌ها</a> - برای فوروارد پیام‌های خوانده نشده از کانال مبدأ به کانال مقصد</li>
    </ul>
    """


if __name__ == '__main__':
    app.run(port=5000, debug=True)
