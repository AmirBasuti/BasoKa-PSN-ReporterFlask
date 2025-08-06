# 🚀 Quick Setup Guide for BasoKa Flask Reporter

## 📋 What you need to do:

### 1. Install Dependencies
```bash
uv sync
# This installs Flask, Selenium, and other required packages
```

### 2. Install ChromeDriver
- Download ChromeDriver from: https://chromedriver.chromium.org/
- Make sure it matches your Chrome browser version
- Add ChromeDriver to your system PATH

### 3. Replace the Selenium Bot Code
- Open `checker.py`
- Replace the example code with your actual Selenium automation
- Update these sections:
  - `LOGIN_URL` - Your actual login page URL
  - Login form selectors (username field, password field, submit button)
  - Success/failure detection logic
  - Your actual credentials source

### 4. Start the Flask Server
```bash
python main.py
```

### 5. Test with your Telegram Bot
Your bot will use these endpoints:
- `GET /status` - Get login statistics and process status
- `POST /start` - Start your Selenium bot (headless mode)
- `POST /stop` - Stop your Selenium bot
- `GET /is_running` - Check if bot is running
- `GET /log` - Get recent logs

## 🎯 Key Features for Selenium:

✅ **Headless Mode** - Browser runs invisibly in background
✅ **No Mouse/Screen Interference** - Won't affect your desktop
✅ **Stealth Options** - Harder to detect as automated browser
✅ **Error Handling** - Robust error logging and recovery
✅ **Process Management** - Start/stop via Telegram commands

## 📁 Final File Structure:
```
BasoKa_flaskReporter/
├── main.py           # ✨ Your Flask server
├── checker.py        # 🤖 Your Selenium bot (EDIT THIS)
├── test_server.py    # 🧪 For testing endpoints
├── logs/             # 📄 Log files
└── *.json            # 📊 Login data files
```

That's it! Your Flask server will manage your Selenium bot via Telegram commands.
