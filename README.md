# 📝 Change Logger

A lightweight, automated tool that watches your code folder and generates a real-time change log. It tracks created, modified, and deleted files, capturing detailed diffs of every change.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

*   **Real-time Monitoring**: Automatically detects file changes as they happen.
*   **Detailed Diffs**: Logs exactly what lines were added or removed.
*   **Live Dashboard**: Beautiful terminal UI powered by `rich` to show events as they occur.
*   **Markdown Reports**: Generates a `CHANGELOG_AUTO.md` file with foldable diff sections for easy reading.

## 🚀 Getting Started

### 1. Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/razberi-py/Change-logger.git
cd Change-logger
pip install -r requirements.txt
```

### 2. Usage

Run the start script:

```bash
# Windows
start_logger.bat

# Linux/Mac
python monitor.py
```

### 3. How it Works

1.  Select **"1. Select Folder and Watch"** from the menu.
2.  Enter the path to the folder you want to monitor (defaults to the current folder).
3.  The tool will start watching. Any edits you make to files in that folder will be:
    *   Shown instantly on the terminal dashboard.
    *   Logged permanently to `CHANGELOG_AUTO.md` in the watched directory.
4.  Press `Ctrl+C` to stop watching.

## 📄 Example Log Output

```markdown
### 📝 [14:30:05] MODIFIED: src/main.py
- **Lines Added**: 5
- **Lines Removed**: 2

<details>
<summary>View Changes</summary>

```diff
- old_function()
+ new_function_v2()
```
</details>
```

---
Made with ❤️ by [razberi-py](https://github.com/razberi-py)
