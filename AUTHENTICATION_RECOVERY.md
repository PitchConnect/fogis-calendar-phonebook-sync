# 🔄 Authentication Recovery Guide

## When You Miss the Authentication Window

If you miss the 30-minute authentication window, you have several options to restart the process:

### Option 1: Command Line Script (Simplest)
```bash
python restart_auth.py
```
- ✅ Simple one-command solution
- ✅ Shows current token status
- ✅ Sends fresh email with new 30-minute window

### Option 2: Web Interface (Most Convenient)
```bash
python auth_web_trigger.py
```
Then visit: http://localhost:8090

- ✅ Bookmark-friendly web interface
- ✅ Visual token status display
- ✅ One-click authentication restart
- ✅ Works from any device on your network

### Option 3: Container Restart (Nuclear Option)
```bash
docker-compose -f docker-compose-fogis.yml restart fogis-calendar-phonebook-sync
```
- ✅ Guaranteed fresh start
- ⚠️ Restarts the entire service

## Improved Authentication Windows

- **Old**: 10 minutes (too short!)
- **New**: 30 minutes (much more reasonable)
- **Frequency**: Every 6 days (instead of daily)

## Bookmark This!

For easiest access, bookmark: http://localhost:8090
(after running `python auth_web_trigger.py`)

## Pro Tips

1. **Set up the web interface** as a bookmark for instant access
2. **Check your email** regularly during the 6-day cycle
3. **Use the command line script** for quick terminal-based recovery
4. **The 30-minute window** gives you plenty of time to authenticate

Your FOGIS sync will now be much more forgiving! 🎉
