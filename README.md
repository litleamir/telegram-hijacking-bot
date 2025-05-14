# Telegram Channel Management Bot

A Telegram bot for managing and forwarding messages between channels and groups.

## Features

- Set target group and channel
- Add multiple target channels
- Forward messages from source to target channels
- Handle photos and videos with watermark removal
- OTP verification for secure access
- Status monitoring and management

## Requirements

- Python 3.8+
- Telegram Bot Token
- Required Python packages (see requirements.txt)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/telegram-hijacking-bot.git
cd telegram-hijacking-bot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file and add your bot token:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

## Usage

1. Start the bot:
```bash
python bot.py
```

2. Available commands:
- `/start` - Start the bot and see available commands
- `/set_group` - Set target group
- `/set_channel` - Set target channel
- `/set_phone` - Set phone number for crawler
- `/add_target` - Add a new target channel
- `/remove_target` - Remove a target channel
- `/list_targets` - List all target channels
- `/status` - Show current status
- `/start_crawler` - Start the crawler
- `/stop_crawler` - Stop the crawler
- `/help` - Show help message

## Security Notes

- Never share your bot token or phone number
- Keep your `.env` file secure
- The bot requires admin privileges in the target group

## License

This project is licensed under the MIT License - see the LICENSE file for details. 