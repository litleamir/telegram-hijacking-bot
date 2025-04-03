import os
import pickle
import time
import base64
import requests
import re
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

# تنظیمات ثابت
PHONE_NUMBER = "9128517225"  # شماره تلفن ثابت (بدون کد کشور)
SOURCE_CHANNEL = "@slxpemaple"  # کانال مبدأ (فرمت @username)
TARGET_CHANNEL = "@amiralitesttesttestbotbotbot"  # کانال مقصد

COOKIES_FILE_PATH = 'telegram_cookies.pkl'
driver = None


def initialize_driver():
    """Initialize WebDriver"""
    global driver
    if driver is None:
        print("[+] Initializing WebDriver...")
        try:
            chromedriver_path = r"D:\python\project\telegram-hijacking-bot\telegram-crawler\chromedriver-win64\chromedriver-win64\chromedriver.exe"
            if not os.path.exists(chromedriver_path):
                print(f"[X] ChromeDriver not found at: {chromedriver_path}")
                return None
                
            print(f"[+] Using ChromeDriver at: {chromedriver_path}")
            service = Service(executable_path=chromedriver_path)
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")  # Use new headless mode
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--disable-notifications")
            options.add_argument("--window-size=1920,1080")  # Set a standard window size
            options.add_argument("--remote-debugging-port=9222")
            
            print("[+] Creating Chrome driver...")
            driver = webdriver.Chrome(service=service, options=options)
            print("[+] Chrome driver created successfully")
            
            return driver
        except Exception as e:
            print(f"[X] Error initializing driver: {str(e)}")
            return None
    return driver


def save_cookies(driver, path):
    """Save cookies after login"""
    print("[+] Saving cookies...")
    try:
        cookies = driver.get_cookies()
        # Filter out expired cookies and ensure proper domain format
        valid_cookies = []
        current_time = int(time.time())
        
        for cookie in cookies:
            # Skip expired cookies
            if 'expiry' in cookie and cookie['expiry'] <= current_time:
                continue
                
            # Ensure domain is properly formatted
            if 'domain' in cookie:
                cookie['domain'] = cookie['domain'].strip('.')
                if not cookie['domain']:
                    del cookie['domain']
                elif not cookie['domain'].startswith('.'):
                    cookie['domain'] = '.' + cookie['domain']
            
            # Convert expiry to integer if it's a float
            if 'expiry' in cookie:
                cookie['expiry'] = int(cookie['expiry'])
            
            valid_cookies.append(cookie)
            
        with open(path, 'wb') as filehandler:
            pickle.dump(valid_cookies, filehandler)
        print(f"[+] Cookies saved successfully to {path}")
        print(f"[+] Number of valid cookies saved: {len(valid_cookies)}")
    except Exception as e:
        print(f"[X] Error saving cookies: {str(e)}")


def load_cookies(driver, path):
    """Load cookies to maintain session"""
    if os.path.exists(path):
        print("[+] Loading cookies...")
        try:
            # First navigate to Telegram Web
            driver.get('https://web.telegram.org/a/')
            time.sleep(3)  # Wait for page to load
            
            with open(path, 'rb') as cookiesfile:
                cookies = pickle.load(cookiesfile)
                print(f"[+] Found {len(cookies)} cookies to load")
                
                # First delete all existing cookies
                driver.delete_all_cookies()
                
                # Add each cookie with proper domain handling
                for cookie in cookies:
                    try:
                        # Handle domain properly
                        if 'domain' in cookie:
                            cookie['domain'] = cookie['domain'].strip('.')
                            if not cookie['domain']:
                                del cookie['domain']
                            elif not cookie['domain'].startswith('.'):
                                cookie['domain'] = '.' + cookie['domain']
                        
                        # Handle expiry
                        if 'expiry' in cookie:
                            if cookie['expiry'] <= int(time.time()):
                                continue  # Skip expired cookies
                            cookie['expiry'] = int(cookie['expiry'])
                        
                        # Add cookie
                        driver.add_cookie(cookie)
                    except Exception as e:
                        print(f"[!] Could not add cookie: {str(e)}")
                        continue
                
                print("[+] Cookies loaded successfully")
                
                # Refresh page and wait for chat list
                driver.refresh()
                time.sleep(5)
                
                try:
                    # Check if we're logged in by looking for chat list
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'chat-list')]"))
                    )
                    print("[+] Successfully logged in with cookies!")
                    return True
                except:
                    print("[-] Cookies are invalid or expired")
                    return False
                
        except Exception as e:
            print(f"[X] Error loading cookies: {str(e)}")
            return False
    else:
        print(f"[-] Cookie file not found: {path}")
        return False


def check_cookies_valid(driver):
    """Check if current cookies are still valid"""
    try:
        # Try to access a protected Telegram Web page
        driver.get('https://web.telegram.org/a/')
        time.sleep(2)
        
        # Check if we're logged in by looking for chat list
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'chat-list')]"))
            )
            print("[+] Cookies are valid")
            return True
        except:
            print("[-] Cookies are invalid")
            return False
    except Exception as e:
        print(f"[X] Error checking cookies: {str(e)}")
        return False


@app.route('/login_and_verify', methods=['GET'])
def login_and_verify():
    """تابع جدید برای لاگین و ورود با شماره تلفن ثابت"""
    global driver
    try:
        print("[+] Starting login process...")
        driver = initialize_driver()
        if driver is None:
            return jsonify({'error': 'Failed to initialize driver'}), 500
            
        print("[+] Opening Telegram Web...")
        driver.get('https://web.telegram.org/a/')
        print("[+] Page loaded")
        
        time.sleep(5)  # Increased wait time
        
        # Try to load cookies first
        if load_cookies(driver, COOKIES_FILE_PATH):
            print("[+] Refreshing page after loading cookies...")
            driver.refresh()
            time.sleep(5)
            
            # Check if cookies are still valid
            if check_cookies_valid(driver):
                print("[+] Already logged in with valid cookies!")
                return jsonify({'message': 'Already logged in with cookies'})
            else:
                print("[!] Cookies are invalid, proceeding with login...")
        
        # اگر قبلاً لاگین شده باشد، این مرحله را رد می‌کند
        try:
            print("[+] Looking for login button...")
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@class='Button smaller primary text']"))
            )
            print("[+] Login button found")
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
            
            return jsonify({
                'message': 'لطفاً کد OTP را که به شماره تلفن شما ارسال شده وارد کنید.',
                'status': 'waiting_for_otp'
            })
        
        except Exception as e:
            print(f"[!] احتمالاً قبلاً لاگین شده‌اید یا خطایی رخ داده: {str(e)}")
            return jsonify({'message': 'احتمالاً قبلاً لاگین شده‌اید یا خطایی رخ داده است.'})
            
    except Exception as e:
        print(f"[X] Login error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/verify_otp', methods=['GET'])
def verify_otp():
    """Verify OTP code and continue with message forwarding"""
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

        # Continue with message forwarding
        print("[+] Starting message forwarding process...")
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
            unread_divider = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@class='unread-divider local-action-message']"))
            )
            print("✅ unread divider found")

            # Scroll to unread divider once
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", unread_divider)
            time.sleep(1)

            # Find the first message after unread divider
            first_message = unread_divider.find_element(By.XPATH, "./following::div[contains(@class, 'Message')][1]")
            print("✅ first message found")

            # Right click on first message to open context menu
            ActionChains(driver).context_click(first_message).perform()
            time.sleep(0.5)

            # Click Select option
            select_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[@class='MenuItem compact' and text()='Select']")
                )
            )
            select_button.click()
            time.sleep(0.5)

            # Get all unread messages after the divider
            messages = driver.find_elements(By.XPATH, 
                "//div[@class='unread-divider local-action-message']/following::div[contains(@class, 'Message') and contains(@class, 'message-list-item') and not(contains(@class, 'is-selected')) and not(contains(@class, 'message-date-group'))]")
            
            print(f"[+] Found {len(messages)} messages to select")
            
            # Select messages in small batches
            batch_size = 3
            selected_count = 0
            
            for i in range(0, len(messages), batch_size):
                batch = messages[i:i + batch_size]
                for msg in batch:
                    try:
                        # Check if message is already selected and is a valid message
                        msg_class = msg.get_attribute('class')
                        if msg_class and 'is-selected' not in msg_class and 'message-list-item' in msg_class:
                            # Scroll message into view smoothly
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", msg)
                            time.sleep(0.2)
                            
                            # Click the message
                            ActionChains(driver).move_to_element(msg).click().perform()
                            selected_count += 1
                            
                            # If we've selected all messages, break
                            if selected_count >= len(messages):
                                break
                    except Exception as e:
                        print(f"[!] Could not select message: {str(e)}")
                        continue
                
                # If we've selected all messages, break
                if selected_count >= len(messages):
                    break

            print(f"[+] Selected {selected_count} messages")

        except Exception as e:
            print(f"[X] خطا در انتخاب پیام‌ها: {str(e)}")

        try:
            # Try to find and click cancel button if it exists
            try:
                cancel_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@type='button' and text()='Cancel']"))
                )
                cancel_button.click()
                print("[+] Clicked cancel button")
            except:
                print("[!] No cancel button found, continuing...")  
            # Find and click forward button
            time.sleep(0.5)
            forward_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[@role='button' and @title='Forward Messages' and not(contains(@class, 'copy'))]"))
            )
            forward_button.click()
            time.sleep(1)  # Wait for forward dialog
            
            # Search for target channel
            search_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@class='form-control']"))
            )
            search_input.send_keys(f"{TARGET_CHANNEL}")
            time.sleep(1)  # Wait for search results
            
            # Click first result
            first_result = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@class='ripple-container']"))
            )
            first_result.click()
            time.sleep(1)  # Wait for selection
            
            # Click send button
            send_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'send') and contains(@class, 'Button')]"))
            )
            send_button.click()
            time.sleep(2)  # Wait for forwarding to complete
            driver.quit()
            return jsonify({'success': 'Messages forwarded successfully!'}), 200

        except Exception as e:
            print(f"[X] خطا در فوروارد پیام‌ها: {str(e)}")
            return jsonify({'error': f'Error forwarding messages: {str(e)}'}), 500

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


def update_crawler_settings(source=None, target=None):
    """بروزرسانی تنظیمات کرالر در فایل main.py"""
    try:
        crawler_file_path = "telegram-crawler/main.py"
        if not os.path.exists(crawler_file_path):
            print(f"Error: Crawler file '{crawler_file_path}' not found!")
            return False
            
        with open(crawler_file_path, "r", encoding="utf-8") as file:
            content = file.read()
        
        if source:
            # جستجوی الگو برای جایگزینی کانال مبدأ
            source_pattern = r'SOURCE_CHANNEL\s*=\s*["\']@?[^"\']*["\']'
            if re.search(source_pattern, content):
                content = re.sub(source_pattern, f'SOURCE_CHANNEL = "{source}"', content)
            else:
                print(f"Warning: Could not find SOURCE_CHANNEL pattern in crawler file")
                # تلاش برای جایگزینی با الگوی دقیق
                content = content.replace(
                    'SOURCE_CHANNEL = "@slxpemaple"',
                    f'SOURCE_CHANNEL = "{source}"'
                )
        
        if target:
            # جستجوی الگو برای جایگزینی کانال مقصد
            target_pattern = r'TARGET_CHANNEL\s*=\s*["\']@?[^"\']*["\']'
            if re.search(target_pattern, content):
                content = re.sub(target_pattern, f'TARGET_CHANNEL = "{target}"', content)
            else:
                print(f"Warning: Could not find TARGET_CHANNEL pattern in crawler file")
                # تلاش برای جایگزینی با الگوی دقیق
                content = content.replace(
                    'TARGET_CHANNEL = "@amiralitesttesttestbotbotbot"',
                    f'TARGET_CHANNEL = "{target}"'
                )
        
        with open(crawler_file_path, "w", encoding="utf-8") as file:
            file.write(content)
        
        return True
    except Exception as e:
        print(f"Error updating crawler settings: {str(e)}")
        return False


if __name__ == '__main__':
    app.run(port=5000, debug=True)
