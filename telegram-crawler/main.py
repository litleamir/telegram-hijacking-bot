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
PHONE_NUMBER = "9966038413"  # شماره تلفن (بدون کد کشور)
SOURCE_CHANNELS = ['@JahanTasnim', '@EtemadOnline', '@iribnews', '@akharinkhabar', '@didebaniran', '@HamshahriNews', '@JamejamDaily', '@serfan_jahate_ettela', '@jamarannews','@chandsanieh_news','@YjcNewsChannel','@isna94', '@Mehrnews', '@snntv','@Farsna','@Entekhab_ir']  
#SOURCE_CHANNELS = ['@slxpemaple']
TARGET_CHANNEL = "@amiralitesttesttestbotbotbot"  # کانال مقصد

COOKIES_FILE_PATH = 'telegram_cookies.pkl'
driver = None
current_source_index = 0  # برای پیگیری کانال مبدأ فعلی



def initialize_driver():
    """Initialize WebDriver"""
    global driver
    if driver is None:
        print("[+] Initializing WebDriver...")
        try:
            # مسیر مناسب برای لینوکس
            chromedriver_path = r"/usr/local/bin/chromedriver"
            
            if not os.path.exists(chromedriver_path):
                print(f"[X] ChromeDriver not found at: {chromedriver_path}")
                return None
                
            print(f"[+] Using ChromeDriver at: {chromedriver_path}")
            service = Service(executable_path=chromedriver_path)
            options = webdriver.ChromeOptions()
            # Enable headless mode
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--disable-notifications")
            
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
#        if load_cookies(driver, COOKIES_FILE_PATH):
 #           print("[+] Refreshing page after loading cookies...")
  #          driver.refresh()
   #         time.sleep(5)
            
            # Check if cookies are still valid
    #        if check_cookies_valid(driver):
   #             print("[+] Already logged in with valid cookies!")
     #           return jsonify({'message': 'Already logged in with cookies'})
      #      else:
       #         print("[!] Cookies are invalid, proceeding with login...")
        
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
            ActionChains(driver).move_to_element(code_input).click().perform()
            code_input.clear()
            code_input.send_keys("IR")

            element = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[contains(@class, 'MenuItem') and contains(@class, 'compact')]"))
            )
            ActionChains(driver).move_to_element(element).click().perform()
            try:
                element = WebDreiverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'MenuItem') and contains(@class, 'compat')]")))
                ActionChains(driver).move_to_element(element).click().perform()
            except:
            	print("country dropdown cliked")
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
    global driver, current_source_index
    
    if not SOURCE_CHANNELS:
        return jsonify({'error': 'No source channels configured'})
        
    otp_code = request.args.get('otp')
    if not otp_code:
        return jsonify({'error': 'OTP is required! Use: /verify_otp?otp=CODE'})

    if driver is None:
        return jsonify({'error': 'Driver not initialized'})

    try:
        print(f"[+] Entering OTP: {otp_code}")
        otp_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@id='sign-in-code']"))
        )
        otp_input.clear()
        otp_input.send_keys(otp_code)
        
        # Wait for either success or error message
        try:
            # Check for error message (invalid code)
            error_message = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@aria-label, 'Invalid code, please try again')]"))
            )
            if error_message and "Invalid code" in error_message.text:
                print("[!] Invalid OTP code")
                driver.quit()
                return jsonify({"status": "error", "message": "کد تأیید اشتباه است. لطفاً کد صحیح را وارد کنید."})
        except:
            # If no error message, check for success
            try:
                # Wait for the main page to load (indicating successful login)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@id, 'Main')]"))
                )
                print("[+] OTP verification successful")
                
                # Continue with message forwarding for each source channel
                while current_source_index < len(SOURCE_CHANNELS):
                    current_source = SOURCE_CHANNELS[current_source_index]
                    print(f"[+] Processing source channel {current_source_index + 1}/{len(SOURCE_CHANNELS)}: {current_source}")
                    
                    try:
                        # Search for current source channel
                        search_input = WebDriverWait(driver, 20).until(
                            EC.element_to_be_clickable((By.XPATH, "//input[@id='telegram-search-input']"))
                        )
                        ActionChains(driver).move_to_element(search_input).click().perform()
                        time.sleep(1)
                        search_input.clear()
                        time.sleep(1)
                        search_input.send_keys(current_source)
                        print(f"[+] Searching for source channel: {current_source}")
                        time.sleep(2)

                        first_item = WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located(
                                (By.XPATH, "(//div[contains(@class, 'ChatInfo')])[1]"))
                        )
                        ActionChains(driver).move_to_element(first_item).click().perform()
                        print(f"[+] Channel {current_source} opened")
                        time.sleep(2)

                        try:
                            unread_divider = WebDriverWait(driver, 20).until(
                                EC.presence_of_element_located((By.XPATH, "//div[@class='unread-divider local-action-message']"))
                            )
                            print("✅ unread divider found")

                            # Process messages for current channel
                            if process_messages_for_channel(driver, current_source):
                                print(f"[+] Successfully processed messages for channel {current_source}")
                                current_source_index += 1
                            else:
                                print(f"[!] Failed to process messages for channel {current_source}, retrying...")
                                time.sleep(2)
                                continue
                                
                        except Exception as e:
                            print(f"[!] No unread messages in channel {current_source}: {str(e)}")
                            current_source_index += 1
                            time.sleep(2)
                            continue
                            
                    except Exception as e:
                        print(f"[!] Error accessing channel {current_source}: {str(e)}")
                        time.sleep(2)
                        continue
                        
                # If we've processed all channels
                if current_source_index >= len(SOURCE_CHANNELS):
                    driver.quit()
                    return jsonify({
                        'status': 'info',
                        'message': '✅ تمام پیام‌های همه کانال‌ها خوانده شده‌اند.'
                    })

            except Exception as e:
                print(f"[!] Error processing channels: {str(e)}")
                driver.quit()
                return jsonify({
                    'status': 'error',
                    'message': f'خطا در پردازش کانال‌ها: {str(e)}'
                })

    except Exception as e:
        print(f"[X] Error: {str(e)}")
        if driver:
            driver.quit()
        return jsonify({'error': str(e)})


def process_messages_for_channel(driver, source_channel):
    """Process unread messages for a specific channel"""
    try:
        # Scroll to unread divider once
        unread_divider = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='unread-divider local-action-message']"))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", unread_divider)
        time.sleep(2)

        # Find the first message after unread divider
        first_message = unread_divider.find_element(By.XPATH, "./following::div[contains(@class, 'Message')][1]")
        print("✅ first message found")

        # Right click on first message to open context menu
        ActionChains(driver).context_click(first_message).perform()
        time.sleep(1)

        # Click Select option
        select_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[@class='MenuItem compact' and text()='Select']")
            )
        )
        select_button.click()
        time.sleep(1)

        # Get all unread messages after the divider
        messages = driver.find_elements(By.XPATH, 
            "//div[@class='unread-divider local-action-message']/following::div[contains(@class, 'Message') and contains(@class, 'message-list-item') and not(contains(@class, 'is-selected')) and not(contains(@class, 'message-date-group'))]")
        
        if not messages:
            print(f"[!] No unread messages found in channel {source_channel}")
            return False
        
        print(f"[+] Found {len(messages)} messages to select in channel {source_channel}")
        
        # Select messages in small batches
        batch_size = 2
        selected_count = 0
        retry_count = 0
        max_retries = 3
        
        while selected_count < len(messages) and retry_count < max_retries:
            for i in range(0, len(messages), batch_size):
                batch = messages[i:i + batch_size]
                for msg in batch:
                    try:
                        msg_class = msg.get_attribute('class')
                        if msg_class and 'is-selected' not in msg_class and 'message-list-item' in msg_class:
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", msg)
                            time.sleep(0.5)
                            ActionChains(driver).move_to_element(msg).click().perform()
                            selected_count += 1
                            if selected_count >= len(messages):
                                break
                    except Exception as e:
                        print(f"[!] Could not select message: {str(e)}")
                        continue
                
                if selected_count >= len(messages):
                    break
                    
            if selected_count < len(messages):
                retry_count += 1
                print(f"[!] Retrying message selection (attempt {retry_count}/{max_retries})")
                time.sleep(1)

        print(f"[+] Selected {selected_count} messages from channel {source_channel}")

        # Forward selected messages
        forward_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[@role='button' and @title='Forward Messages' and not(contains(@class, 'copy'))]"))
        )
        forward_button.click()
        time.sleep(2)

        # Search for target channel
        search_input = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@class='form-control']"))
        )
        search_input.send_keys(TARGET_CHANNEL)
        time.sleep(2)

        # Click first result
        first_result = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@class='ripple-container']"))
        )
        first_result.click()
        time.sleep(2)

        # Click send button
        send_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'send') and contains(@class, 'Button')]"))
        )
        send_button.click()
        time.sleep(3)
        
        return True
        
    except Exception as e:
        print(f"[!] Error processing messages for channel {source_channel}: {str(e)}")
        return False


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
    app.run(port=5000, debug=False)
