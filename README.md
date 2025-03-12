# 🎵 Discord Music Bot

A simple and high-quality **Discord music bot** that lets you play songs from **YouTube** in your voice channel while chatting with friends. **Free & open-source!** Built with **Python** and **discord.py**. 🚀

---

## ✨ Features

✅ **Play music** from YouTube 🎶  
✅ **Queue system** to manage multiple tracks 📜  
✅ **Skip tracks** easily ⏭️  
✅ **Now Playing** command to see the current song 🎼  
✅ **Pause and Resume** playback ⏸️▶️  
✅ ~~Adjust volume with a simple command 🔊~~  
✅ **Loop the queue** for endless music 🔁  
✅ **Admin commands** to clean up temporary files 🛠️  
✅ **Available in Spanish 🇪🇸**

---

## 📥 Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/discord-music-bot.git
cd discord-music-bot
```

### 2️⃣ Install Dependencies
Make sure you have **Python 3.8+** installed. Then, install the required dependencies:
```bash
pip install -r requirements.txt
```

### 3️⃣ Set Up the Bot
Create a `.env` file and add your **Discord Bot Token**:
```
BOT_TOKEN=
BOT_PREFIX=.
BOT_COLOR=915CBF
YTDL_FORMAT=worstaudio
PRINT_STACK_TRACE=true
BOT_REPORT_COMMAND_NOT_FOUND=true
BOT_REPORT_DL_ERROR=true
```

### 4️⃣ Run the Bot
Start the bot with:
```bash
python music-bot.py
```

---

## 🎮 Commands

| Command | Description |
|---------|-------------|
| `.play [query]` | Play a song from YouTube |
| `.queue` | Show the current music queue |
| `.skip [n]` | Skip a number of tracks |
| `.nowplaying` | Show the current track |
| `.pause` | Pause the current track |
| `.resume` | Resume playback |
| `.volume [0-100]` | Set the playback volume |
| `.loop` | Toggle queue looping |
| `.cleanup` | Clean up downloaded files (admin only) |

---

## ⚙️ Configuration

You can customize the bot’s **prefix, colors, and settings** in `config.py`.

---

## 🛠️ Troubleshooting

**Q:** Bot is not responding to commands?  
**A:** Ensure your bot has the correct **permissions** to read messages and connect to voice channels.

**Q:** Music stops randomly?  
**A:** This may be due to YouTube restrictions. Try **changing the audio source**.

---

## 🤝 Contributing

Want to improve this bot? Feel free to **fork** the repository and submit a **pull request**!

---

## 📝 License

This project is **open-source** under the [MIT License](LICENSE).

---

## ⭐ Show Some Love
If you like this project, **give it a star ⭐ on GitHub!** 🎵💙
