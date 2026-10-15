<p align="center"><img src="docs/banner.jpg" alt="Nova Bot"></p>

<p align="center">Your own AI chat app for Windows, made by Nova Studios. Free, private and yours to customise.</p>

---

Nova Bot is one chat window that can use the smartest free AIs on the internet or run AI models fully on your own PC. You can switch between them with one click.

| Brain | How smart | Limits | Privacy |
|---|---|---|---|
| **Google Gemini 3.8 Flash** | Smartest free option | Free daily limit | Google may use free-tier chats to improve its products |
| **Groq** (gpt-oss-120b, Qwen…) | Very good, very fast | 1,000 free requests a day per model | Runs on Groq's servers |
| **OpenRouter** (DeepSeek, Llama…) | Many free models | About 50 free requests a day | Runs on each model's host |
| **This PC** (Ollama) | Good. Depends on your graphics card | None | 100% on your PC, works offline |

## Features

- **A free AI downloads automatically on first start.** Nova Bot checks your graphics card and downloads the best free, unlimited model for it (Qwen 3.5 4B, 9B or 27B)
- **See-through glass over the Nova Bot artwork.** Every panel is frosted glass, and **Settings → Look** sets how see-through it is, how much blur, or a plain black background
- Chats are saved, with a list of past chats in the sidebar
- Replies appear word by word, and you can stop them mid-answer
- A "Think first" mode makes the AI reason step by step before answering, and you can open up its thinking
- Code blocks have copy buttons, plus tables, lists and links
- You can change Nova's name, personality and creativity in Settings
- Models for your PC download from inside the app, with a progress bar
- API keys, settings and chats stay on your PC (`%APPDATA%\Nova Bot`)

## Install

1. Download this repo: **Code → Download ZIP**, then unzip it somewhere.
2. Double-click **`Install.bat`**. It installs Python and Ollama if you don't have them and adds a **Nova Bot** shortcut to your Desktop and Start menu.
3. Open Nova Bot. It starts downloading a free AI for your PC by itself, and you can start chatting when the bar fills up.
   - **For the smartest AI as well:** get a free key at [Google AI Studio](https://aistudio.google.com/apikey) and paste it in.

## Which model should I download for my PC?

| Graphics card memory | Try |
|---|---|
| No graphics card / 4 GB | `qwen3.5:4b` |
| 8 GB | `qwen3.5:9b` or `gemma4:12b-it-qat` |
| 16 GB | `qwen3.5:27b` or `gemma4:26b-a4b` |
| 24 GB+ | `qwen3.8:27b` |

Any model name from [ollama.com/search](https://ollama.com/search) works.

## For developers

You only need Python 3.10 or newer and the standard library.

```
python server.py --open
```

- `server.py`: a small local server on `127.0.0.1:8765`. It serves the window and forwards chats to Gemini, Groq, OpenRouter (OpenAI-compatible APIs) or Ollama.
- `app/index.html`: the whole chat window (HTML, CSS and JS in one file).
- `art/`: the original Nova Bot artwork. `tools/make_icon.py` (needs Pillow) turns it into the icon, avatar and backgrounds in `app/`.
- `tools/make_shortcut.ps1` makes the Desktop and Start menu shortcuts.

---

<p align="center">Made by <b>Nova Studios</b></p>
