# 📱 iMessage Media Pipeline — Fully Working

> **All of this works with Claude Code (cloud) AND any model in the local lineup — Gemma 4 31B, Llama 3.3 70B, or Qwen 3.5 122B.**
> The scripts are pure shell/AppleScript — the AI just calls them. Model doesn't matter.

---

## ✅ Status — Everything Ships

| Feature | Status | How |
|---------|:---:|---|
| 📨 Receive text commands from phone | ✅ | SQLite poll on `~/Library/Messages/chat.db` |
| 💬 Send text replies to phone | ✅ | AppleScript → Messages |
| 🖼️ Send images to phone | ✅ | Clipboard copy → `open imessage://` → paste |
| 🎥 Send video to phone | ✅ | Finder Cmd+C → `open imessage://` → paste |
| 📹 Start/stop screen recording | ✅ | Studio Record HTTP API (port 17494) |
| 🎬 Build produced video | ✅ | `build_production_video.py` — silence cut + cards + subtitles |
| 🔄 Full send→wait→reply loop | ✅ | `imessage-toggle.sh` + `imessage-receive.sh` |

---

## 🔑 The Key Discovery — Video Sending

AppleScript `send file to buddy` is broken/restricted on macOS Sonoma+.
Text sends fine. File attachments fail silently with the obvious approach.

**What doesn't work:**
```bash
# ❌ returns success but "not delivered" on phone
osascript -e 'tell app "Messages" to send POSIX file "/path/to/video.mp4" to buddy "..."'
```

**What works:**
```
1. Finder selects the file → Cmd+C (copies as proper file object)
2. open imessage://+1XXXXXXXXXX (opens/focuses conversation)
3. Cmd+V paste into Messages input
4. Return to send
```

This works because Finder's clipboard type is recognized by Messages — direct AppleScript file sends are not.

---

## 📁 The Tools (install via setup.sh)

All scripts live in `~/.claude/` after running `setup.sh`:

| Script | What it does |
|---|---|
| `~/.claude/imessage-send.sh "text"` | Send a text message |
| `~/.claude/imessage-send-image.sh /path` | Send an image |
| `~/.claude/imessage-send-video.sh /path` | Send a video (auto-compresses >95MB) |
| `~/.claude/imessage-toggle.sh` | Toggle mobile mode flag on/off |
| `~/.claude/imessage-receive.sh` | Wait up to 5 min for a reply |

**Studio Record** (screen recording app):
```bash
python studio-record/studio_record.py &   # launch
curl -X POST http://127.0.0.1:17494/start?mode=screen  # start recording
curl -X POST http://127.0.0.1:17494/stop               # stop + save
```

---

## 🤖 The Full Demo Pipeline

```
📱 You text: "Find me a cool article and send me a video of you reading it"
     │
     ▼
🔄 imessage-receive.sh picks up your message
     │
     ▼
🤖 Claude / your local model (Gemma · Llama · Qwen) receives the task
     │
     ├── curl 17494/start?mode=screen   ← start recording
     ├── Brave browser → finds article
     ├── ~/.local/bin/speak "..." ← narrates in your voice
     ├── curl 17494/stop              ← stop recording
     │
     ▼
🎬 build_production_video.py (optional — adds title card + subtitles)
     │
     ▼
~/.claude/imessage-send-video.sh /path/to/video.mp4
     │
     ▼
📲 Video lands on your iPhone via iMessage
```

---

## 🔗 Full Repo

All scripts and Studio Record are in a separate standalone repo:
**[nicedreamzapp/claude-screen-to-phone](https://github.com/nicedreamzapp/claude-screen-to-phone)**

That repo is self-contained — Mac + iPhone users can clone it, run `setup.sh`, and have the full pipeline without needing the local AI stack.

**This repo** (`claude-code-local`) wires it into your local AI so a model from the lineup (Gemma 4 31B, Llama 3.3 70B, or Qwen 3.5 122B) is doing the thinking instead of Claude cloud.
