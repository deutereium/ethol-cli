# Ethol CLI (Command Line Interface)

## Features
- Automatic login via CAS (no API endpoint needed)
- cached login session into a cookie
- quick auto-attend script
- Optional ethol notification polling 
- Sends new notifications to a Telegram chat (via bot token)

## Notifier
1. **Clone the repository**
2. **Copy the `.env.example` file**
   ```bash
   cp .env.example .env
   ```
3. **Edit your `.env` credential**
4. **Install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
5. **quick run the notifier:**
   ```bash
   python main.py
   ```
   
## Attend Script
1. **Copy the `.env.example` file**
   ```bash
   cp .env.example .env
   ```
2. **Edit your `.env` credential**
3. **Run the `attend.py` script**
   ```bash
   python3 attend.py
   ```
