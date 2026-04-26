# 🛡️ Aegis Security Console

A highly autonomous, cyberpunk-themed API Security Auditor powered by AI (Mistral & Gemini). Aegis-Agent utilizes the ReAct (Reasoning and Acting) framework to autonomously scan, map, and test web applications for security vulnerabilities without requiring complex manual inputs.

---

## 🌌 Features
- **Autonomous AI Brain:** Powered by Mistral and Gemini, the agent reasons through security testing workflows, making its own decisions on what to scan next.
- **Dynamic Fallback System:** If the primary AI provider fails or hits a rate limit, Aegis automatically falls back to a secondary AI provider, or ultimately, a deterministic offline fallback scan.
- **Cyberpunk GUI:** A breathtaking, hardware-accelerated "Void Dark" interface featuring neon accents, parallax starfields, and dynamic mouse particle trails.
- **Standalone Executable:** Fully bundled into a single Windows `.exe` file. No Python installation required!
- **Local Credential Storage:** API keys are never hardcoded. They are stored locally on your machine in a hidden `.json` file for maximum security.

---

## 📂 Project Structure

```text
aegis_project/
├── ui.py               # The main Graphical User Interface (Cyberpunk Theme)
├── main.py             # The core ReAct loop that controls the autonomous agent
├── ai_engine.py        # Connects to Mistral/Gemini and manages API authentication
├── tools.py            # The security tool suite (Network Recon, API Parser, HTTP Client)
├── run_aegis.py        # Master Bootloader (Used to compile the multi-process EXE)
├── .gitignore          # Keeps your API keys and heavy builds off GitHub
└── dist/               # (Generated) Contains the compiled Aegis_Security_Console.exe
```

---

## 🚀 How to Run

### Method 1: The Standalone Executable (Recommended)
You do not need to install anything to run Aegis.
1. Navigate to the `dist/` folder.
2. Double-click `Aegis_Security_Console.exe`.
3. Go to the **Configuration** tab and paste your Mistral and Gemini API keys. Click **Save Config**.
4. Go to the **Auditor** tab, enter a Target IP or URL (e.g., `localhost` or `http://example.com`), and click **Start Audit**!

### Method 2: Running via Python Source
If you are a developer and want to run the raw Python files:
1. Ensure you have Python 3.10+ installed.
2. Install the required dependencies:
   ```bash
   pip install requests pyinstaller
   ```
3. Run the graphical interface:
   ```bash
   python ui.py
   ```
*(Note: You can also run the backend headlessly via `python main.py --target <URL>` once your config is generated).*

---

## 🛠️ How to Build the `.exe`
If you make changes to the source code (`tools.py`, `ui.py`, etc.), you will need to recompile the executable.

1. Open a terminal in the project root directory.
2. Run the PyInstaller command against the master bootloader:
   ```bash
   python -m PyInstaller --noconsole --onefile --name "Aegis_Security_Console" run_aegis.py --clean -y
   ```
3. Your new `.exe` will be generated inside the `dist/` folder!

---

## 🔒 Security & Privacy Warning
Aegis-Agent is an active security auditing tool. **DO NOT** point this tool at external websites, servers, or APIs that you do not explicitly own or have written permission to test. Unauthorized scanning may result in legal consequences. 

*Your API keys are stored in `.aegis_ui_config.json` next to your executable. Do not share this file with anyone.*
