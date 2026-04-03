import sys
import os
import re
import subprocess
import requests
import math
import psutil
import ctypes
import collections
import json
import asyncio
import edge_tts
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QLineEdit, QMenu, QAction, QInputDialog
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen
from PyQt5.QtMultimedia import QSoundEffect, QMediaPlayer, QMediaContent

DEBUG = True

# ---------------------------------------------------------------------------
# APP MAP  —  add any app here. Use %USERNAME% / %APPDATA% env vars freely.
# Keys are lowercase nicknames the user types (or JARVIS tags).
# Values are the executable path or command string.
# ---------------------------------------------------------------------------
APP_MAP = {
    # ── Windows Built-ins ──
    "notepad":        "notepad.exe",
    "calculator":     "calc.exe",
    "paint":          "mspaint.exe",
    "explorer":       "explorer.exe",
    "task manager":   "taskmgr.exe",
    "taskmgr":        "taskmgr.exe",
    "cmd":            "cmd.exe",
    "powershell":     "powershell.exe",
    "terminal":       "wt.exe",
    "control panel":  "control.exe",
    "settings":       "ms-settings:",          # opens Win11 Settings via URI
    "snipping tool":  "SnippingTool.exe",
    "wordpad":        "wordpad.exe",
    "regedit":        "regedit.exe",

    # ── Browsers ──
    "chrome":   r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox":  r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "edge":     r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "brave":    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "opera":    r"%LOCALAPPDATA%\Programs\Opera\opera.exe",

    # ── Dev Tools ──
    "vscode":           r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
    "visual studio":    r"C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\devenv.exe",
    "git bash":         r"C:\Program Files\Git\git-bash.exe",
    "github desktop":   r"%LOCALAPPDATA%\GitHubDesktop\GitHubDesktop.exe",
    "postman":          r"%LOCALAPPDATA%\Postman\Postman.exe",
    "docker":           r"C:\Program Files\Docker\Docker\Docker Desktop.exe",
    "dbeaver":          r"C:\Program Files\DBeaver\dbeaver.exe",

    # ── Communication ──
    "discord":  r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe",
    "slack":    r"%LOCALAPPDATA%\slack\slack.exe",
    "teams":    r"%LOCALAPPDATA%\Microsoft\Teams\current\Teams.exe",
    "zoom":     r"%APPDATA%\Zoom\bin\Zoom.exe",
    "telegram": r"%APPDATA%\Telegram Desktop\Telegram.exe",
    "whatsapp": r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe",

    # ── Media ──
    "spotify":  r"%APPDATA%\Spotify\Spotify.exe",
    "vlc":      r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    "obs":      r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",

    # ── Office ──
    "word":       r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel":      r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "powerpoint": r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
    "outlook":    r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
    "onenote":    r"C:\Program Files\Microsoft Office\root\Office16\ONENOTE.EXE",

    # ── Utilities ──
    "7zip":       r"C:\Program Files\7-Zip\7zFM.exe",
    "winrar":     r"C:\Program Files\WinRAR\WinRAR.exe",
    "steam":      r"C:\Program Files (x86)\Steam\steam.exe",
    "Burp Suite":  r"C:\Users\TobiasAre\AppData\Local\Programs\BurpSuiteCommunity\BurpSuiteCommunity.exe",
}

# Process names used by psutil when CLOSING apps (lowercase .exe name)
PROCESS_MAP = {
    "notepad":        "notepad.exe",
    "calculator":     "calculator.exe",
    "paint":          "mspaint.exe",
    "chrome":         "chrome.exe",
    "firefox":        "firefox.exe",
    "edge":           "msedge.exe",
    "brave":          "brave.exe",
    "discord":        "discord.exe",
    "slack":          "slack.exe",
    "teams":          "teams.exe",
    "zoom":           "zoom.exe",
    "spotify":        "spotify.exe",
    "vlc":            "vlc.exe",
    "obs":            "obs64.exe",
    "vscode":         "code.exe",
    "word":           "WINWORD.EXE",
    "excel":          "EXCEL.EXE",
    "powerpoint":     "POWERPNT.EXE",
    "outlook":        "OUTLOOK.EXE",
    "steam":          "steam.exe",
    "telegram":       "telegram.exe",
    "whatsapp":       "whatsapp.exe",
}

# ---------------------------------------------------------------------------

if sys.platform == "win32":
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


# --- STARTUP WORKER ---
class StartupContextWorker(QThread):
    finished = pyqtSignal(dict)

    def run(self):
        context = {}
        hour = datetime.now().hour
        if 5 <= hour < 12:   context['time'] = "Morning"
        elif 12 <= hour < 17: context['time'] = "Afternoon"
        elif 17 <= hour < 22: context['time'] = "Evening"
        else:                  context['time'] = "Late Night"

        try:
            geo = requests.get("https://get.geojs.io/v1/ip/geo.json", timeout=5).json()
            lat, lon, city = geo.get('latitude', ''), geo.get('longitude', ''), geo.get('city', '')
            if lat and lon:
                weather_res = requests.get(
                    f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&temperature_unit=fahrenheit",
                    timeout=5).json()
                wcode = weather_res.get('current_weather', {}).get('weathercode', 0)
                temp  = weather_res.get('current_weather', {}).get('temperature', 0)
                weather_desc = "Clear"
                if wcode in [1, 2, 3]:               weather_desc = "Cloudy"
                elif wcode in [45, 48]:               weather_desc = "Foggy"
                elif wcode in [51, 53, 55, 56, 57]:  weather_desc = "Drizzling"
                elif wcode in [61, 63, 65, 66, 67]:  weather_desc = "Raining"
                elif wcode in [71, 73, 75, 77]:      weather_desc = "Snowing"
                elif wcode in [95, 96, 99]:           weather_desc = "Thunderstorm"
                context['weather'] = f"{weather_desc}, {temp}°F in {city}"
        except Exception:
            context['weather'] = "Unknown weather"

        self.finished.emit(context)


# --- TTS WORKER ---
class TTSWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, text, output_path):
        super().__init__()
        self.text = text
        self.output_path = output_path

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            communicate = edge_tts.Communicate(self.text, "en-GB-RyanNeural", rate="+5%")
            loop.run_until_complete(communicate.save(self.output_path))
            loop.close()
            self.finished.emit(self.output_path)
        except Exception as e:
            print(f"TTS Error: {e}")
            self.finished.emit("")


# --- MEMORY WORKER ---
class MemoryWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, url, model, text):
        super().__init__()
        self.url = url
        self.model = model
        self.text = text

    def run(self):
        try:
            today = datetime.now().strftime("%A (%Y-%m-%d)")
            prompt = (f"Extract a brief fact (hobby, plan, project, preference) about the user from this message "
                      f"if it contains long-term info. If none, reply 'NONE'. Keep it under 15 words. "
                      f"Talk about the user in third person ('User'). Today is {today}. Message: '{self.text}'")
            response = requests.post(self.url, json={"model": self.model, "prompt": prompt, "stream": False}, timeout=15)
            data = response.json()
            if "response" in data:
                self.finished.emit(data["response"].strip())
        except Exception:
            self.finished.emit("NONE")


# --- OLLAMA WORKER ---
class OllamaWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, url, model, prompt):
        super().__init__()
        self.url = url
        self.model = model
        self.prompt = prompt

    def run(self):
        try:
            response = requests.post(self.url,
                json={"model": self.model, "prompt": self.prompt, "stream": False}, timeout=30)
            response_json = response.json()
            if "error" in response_json:
                self.finished.emit(f"Error: {response_json['error']} [sad]")
            else:
                self.finished.emit(response_json["response"])
        except Exception as e:
            self.finished.emit(f"Systems offline, sir. {e} [sad]")


# --- ANIMATED PET GRAPHICS ---
class AnimatedPetGraphics(QWidget):
    def __init__(self):
        super().__init__()
        self.emotion = "happy"
        self.frame = 0
        self.blink_timer = 0
        self.jump_offset = 0
        self.setFixedSize(200, 200)

        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.animate_frame)
        self.anim_timer.start(16)

    def poke(self):
        self.jump_offset = -40
        self.emotion = "surprised"

    def animate_frame(self):
        self.frame += 1
        self.blink_timer += 1
        if self.blink_timer > 180:
            self.blink_timer = 0
        if self.jump_offset < 0:
            self.jump_offset += 2
        else:
            self.jump_offset = 0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        color = QColor(255, 180, 200)
        bounce_speed, bounce_height, eye_state = 0.08, 8, "open"

        if   self.emotion == "sad":       color, bounce_speed, bounce_height, eye_state = QColor(120,160,255), 0.03, 3,  "half"
        elif self.emotion == "angry":     color, bounce_speed, bounce_height, eye_state = QColor(255,100,100), 0.4,  5,  "angry"
        elif self.emotion == "thinking":  color, bounce_speed, bounce_height, eye_state = QColor(200,150,255), 0.05, 12, "open"
        elif self.emotion == "bored":     color, bounce_speed, bounce_height, eye_state = QColor(160,160,160), 0.02, 2,  "closed"
        elif self.emotion == "excited":   color, bounce_speed, bounce_height, eye_state = QColor(255,220,100), 0.3,  20, "open"
        elif self.emotion == "sweating":  color, bounce_speed, bounce_height, eye_state = QColor(255,80, 80),  0.5,  6,  "angry"
        elif self.emotion == "surprised": color, bounce_speed, bounce_height, eye_state = QColor(180,255,200), 0.0,  0,  "wide"

        hour = datetime.now().hour
        if 0 <= hour < 5 or hour >= 23: bounce_speed *= 0.4
        elif 20 <= hour < 23:           bounce_speed *= 0.7

        offset_y = (math.sin(self.frame * bounce_speed) * bounce_height) + self.jump_offset
        center_x, center_y = 100, 100 + offset_y

        shadow_width = max(30, 80 - (offset_y * 1.5))
        painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(center_x - shadow_width/2), 160, int(shadow_width), 15)

        painter.setBrush(QBrush(color))
        painter.drawEllipse(int(center_x - 50), int(center_y - 40), 100, 80)
        painter.drawEllipse(int(center_x - 55), int(center_y - 10), 110, 50)

        painter.setBrush(QBrush(QColor(40, 40, 40)))
        eye_y = int(center_y - 10)
        left_eye_x, right_eye_x = int(center_x - 25), int(center_x + 10)
        is_blinking = self.blink_timer < 8

        if is_blinking or eye_state == "closed":
            painter.drawRect(left_eye_x, eye_y + 5, 12, 3)
            painter.drawRect(right_eye_x, eye_y + 5, 12, 3)
        elif eye_state == "angry":
            painter.drawEllipse(left_eye_x, eye_y, 12, 12)
            painter.drawEllipse(right_eye_x, eye_y, 12, 12)
            painter.setPen(QPen(QColor(40, 40, 40), 4, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(left_eye_x - 5, eye_y - 5, left_eye_x + 10, eye_y)
            painter.drawLine(right_eye_x + 15, eye_y - 5, right_eye_x, eye_y)
            painter.setPen(Qt.NoPen)
        elif eye_state == "half":
            painter.drawEllipse(left_eye_x, eye_y, 12, 12)
            painter.drawEllipse(right_eye_x, eye_y, 12, 12)
            painter.setBrush(QBrush(color))
            painter.drawRect(left_eye_x - 2, eye_y - 2, 35, 7)
        elif eye_state == "wide":
            painter.drawEllipse(left_eye_x - 2, eye_y - 4, 16, 20)
            painter.drawEllipse(right_eye_x - 2, eye_y - 4, 16, 20)
        else:
            painter.drawEllipse(left_eye_x, eye_y, 12, 14)
            painter.drawEllipse(right_eye_x, eye_y, 12, 14)
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(left_eye_x + 2, eye_y + 2, 4, 4)
            painter.drawEllipse(right_eye_x + 2, eye_y + 2, 4, 4)


# ===========================================================================
# MAIN APP
# ===========================================================================
class Tamagotchi(QWidget):
    def __init__(self):
        super().__init__()

        self.base_dir    = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.base_dir, "config.json")
        self.memory_path = os.path.join(self.base_dir, "memory.json")

        self.config   = self.load_or_create_config()
        self.pet_name = self.config.get("pet_name", "JARVIS")
        self.long_term_memory = self.load_memory()

        self.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.model      = "llama3.2:3b"

        # Build a readable app list for the system prompt
        known_apps = ", ".join(sorted(APP_MAP.keys()))
        self.system_prompt = (
            f"You are {self.pet_name}, an AI assistant in the style of JARVIS from Iron Man. "
            f"Address the user as 'sir'. Be concise, intelligent, and occasionally dry-humored. "
            f"Keep answers to 1-2 sentences. "
            f"You can launch applications. When the user asks you to open or launch something, "
            f"end your reply with [launch:<key>] using one of these exact keys: {known_apps}. "
            f"You can also close apps — end your reply with [close:<key>] using the same keys. "
            f"For unknown apps just try [launch:<whatever they said>]. "
            f"You can also set your emotion with [happy], [sad], [excited], [angry], [thinking], [surprised]."
        )

        self.chat_history     = collections.deque(maxlen=8)
        self.last_window_title = ""
        self.mouse_travel     = 0
        self.is_bored_idle    = False

        os.makedirs(os.path.join(self.base_dir, "sounds"), exist_ok=True)
        self.speech_output_path = ""
        self.media_player = QMediaPlayer()

        self.pop_sound_path    = os.path.join(self.base_dir, "sounds", "pop.wav")
        self.squeak_sound_path = os.path.join(self.base_dir, "sounds", "squeak.wav")
        self.pop_sound    = QSoundEffect()
        self.pop_sound.setSource(QUrl.fromLocalFile(self.pop_sound_path))
        self.squeak_sound = QSoundEffect()
        self.squeak_sound.setSource(QUrl.fromLocalFile(self.squeak_sound_path))

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(350, 350)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

        layout = QVBoxLayout()

        self.speech = QLabel("")
        self.speech.setWordWrap(True)
        self.speech.setAlignment(Qt.AlignCenter)
        self.speech.setStyleSheet(
            "color: #00d4ff; background-color: rgba(5, 15, 30, 230); "
            "border: 2px solid #00d4ff; border-radius: 10px; "
            "padding: 12px; font-size: 13px; font-weight: bold; font-family: Consolas;")
        self.speech.hide()

        self.pet_canvas = AnimatedPetGraphics()
        self.pet_canvas.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Awaiting your command, sir...")
        self.input_box.setStyleSheet(
            "background-color: rgba(0, 10, 25, 220); border: 2px solid #00d4ff; "
            "border-radius: 8px; padding: 6px; color: #00d4ff; font-family: Consolas;")
        self.input_box.hide()
        self.input_box.returnPressed.connect(self.process_user_input)
        self.input_box.textChanged.connect(self.on_typing)

        layout.addWidget(self.speech)
        layout.addWidget(self.pet_canvas, alignment=Qt.AlignCenter)
        layout.addWidget(self.input_box)
        self.setLayout(layout)
        self.move(1200, 600)

        self.active_ollama_workers = set()
        self.active_tts_workers    = set()
        self.active_memory_workers = set()

        self.system_timer = QTimer()
        self.system_timer.timeout.connect(self.monitor_system)
        self.system_timer.start(5000)

        self.startup_worker = StartupContextWorker()
        self.startup_worker.finished.connect(self.on_startup_context_ready)
        self.startup_worker.start()

    # -----------------------------------------------------------------------
    # CONFIG & MEMORY
    # -----------------------------------------------------------------------
    def load_or_create_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        name, ok = QInputDialog.getText(None, "New Assistant", "Name your AI assistant:")
        name = name.strip() if ok and name.strip() else "JARVIS"
        config = {"pet_name": name}
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        return config

    def load_memory(self):
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save_memory(self):
        with open(self.memory_path, 'w', encoding='utf-8') as f:
            json.dump(self.long_term_memory, f)

    # -----------------------------------------------------------------------
    # APP LAUNCHER  ← the core new feature
    # -----------------------------------------------------------------------
    def _resolve_app_path(self, key):
        """Return the expanded executable path for a key, or None if not found."""
        path = APP_MAP.get(key.lower().strip())
        if path:
            return os.path.expandvars(path)
        return None

    def launch_app(self, key, url=None):
        """
        Launch an app by its APP_MAP key.
        If url is provided it is appended as an argument (e.g. for browsers).
        Falls back to trying `key.exe` directly if not in the map.
        Returns (success: bool, message: str)
        """
        path = self._resolve_app_path(key)

        if not path:
            # Graceful fallback — try it as a raw exe name
            path = key if key.endswith(".exe") else f"{key}.exe"

        try:
            cmd = [path]
            if url:
                cmd.append(url)

            # ms-settings: style URIs need ShellExecute, not Popen
            if path.startswith("ms-"):
                os.startfile(path)
            else:
                subprocess.Popen(cmd, shell=False)

            app_label = key.title()
            return True, f"Launching {app_label}, sir."
        except FileNotFoundError:
            return False, f"I couldn't locate {key}, sir. The path may need updating in APP_MAP."
        except Exception as e:
            return False, f"Launch failed for {key}: {e}"

    def close_app(self, key):
        """
        Kill all processes matching PROCESS_MAP[key].
        Falls back to treating key itself as the exe name.
        Returns (success: bool, message: str)
        """
        proc_name = PROCESS_MAP.get(key.lower().strip(), key if key.endswith(".exe") else f"{key}.exe")
        killed = 0
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == proc_name.lower():
                    proc.kill()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        if killed:
            return True, f"Terminated {key.title()} ({killed} process{'es' if killed > 1 else ''}), sir."
        else:
            return False, f"No running instances of {key.title()} found, sir."

    # -----------------------------------------------------------------------
    # STARTUP
    # -----------------------------------------------------------------------
    def on_startup_context_ready(self, context):
        time_str    = context.get('time', 'Unknown time')
        weather_str = context.get('weather', 'Unknown weather')
        greeting    = (f"*System Note: You just came online. It is {time_str} and the weather is "
                       f"{weather_str}. Give the user a short, formal JARVIS-style greeting.*")
        QTimer.singleShot(1000, lambda: self.send_to_ollama(greeting))

    # -----------------------------------------------------------------------
    # UI HELPERS
    # -----------------------------------------------------------------------
    def set_emotion(self, emotion):
        self.pet_canvas.emotion = emotion

    def show_speech(self, text):
        self.speech.setText(text)
        self.speech.show()
        if os.path.exists(self.pop_sound_path):
            self.pop_sound.play()

    # -----------------------------------------------------------------------
    # SYSTEM MONITOR
    # -----------------------------------------------------------------------
    def monitor_system(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        if cpu > 85 or ram > 90:
            self.set_emotion("sweating")
            self.show_speech(f"⚠ System under strain, sir. CPU: {cpu}% | RAM: {ram}%")
            return

        if sys.platform != "win32":
            return

        try:
            hwnd   = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf    = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            active_title = buf.value.lower()

            if active_title != self.last_window_title and active_title:
                self.last_window_title = active_title
                if any(k in active_title for k in ["spotify", "youtube music", "apple music"]):
                    self.set_emotion("happy")
                    self.show_speech("Music detected. Shall I add this to your playlist, sir? 🎵")
                elif any(k in active_title for k in ["code", "visual studio", "pycharm", "sublime"]):
                    hour = datetime.now().hour
                    if 0 <= hour < 5:
                        self.set_emotion("angry")
                        self.show_speech("Sir, it is past midnight. Rest is advisable. 💢")
                    else:
                        self.set_emotion("excited")
                        self.show_speech("Engineering mode engaged. 💻")
                elif "youtube" in active_title:
                    self.set_emotion("happy")
                    self.show_speech("Monitoring your viewing activity, sir. 👀")
        except Exception:
            pass

        try:
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
            millis       = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            idle_seconds = millis / 1000.0
            if idle_seconds > 600:
                if not self.is_bored_idle:
                    self.is_bored_idle = True
                    self.send_to_ollama("*System Note: The user has been idle for 10 minutes. "
                                        "Request a status update in a formal JARVIS manner.*")
            else:
                self.is_bored_idle = False
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # MOUSE EVENTS
    # -----------------------------------------------------------------------
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.dragPosition)
        elif not event.buttons():
            self.mouse_travel += 1
            if self.mouse_travel > 40:
                self.set_emotion("happy")
                self.mouse_travel = 0
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            self.pet_canvas.poke()
            if os.path.exists(self.squeak_sound_path):
                self.squeak_sound.play()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.input_box.isVisible():
                self.input_box.hide()
                self.speech.hide()
            else:
                self.input_box.show()
                self.input_box.setFocus()
                self.show_speech("Awaiting your command, sir. 💬")

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        quit_action = QAction("Shut Down", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)
        menu.exec_(event.globalPos())

    # -----------------------------------------------------------------------
    # DRAG & DROP
    # -----------------------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            self.set_emotion("surprised")
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            if file_path.endswith(('.txt', '.py', '.md', '.json', '.log')):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()[:1000].rsplit('\n', 1)[0]
                self.send_to_ollama(
                    f"I just received a file named '{os.path.basename(file_path)}'. "
                    f"Here is its content: {content}. Please analyse it briefly.")
            else:
                self.show_speech("I can only process text-based files, sir.")
                self.set_emotion("sad")

    # -----------------------------------------------------------------------
    # INPUT HANDLING
    # -----------------------------------------------------------------------
    def on_typing(self, text):
        if self.active_ollama_workers:
            return
        length = len(text)
        if length == 0:         self.set_emotion("happy")
        elif length <= 10:      self.set_emotion("thinking")
        elif length <= 25:      self.set_emotion("surprised")
        else:                   self.set_emotion("bored")

    def process_user_input(self):
        text = self.input_box.text().strip()
        if not text:
            return
        self.input_box.clear()
        self.input_box.hide()

        lower = text.lower()

        # ── Direct "open <app>" command ──────────────────────────────────
        if lower.startswith("open ") or lower.startswith("launch "):
            prefix_len = 5 if lower.startswith("open ") else 7
            raw_key    = lower[prefix_len:].strip()

            # Check if a URL was appended: "open brave youtube.com"
            url = None
            for browser in ["chrome", "firefox", "edge", "brave", "opera"]:
                if raw_key.startswith(browser):
                    remainder = raw_key[len(browser):].strip()
                    if remainder:
                        url = remainder if remainder.startswith("http") else f"https://{remainder}"
                    raw_key = browser
                    break

            success, msg = self.launch_app(raw_key, url)
            self.set_emotion("excited" if success else "sad")
            self.show_speech(msg)
            self.chat_history.append({"role": "User",  "content": text})
            self.chat_history.append({"role": "Pet",   "content": msg})
            return

        # ── Direct "close <app>" command ─────────────────────────────────
        if lower.startswith("close ") or lower.startswith("kill "):
            prefix_len = 6 if lower.startswith("close ") else 5
            raw_key    = lower[prefix_len:].strip()
            success, msg = self.close_app(raw_key)
            self.set_emotion("angry" if success else "sad")
            self.show_speech(msg)
            self.chat_history.append({"role": "User",  "content": text})
            self.chat_history.append({"role": "Pet",   "content": msg})
            return

        # ── Clipboard read ────────────────────────────────────────────────
        if lower == "read this":
            clipboard_text = QApplication.clipboard().text()
            text = (f"The user copied this text: '{clipboard_text}'. Analyse it briefly."
                    if clipboard_text else "The clipboard was empty, sir.")

        # ── List available apps ───────────────────────────────────────────
        if lower in ["list apps", "what can you open", "available apps"]:
            app_list = ", ".join(sorted(APP_MAP.keys()))
            self.show_speech(f"I can launch: {app_list}")
            return

        self.send_to_ollama(text)

    # -----------------------------------------------------------------------
    # MEMORY
    # -----------------------------------------------------------------------
    def handle_memory_extracted(self, fact):
        if fact and "NONE" not in fact.upper() and 5 < len(fact) < 150:
            date_str = datetime.now().strftime("%Y-%m-%d")
            self.long_term_memory.append(f"[{date_str}] {fact}")
            self.long_term_memory = self.long_term_memory[-15:]
            self.save_memory()

    # -----------------------------------------------------------------------
    # OLLAMA
    # -----------------------------------------------------------------------
    def send_to_ollama(self, user_text):
        self.set_emotion("thinking")
        self.show_speech("Processing query... ▋")

        if not user_text.startswith("*System Note"):
            mem_worker = MemoryWorker(self.ollama_url, self.model, user_text)
            self.active_memory_workers.add(mem_worker)
            mem_worker.finished.connect(self.handle_memory_extracted)
            mem_worker.finished.connect(lambda res, w=mem_worker: self.active_memory_workers.discard(w))
            mem_worker.start()

        self.chat_history.append({"role": "User", "content": user_text})

        lt_memory_context = ""
        if self.long_term_memory:
            facts = '\n- '.join(self.long_term_memory)
            lt_memory_context = f"\n[Long-term data on user:\n- {facts}]\n"

        full_prompt = f"{self.system_prompt}{lt_memory_context}\n\n"
        for msg in self.chat_history:
            full_prompt += f"{msg['role']}: {msg['content']}\n"
        full_prompt += "Pet:"

        worker = OllamaWorker(self.ollama_url, self.model, full_prompt)
        self.active_ollama_workers.add(worker)
        worker.finished.connect(self.handle_ollama_response)
        worker.finished.connect(lambda res, w=worker: self.active_ollama_workers.discard(w))
        worker.start()

    def handle_ollama_response(self, raw_response):
        if raw_response.startswith("Error") or raw_response.startswith("Systems offline"):
            if self.chat_history and self.chat_history[-1]["role"] == "User":
                self.chat_history.pop()

        # ── Handle [launch:<key>] tag from AI ────────────────────────────
        launch_match = re.search(r'\[launch:([^\]]+)\]', raw_response, re.IGNORECASE)
        if launch_match:
            app_key = launch_match.group(1).strip().lower()
            success, launch_msg = self.launch_app(app_key)
            if not success:
                print(f"[JARVIS Launcher] {launch_msg}")

        # ── Handle [close:<key>] tag from AI ─────────────────────────────
        close_match = re.search(r'\[close:([^\]]+)\]', raw_response, re.IGNORECASE)
        if close_match:
            app_key = close_match.group(1).strip().lower()
            self.close_app(app_key)

        # ── Extract emotion tag ───────────────────────────────────────────
        emotion_match = re.search(r'\[([a-zA-Z]+)\]\s*$', raw_response)
        if emotion_match:
            self.set_emotion(emotion_match.group(1).lower())
        else:
            self.set_emotion("happy")

        # Strip all tags for display
        clean_text = re.sub(r'\[.*?\]', '', raw_response).strip()
        self.show_speech(clean_text)
        self.speak_text(clean_text)
        self.chat_history.append({"role": "Pet", "content": clean_text})

    # -----------------------------------------------------------------------
    # TTS
    # -----------------------------------------------------------------------
    def speak_text(self, text):
        if not text:
            return
        self.media_player.stop()
        self.media_player.setMedia(QMediaContent())

        sounds_dir = os.path.join(self.base_dir, "sounds")
        for fname in os.listdir(sounds_dir):
            if fname.startswith("speech_") and fname.endswith(".mp3"):
                try:
                    os.remove(os.path.join(sounds_dir, fname))
                except Exception:
                    pass

        unique_ts = int(datetime.now().timestamp() * 1000)
        self.speech_output_path = os.path.join(sounds_dir, f"speech_{unique_ts}.mp3")

        tts_worker = TTSWorker(text, self.speech_output_path)
        self.active_tts_workers.add(tts_worker)
        tts_worker.finished.connect(self.play_speech)
        tts_worker.finished.connect(lambda path, w=tts_worker: self.active_tts_workers.discard(w))
        tts_worker.start()

    def play_speech(self, path):
        if path and os.path.exists(path):
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
            self.media_player.play()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = Tamagotchi()
    pet.show()
    sys.exit(app.exec_())
