import os
import sqlite3
import tempfile
import requests
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from PIL import Image, ImageDraw
import io
import subprocess
import threading
import time
import re

# Load environment variables
load_dotenv()

# Get bot token from environment variable
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Store the target group and channel IDs
target_group_id = None
target_channel_id = None
waiting_for_channel = False

# متغیرهای مربوط به کرالر
crawler_process = None
waiting_for_otp = False
otp_user_id = None
waiting_for_source_channel = False
waiting_for_target_channel = False
source_channel = None
target_channel = None

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    # Register datetime adapter
    def adapt_datetime(dt):
        return dt.isoformat()
    
    def convert_datetime(s):
        return datetime.fromisoformat(s)
    
    sqlite3.register_adapter(datetime, adapt_datetime)
    sqlite3.register_converter("datetime", convert_datetime)
    
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (message_id INTEGER PRIMARY KEY,
                  chat_id INTEGER,
                  photo_path TEXT,
                  original_photo_path TEXT,
                  status TEXT,
                  timestamp datetime)''')
    conn.commit()
    conn.close()

# Create temporary directory for photos
TEMP_DIR = "temp_photos"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_message = [
        "👋 سلام به ربات مدیریت کانال خوش آمدید!",
        "",
        "🔹 برای شروع کار، باید گروه و کانال هدف را تنظیم کنید:",
        "",
        "1️⃣ ابتدا ربات را در گروه مورد نظر اضافه کرده و دستور /set_group را در آنجا اجرا کنید.",
        "2️⃣ سپس دستور /set_channel را بزنید و یک پیام از کانال هدف فوروارد کنید.",
        "",
        "📢 برای مدیریت کرالر از دستورات زیر استفاده کنید:",
        "• /set_source_channel - تنظیم کانال مبدأ",
        "• /set_target_channel - تنظیم کانال مقصد (به صورت پیش‌فرض همین ربات)",
        "• /run - اجرای کرالر",
        "",
        "🔍 دستورات مفید:",
        "• /help - مشاهده همه دستورات",
        "• /status - مشاهده وضعیت فعلی ربات"
    ]
    
    await update.message.reply_text("\n".join(welcome_message))

async def set_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setgroup command to set target group"""
    global target_group_id
    
    print(f"Received set_group command in chat: {update.message.chat.id}, type: {update.message.chat.type}")
    
    if not update.message.chat.type in ['group', 'supergroup']:
        print("Error: Not in a group or supergroup")
        await update.message.reply_text("⚠️ این دستور فقط در گروه قابل استفاده است.\n\nلطفاً در گروه هدف، ربات را ادد کرده و دستور /setgroup را در آنجا اجرا کنید.\n\nنوع چت فعلی: " + update.message.chat.type)
        return
    
    try:
        # بررسی دسترسی‌های ربات در گروه
        chat = await context.bot.get_chat(update.message.chat.id)
        bot_member = await chat.get_member(context.bot.id)
        
        # بررسی آیا ربات به عنوان ادمین اضافه شده است
        if not bot_member.status in ['administrator', 'creator']:
            await update.message.reply_text("⚠️ لطفاً ربات را به عنوان ادمین در گروه اضافه کنید تا بتواند به درستی کار کند.")
            return
        
        target_group_id = update.message.chat.id
        print(f"Target group set successfully: {target_group_id}")
        await update.message.reply_text(f"✅ گروه هدف با موفقیت تنظیم شد!\n\nگروه: {chat.title}\nشناسه: {target_group_id}\n\nحالا لطفاً دستور /set_channel را بزنید و سپس یک پیام از کانال مورد نظر را فوروارد کنید.")
    
    except Exception as e:
        print(f"Error in set_group: {str(e)}")
        await update.message.reply_text(f"❌ خطا در تنظیم گروه هدف: {str(e)}")

async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setchannel command to start channel setting process"""
    global waiting_for_channel
    
    print(f"Received set_channel command from user: {update.effective_user.id}")
    
    if not target_group_id:
        await update.message.reply_text("⚠️ ابتدا باید گروه هدف را تنظیم کنید!\n\nلطفاً دستور /set_group را در گروه مورد نظر اجرا کنید.")
        return
    
    waiting_for_channel = True
    await update.message.reply_text("🔄 لطفاً یک پیام از کانال مورد نظر را فوروارد کنید.\n\n⚠️ توجه: ربات باید در کانال مورد نظر عضو باشد تا بتواند پیام‌ها را ارسال کند.")

async def set_source_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیم کانال مبدأ برای کرالر"""
    global waiting_for_source_channel
    waiting_for_source_channel = True
    await update.message.reply_text("لطفاً نام کانال مبدأ را وارد کنید (مثال: @BINNER_IRAN)")

async def set_target_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیم کانال مقصد برای کرالر"""
    global waiting_for_target_channel, target_channel
    
    # تنظیم مستقیم آیدی ربات به عنوان کانال مقصد کرالر
    target_channel = "@amiralitesttesttestbotbotbot"
    
    # بروزرسانی فایل کرالر
    if await update_crawler_settings(target=target_channel):
        await update.message.reply_text(f"✅ کانال مقصد کرالر با موفقیت به '{target_channel}' تنظیم شد.")
    else:
        await update.message.reply_text("❌ خطا در بروزرسانی تنظیمات کرالر!")

def create_main_keyboard():
    """Create the main inline keyboard with three buttons"""
    keyboard = [
        [
            InlineKeyboardButton("حذف واتر مارک", callback_data="remove_watermark"),
            InlineKeyboardButton("تایید", callback_data="approve")
        ],
        [
            InlineKeyboardButton("حذف همه لینک‌ها", callback_data="remove_links"),
            InlineKeyboardButton("رد", callback_data="reject")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_text_keyboard():
    """Create keyboard for text messages"""
    keyboard = [
        [
            InlineKeyboardButton("حذف همه لینک‌ها", callback_data="remove_links"),
            InlineKeyboardButton("تایید", callback_data="approve")
        ],
        [InlineKeyboardButton("رد", callback_data="reject")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_watermark_keyboard():
    """Create the watermark removal direction keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("از بالا", callback_data="from_top"),
            InlineKeyboardButton("از پایین", callback_data="from_bottom")
        ],
        [InlineKeyboardButton("بازگشت", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_unit_keyboard():
    """Create the unit selection keyboard (1-10)"""
    keyboard = []
    row = []
    for i in range(1, 11):
        row.append(InlineKeyboardButton(str(i), callback_data=f"unit_{i}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def remove_links_from_text(text):
    """Remove all links from text"""
    # Split text into lines to preserve line breaks
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Remove URLs
        line = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', line)
        # Remove t.me links
        line = re.sub(r't\.me/[a-zA-Z0-9_]+', '', line)
        # Remove @username
        line = re.sub(r'@[a-zA-Z0-9_]+', '', line)
        # Clean up multiple spaces
        line = re.sub(r'\s+', ' ', line)
        # Add line if it's not empty after cleaning
        if line.strip():
            cleaned_lines.append(line.strip())
    
    # Join lines back together with line breaks
    return '\n'.join(cleaned_lines)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all messages except commands"""
    global target_channel_id, waiting_for_channel, waiting_for_otp, waiting_for_source_channel, waiting_for_target_channel, source_channel, target_channel
    
    # چاپ اطلاعات پیام برای اشکال‌زدایی
    print(f"Message received from user {update.effective_user.id} in chat {update.effective_chat.id}")
    
    # اگر پیام از یک کانال است، پردازش نکن
    if update.effective_chat.type in ['channel']:
        print("Message from channel, skipping processing")
        return
    
    # اگر منتظر OTP هستیم، پیام را به تابع مربوطه ارسال کن
    if waiting_for_otp and update.effective_user.id == otp_user_id:
        await handle_otp_message(update, context)
        return
    
    # تنظیم کانال مبدأ کرالر
    if waiting_for_source_channel:
        source_channel = update.message.text.strip()
        if not source_channel.startswith('@'):
            source_channel = '@' + source_channel
        waiting_for_source_channel = False
        
        # بروزرسانی فایل کرالر
        if await update_crawler_settings(source=source_channel):
            await update.message.reply_text(f"✅ کانال مبدأ با موفقیت به '{source_channel}' تغییر یافت.")
        else:
            await update.message.reply_text("❌ خطا در بروزرسانی تنظیمات کرالر!")
        return
    
    # تنظیم کانال مقصد کرالر
    if waiting_for_target_channel:
        target_channel = update.message.text.strip()
        if not target_channel.startswith('@'):
            target_channel = '@' + target_channel
        waiting_for_target_channel = False
        
        # بروزرسانی فایل کرالر
        if await update_crawler_settings(target=target_channel):
            await update.message.reply_text(f"✅ کانال مقصد با موفقیت به '{target_channel}' تغییر یافت.")
        else:
            await update.message.reply_text("❌ خطا در بروزرسانی تنظیمات کرالر!")
        return
    
    # Handle channel setting if waiting for channel
    if waiting_for_channel:
        if not update.message.forward_from_chat:
            print("Error: Message not forwarded from chat")
            await update.message.reply_text("⚠️ لطفاً پیام را مستقیماً از کانال فوروارد کنید!")
            return
        
        if update.message.forward_from_chat.type != 'channel':
            print(f"Error: Chat type is {update.message.forward_from_chat.type}, not channel")
            await update.message.reply_text(f"⚠️ لطفاً پیام را از یک کانال فوروارد کنید! (نوع فعلی: {update.message.forward_from_chat.type})")
            return
        
        # تنظیم کانال هدف
        target_channel_id = update.message.forward_from_chat.id
        waiting_for_channel = False
        
        try:
            # بررسی دسترسی به کانال
            channel_info = await context.bot.get_chat(target_channel_id)
            
            # بررسی آیا ربات عضو کانال هست
            try:
                bot_member = await channel_info.get_member(context.bot.id)
                is_member = bot_member.status in ['administrator', 'member', 'creator']
            except Exception:
                is_member = False
            
            success_message = [
                f"✅ کانال هدف با موفقیت تنظیم شد!",
                f"📢 کانال: {channel_info.title}",
                f"🆔 شناسه: {target_channel_id}"
            ]
            
            if not is_member:
                success_message.append("\n⚠️ توجه: ربات باید در کانال عضو باشد تا بتواند پیام ارسال کند.")
                success_message.append("لطفاً ربات را به کانال اضافه کنید.")
            
            await update.message.reply_text("\n".join(success_message))
            
        except Exception as e:
            print(f"Error checking channel: {str(e)}")
            await update.message.reply_text(f"⚠️ کانال هدف تنظیم شد، اما ممکن است ربات دسترسی کامل نداشته باشد: {str(e)}")
        
        return
    
    # Handle normal messages
    if not target_group_id:
        await update.message.reply_text("⚠️ لطفاً ابتدا گروه هدف را تنظیم کنید!\n\nاز دستور /set_group استفاده کنید.")
        return
    
    # Skip if it's a command
    if update.message.text and update.message.text.startswith('/'):
        return
    
    # Handle text messages
    if update.message.text:
        text = update.message.text
        # Send the text with keyboard
        text_message = await context.bot.send_message(
            chat_id=target_group_id,
            text=text,
            reply_markup=create_text_keyboard()
        )
        
        # Save to database with datetime handling
        conn = sqlite3.connect('bot_data.db', detect_types=sqlite3.PARSE_DECLTYPES)
        c = conn.cursor()
        c.execute('''INSERT INTO messages (message_id, chat_id, photo_path, original_photo_path, status, timestamp)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (text_message.message_id, target_group_id, None, None, 'pending', datetime.now()))
        conn.commit()
        conn.close()
        
        await update.message.reply_text("✅ پیام متنی به گروه ارسال شد.")
    
    # Handle photos
    elif update.message.photo:
        await handle_photo(update, context)
    
    # Handle videos
    elif update.message.video:
        video = update.message.video
        caption = update.message.caption or ""
        
        # Download the video
        video_file = await context.bot.get_file(video.file_id)
        
        # Save original video
        original_path = os.path.join(TEMP_DIR, f"original_{video.file_id}.mp4")
        await video_file.download_to_drive(original_path)
        
        # Send to target group with inline keyboard
        sent_message = await context.bot.send_video(
            chat_id=target_group_id,
            video=open(original_path, 'rb'),
            caption=caption,
            reply_markup=create_main_keyboard()
        )
        
        # Save to database
        conn = sqlite3.connect('bot_data.db', detect_types=sqlite3.PARSE_DECLTYPES)
        c = conn.cursor()
        c.execute('''INSERT INTO messages (message_id, chat_id, photo_path, original_photo_path, status, timestamp)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (sent_message.message_id, target_group_id, original_path, original_path, 'pending', datetime.now()))
        conn.commit()
        conn.close()
        
        await update.message.reply_text("✅ ویدیو به گروه ارسال شد.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages"""
    if not target_group_id or not target_channel_id:
        await update.message.reply_text("⚠️ لطفاً ابتدا گروه و کانال هدف را تنظیم کنید!")
        return
    
    photo = update.message.photo[-1]
    caption = update.message.caption or ""
    
    # Download the photo
    photo_file = await context.bot.get_file(photo.file_id)
    
    # Save original photo
    original_path = os.path.join(TEMP_DIR, f"original_{photo.file_id}.jpg")
    await photo_file.download_to_drive(original_path)
    
    # Send to target group with inline keyboard
    sent_message = await context.bot.send_photo(
        chat_id=target_group_id,
        photo=open(original_path, 'rb'),
        caption=caption,
        reply_markup=create_main_keyboard()
    )
    
    # Save to database with datetime handling
    conn = sqlite3.connect('bot_data.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('''INSERT INTO messages (message_id, chat_id, photo_path, original_photo_path, status, timestamp)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (sent_message.message_id, target_group_id, original_path, original_path, 'pending', datetime.now()))
    conn.commit()
    conn.close()
    
    await update.message.reply_text("✅ تصویر به گروه ارسال شد.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect('bot_data.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    
    if query.data == "approve":
        # Get photo path (cropped if exists, otherwise original)
        c.execute('SELECT photo_path, original_photo_path FROM messages WHERE message_id = ?', (query.message.message_id,))
        result = c.fetchone()
        if result:
            photo_path = result[0]
            caption = query.message.caption or ""
            
            # If it's a text message
            if not photo_path:
                await context.bot.send_message(
                    chat_id=target_channel_id,
                    text=query.message.text
                )
            # If it's a photo or video
            else:
                if photo_path.endswith('.mp4'):
                    await context.bot.send_video(
                        chat_id=target_channel_id,
                        video=open(photo_path, 'rb'),
                        caption=caption
                    )
                else:
                    await context.bot.send_photo(
                        chat_id=target_channel_id,
                        photo=open(photo_path, 'rb'),
                        caption=caption
                    )
            
            # Delete from group
            await query.message.delete()
    
    elif query.data == "reject":
        # Just delete from group
        await query.message.delete()
    
    elif query.data == "remove_links":
        # Get current caption or text
        caption = query.message.caption or query.message.text or ""
        # Remove links
        new_caption = remove_links_from_text(caption)
        
        # Update message with new caption/text
        if query.message.photo:
            await query.message.edit_caption(
                caption=new_caption,
                reply_markup=query.message.reply_markup
            )
        elif query.message.video:
            await query.message.edit_caption(
                caption=new_caption,
                reply_markup=query.message.reply_markup
            )
        else:
            await query.message.edit_text(
                text=new_caption,
                reply_markup=query.message.reply_markup
            )
    
    elif query.data == "remove_watermark":
        # Update keyboard to watermark removal options
        await query.message.edit_reply_markup(reply_markup=create_watermark_keyboard())
    
    elif query.data == "back_to_main":
        # Return to main keyboard
        await query.message.edit_reply_markup(reply_markup=create_main_keyboard())
    
    elif query.data in ["from_top", "from_bottom"]:
        # Get original photo
        c.execute('SELECT original_photo_path FROM messages WHERE message_id = ?', (query.message.message_id,))
        result = c.fetchone()
        if result:
            # Create divided image
            img = Image.open(result[0])
            draw = ImageDraw.Draw(img)
            width, height = img.size
            for i in range(1, 10):
                y = int(height * i / 10)
                draw.line([(0, y), (width, y)], fill='red', width=2)
            
            # Save divided image
            divided_path = os.path.join(TEMP_DIR, f"divided_{query.message.message_id}.jpg")
            img.save(divided_path)
            
            # Update message with divided image and unit selection keyboard
            await query.message.edit_media(
                media=InputMediaPhoto(media=open(divided_path, 'rb')),
                reply_markup=create_unit_keyboard()
            )
    
    elif query.data.startswith("unit_"):
        unit = int(query.data.split("_")[1])
        # Get original photo
        c.execute('SELECT original_photo_path FROM messages WHERE message_id = ?', (query.message.message_id,))
        result = c.fetchone()
        if result:
            # Crop image based on selected unit
            img = Image.open(result[0])
            width, height = img.size
            crop_height = height // 10
            
            if query.data == "from_top":
                cropped = img.crop((0, 0, width, unit * crop_height))
            else:  # from bottom
                # Remove units from bottom
                cropped = img.crop((0, 0, width, height - (unit * crop_height)))
            
            # Save cropped image
            cropped_path = os.path.join(TEMP_DIR, f"cropped_{query.message.message_id}.jpg")
            cropped.save(cropped_path)
            
            # Update database with cropped image path
            c.execute('UPDATE messages SET photo_path = ? WHERE message_id = ?', 
                     (cropped_path, query.message.message_id))
            conn.commit()
            
            # Update message with cropped image and main keyboard
            await query.message.edit_media(
                media=InputMediaPhoto(media=open(cropped_path, 'rb')),
                reply_markup=create_main_keyboard()
            )
    
    conn.close()

async def run_crawler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اجرای کرالر تلگرام"""
    global waiting_for_otp, otp_user_id, crawler_process
    
    # بررسی تنظیمات کانال‌ها
    if not source_channel:
        await update.message.reply_text("⚠️ کانال مبدأ هنوز تنظیم نشده است!\n\nلطفاً از دستور زیر استفاده کنید:\n/set_source_channel - تنظیم کانال مبدأ")
        return
    
    # بررسی فایل کرالر
    try:
        crawler_file_path = "telegram-crawler/main.py"
        if not os.path.exists(crawler_file_path):
            await update.message.reply_text(f"❌ خطا: فایل کرالر '{crawler_file_path}' یافت نشد!")
            return
            
        with open(crawler_file_path, "r", encoding="utf-8") as file:
            content = file.read()
            
            # بروزرسانی تنظیمات کرالر در فایل
            if await update_crawler_settings(source=source_channel, target=target_channel):
                await update.message.reply_text("✅ تنظیمات کرالر در فایل بروزرسانی شد.")
            else:
                await update.message.reply_text("❌ خطا در بروزرسانی تنظیمات کرالر در فایل!")
                return
    except Exception as e:
        print(f"Error checking crawler settings: {str(e)}")
        await update.message.reply_text(f"❌ خطا در بررسی تنظیمات کرالر: {str(e)}")
        return
    
    if crawler_process is not None and crawler_process.poll() is None:
        await update.message.reply_text("❌ کرالر در حال اجرا است.")
        return
    
    otp_user_id = update.effective_user.id
    waiting_for_otp = True
    
    await update.message.reply_text("🔄 در حال اجرای کرالر...\n\nلطفاً کد OTP را که به شماره تلفن شما ارسال شده وارد کنید.\n\nکانال مبدأ: " + source_channel + "\nکانال مقصد: " + target_channel)
    
    # شروع کرالر به صورت زیرپروسس
    try:
        crawler_thread = threading.Thread(target=run_crawler_thread, args=(update, context))
        crawler_thread.start()
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در اجرای کرالر: {str(e)}")


def run_crawler_thread(update, context):
    """اجرای کرالر در یک ترد جدا"""
    global waiting_for_otp, otp_user_id
    
    try:
        # اجرای لاگین کرالر
        response = requests.get('http://localhost:5000/login_and_verify')
        if response.status_code == 200:
            # اگر نیاز به وارد کردن OTP بود
            if "شماره تلفن ارسال شد" in response.json().get('message', ''):
                waiting_for_otp = True
                # ارسال پیام درخواست OTP به کاربر
                context.bot.send_message(
                    chat_id=otp_user_id,
                    text="لطفاً کد تأیید ارسال شده به تلفن را وارد کنید:"
                )
            else:
                # اگر قبلاً لاگین شده بود، مستقیم فوروارد را اجرا کن
                context.bot.send_message(
                    chat_id=otp_user_id,
                    text="کرالر با موفقیت لاگین شده است. در حال اجرای عملیات فوروارد..."
                )
                forward_response = requests.get('http://localhost:5000/forward_messages')
                if forward_response.status_code == 200:
                    context.bot.send_message(
                        chat_id=otp_user_id,
                        text="✅ عملیات فوروارد با موفقیت انجام شد."
                    )
                else:
                    context.bot.send_message(
                        chat_id=otp_user_id,
                        text=f"❌ خطا در فوروارد پیام‌ها: {forward_response.json()}"
                    )
    except Exception as e:
        context.bot.send_message(
            chat_id=otp_user_id,
            text=f"❌ خطا در اجرای کرالر: {str(e)}"
        )


async def handle_otp_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش کد OTP ارسال شده توسط کاربر"""
    global waiting_for_otp, otp_user_id
    
    # اگر منتظر OTP نیستیم یا کاربر متفاوت است، پردازش نکن
    if not waiting_for_otp or update.effective_user.id != otp_user_id:
        return
    
    otp_code = update.message.text.strip()
    # بررسی کن که پیام فقط شامل اعداد باشد
    if not otp_code.isdigit():
        await update.message.reply_text("❌ لطفاً فقط عدد وارد کنید!")
        return
    
    await update.message.reply_text(f"دریافت کد تأیید: {otp_code}")
    waiting_for_otp = False
    
    try:
        # ارسال OTP به کرالر
        response = requests.get(f'http://localhost:5000/verify_otp?otp={otp_code}')
        if response.status_code == 200:
            await update.message.reply_text("✅ لاگین با موفقیت انجام شد. در حال فوروارد پیام‌ها...")
            
            # پیام‌ها در حال فوروارد شدن هستند، منتظر نتیجه می‌مانیم
            if "Messages forwarded successfully" in response.json().get('message', ''):
                await update.message.reply_text("✅ عملیات فوروارد با موفقیت انجام شد.")
            else:
                await update.message.reply_text("✅ عملیات فوروارد با موفقیت انجام شد.")
        else:
            error_message = response.json().get('error', 'خطای نامشخص')
            await update.message.reply_text(f"❌ خطا در تأیید OTP: {error_message}")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

async def update_crawler_settings(source=None, target=None):
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
            source_pattern = r'SOURCE_CHANNEL\s*=\s*"@[^"]*"'
            if re.search(source_pattern, content):
                content = re.sub(source_pattern, f'SOURCE_CHANNEL = "{source}"', content)
            else:
                print(f"Warning: Could not find SOURCE_CHANNEL pattern in crawler file")
                # تلاش برای جایگزینی با الگوی دقیق
                content = content.replace(
                    'SOURCE_CHANNEL = "@BINNER_IRAN"',
                    f'SOURCE_CHANNEL = "{source}"'
                )
        
        if target:
            # جستجوی الگو برای جایگزینی کانال مقصد
            target_pattern = r'TARGET_CHANNEL\s*=\s*"@[^"]*"'
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

async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for debugging all commands"""
    command = update.message.text
    chat_id = update.message.chat.id
    chat_type = update.message.chat.type
    user_id = update.effective_user.id
    
    print(f"DEBUG - Received command: {command}")
    print(f"DEBUG - From user: {user_id}")
    print(f"DEBUG - In chat: {chat_id}, type: {chat_type}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help command - shows all available commands"""
    help_text = [
        "🔍 راهنمای دستورات:",
        "",
        "• /start - شروع کار با ربات",
        "• /set_group یا /setgroup - تنظیم گروه هدف (باید در گروه ارسال شود)",
        "• /set_channel یا /setchannel - تنظیم کانال هدف (فوروارد پیام)",
        "• /set_source_channel - تنظیم کانال مبدأ برای کرالر",
        "• /set_target_channel - تنظیم کانال مقصد کرالر (به صورت پیش‌فرض ربات فعلی)",
        "• /run - اجرای کرالر",
        "• /status - نمایش وضعیت فعلی ربات و تنظیمات آن"
    ]
    
    await update.message.reply_text("\n".join(help_text))

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش وضعیت فعلی ربات و تنظیمات آن"""
    status_info = [
        "📊 وضعیت ربات:"
    ]
    
    # بررسی وضعیت گروه هدف
    if target_group_id:
        try:
            chat = await context.bot.get_chat(target_group_id)
            status_info.append(f"✅ گروه هدف: {chat.title} (ID: {target_group_id})")
        except Exception:
            status_info.append(f"⚠️ گروه هدف: تنظیم شده اما در دسترس نیست (ID: {target_group_id})")
    else:
        status_info.append("❌ گروه هدف: تنظیم نشده - از دستور /set_group یا /setgroup استفاده کنید")
    
    # بررسی وضعیت کانال هدف
    if target_channel_id:
        try:
            chat = await context.bot.get_chat(target_channel_id)
            status_info.append(f"✅ کانال هدف: {chat.title} (ID: {target_channel_id})")
        except Exception:
            status_info.append(f"⚠️ کانال هدف: تنظیم شده اما در دسترس نیست (ID: {target_channel_id})")
    else:
        status_info.append("❌ کانال هدف: تنظیم نشده - از دستور /set_channel یا /setchannel استفاده کنید")
    
    # بررسی وضعیت کرالر
    status_info.append("\n📱 وضعیت کرالر:")
    
    if source_channel:
        status_info.append(f"✅ کانال مبدأ: {source_channel}")
    else:
        status_info.append("❌ کانال مبدأ: تنظیم نشده - از دستور /set_source_channel استفاده کنید")
    
    if target_channel:
        status_info.append(f"✅ کانال مقصد: {target_channel}")
    else:
        status_info.append("❌ کانال مقصد: تنظیم نشده - از دستور /set_target_channel استفاده کنید")
    
    # وضعیت فرایند کرالر
    if crawler_process is not None and crawler_process.poll() is None:
        status_info.append("✅ کرالر: در حال اجرا")
    else:
        status_info.append("❌ کرالر: غیرفعال - از دستور /run برای اجرا استفاده کنید")
    
    # راهنمای دستورات
    status_info.append("\n🔍 دستورات مفید:")
    status_info.append("• /help - نمایش همه دستورات")
    
    await update.message.reply_text("\n".join(status_info))

def main():
    # ایجاد اپلیکیشن ربات
    try:
        print("Initializing bot application...")
        application = Application.builder().token(TOKEN).build()
        
        # اضافه کردن هندلر اشکال‌زدایی برای همه دستورات
        application.add_handler(MessageHandler(filters.COMMAND, debug_command), group=0)
        
        # اضافه کردن هندلرها
        print("Adding command handlers...")
        application.add_handler(CommandHandler("start", start), group=1)
        application.add_handler(CommandHandler("help", help_command), group=1)
        application.add_handler(CommandHandler("set_group", set_group), group=1)
        application.add_handler(CommandHandler("setgroup", set_group), group=1)
        application.add_handler(CommandHandler("set_channel", set_channel), group=1)
        application.add_handler(CommandHandler("setchannel", set_channel), group=1)
        application.add_handler(CommandHandler("set_source_channel", set_source_channel), group=1)
        application.add_handler(CommandHandler("set_target_channel", set_target_channel), group=1)
        application.add_handler(CommandHandler("run", run_crawler), group=1)
        application.add_handler(CommandHandler("status", status_command), group=1)
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo), group=1)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message), group=1)
        application.add_handler(CallbackQueryHandler(handle_callback), group=1)
        
        # تنظیم مدیریت کننده خطا
        application.add_error_handler(error_handler)
        
        # شروع ربات
        print("Bot started! Send /start and then use /set_group in your target group.")
        print(f"Bot token (first 5 chars): {TOKEN[:5]}...")
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        # در صورت خطای اولیه، سعی می‌کنیم توکن را بررسی کنیم
        if TOKEN is None or TOKEN == "":
            print("ERROR: Bot token is empty or not set. Please check your .env file.")
        else:
            print(f"Bot token length: {len(TOKEN)}")
            print(f"First 5 chars of token: {TOKEN[:5]}...")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors caused by updates."""
    # گزارش خطا در کنسول
    print(f"Exception while handling an update: {context.error}")
    
    # سعی می‌کنیم پیام را به کاربر ارسال کنیم
    if update and hasattr(update, 'effective_chat'):
        # اگر پیام از کانال است، پاسخ نده
        if update.effective_chat.type in ['channel']:
            print("Message from channel, skipping error message")
            return
            
        error_message = f"⚠️ خطایی رخ داد: {str(context.error)}"
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=error_message
            )
        except Exception as e:
            print(f"Failed to send error message: {e}")

if __name__ == '__main__':
    main() 