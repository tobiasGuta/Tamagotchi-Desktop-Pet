import sys
import os
import re
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

if sys.platform == "win32":
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

# --- STARTUP WORKER FOR TIME/WEATHER AWARENESS ---
class StartupContextWorker(QThread):
    finished = pyqtSignal(dict)

    def run(self):
        context = {}
        # Time Awareness
        hour = datetime.now().hour
        if 5 <= hour < 12: context['time'] = "Morning"
        elif 12 <= hour < 17: context['time'] = "Afternoon"
        elif 17 <= hour < 22: context['time'] = "Evening"
        else: context['time'] = "Late Night"
        
        # Weather Awareness
        try:
            geo = requests.get("https://get.geojs.io/v1/ip/geo.json", timeout=5).json()
            lat, lon, city = geo.get('latitude', ''), geo.get('longitude', ''), geo.get('city', '')
            if lat and lon:
                weather_res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true", timeout=5).json()
                wcode = weather_res.get('current_weather', {}).get('weathercode', 0)
                temp = weather_res.get('current_weather', {}).get('temperature', 0)
                
                weather_desc = "Clear"
                if wcode in [1, 2, 3]: weather_desc = "Cloudy"
                elif wcode in [45, 48]: weather_desc = "Foggy"
                elif wcode in [51, 53, 55, 56, 57]: weather_desc = "Drizzling"
                elif wcode in [61, 63, 65, 66, 67]: weather_desc = "Raining"
                elif wcode in [71, 73, 75, 77]: weather_desc = "Snowing"
                elif wcode in [95, 96, 99]: weather_desc = "Thunderstorm"
                
                context['weather'] = f"{weather_desc}, {temp}°C in {city}"
        except Exception:
            context['weather'] = "Unknown weather"
            
        self.finished.emit(context)


# --- BACKGROUND WORKER FOR EDGE-TTS (Prevents UI Freezing) ---
class TTSWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, text, output_path):
        super().__init__()
        self.text = text
        self.output_path = output_path

    def run(self):
        try:
            # edge-tts requires asyncio event loop on this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            communicate = edge_tts.Communicate(self.text, "en-US-JennyNeural", rate="+10%")
            loop.run_until_complete(communicate.save(self.output_path))
            loop.close()
            self.finished.emit(self.output_path)
        except Exception as e:
            print(f"TTS Error: {e}")
            self.finished.emit("")


# --- BACKGROUND WORKER FOR MEMORY EXTRACTION ---
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
            prompt = f"Extract a brief fact (hobby, plan, project, preference) about the user from this message if it contains long-term info. If none, reply 'NONE'. Keep it under 15 words. Talk about the user in third person ('User'). Today is {today}. Message: '{self.text}'"
            response = requests.post(
                self.url,
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=15 
            )
            data = response.json()
            if "response" in data:
                self.finished.emit(data["response"].strip())
        except Exception:
            self.finished.emit("NONE")


# --- BACKGROUND WORKER FOR OLLAMA (Prevents UI Freezing) ---
class OllamaWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, url, model, prompt):
        super().__init__()
        self.url = url
        self.model = model
        self.prompt = prompt

    def run(self):
        try:
            response = requests.post(
                self.url,
                json={"model": self.model, "prompt": self.prompt, "stream": False},
                timeout=30 
            )
            response_json = response.json()
            if "error" in response_json:
                self.finished.emit(f"Error: {response_json['error']} [sad]")
            else:
                self.finished.emit(response_json["response"])
        except Exception as e:
            self.finished.emit(f"My brain disconnected... {e} [sad]")


# --- THE ANIMATED VECTOR PET ---
class AnimatedPetGraphics(QWidget):
    def __init__(self):
        super().__init__()
        self.emotion = "happy"
        self.frame = 0
        self.blink_timer = 0
        self.jump_offset = 0 
        self.setFixedSize(200, 200)

        # 60 FPS Timer
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.animate_frame)
        self.anim_timer.start(16) 

    def poke(self):
        self.jump_offset = -40 # Makes the pet jump up
        self.emotion = "surprised"

    def animate_frame(self):
        self.frame += 1
        self.blink_timer += 1
        if self.blink_timer > 180:
            self.blink_timer = 0
            
        # Gravity for jumping
        if self.jump_offset < 0:
            self.jump_offset += 2 # Fall back down
        else:
            self.jump_offset = 0
            
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Base Variables depending on emotion
        color = QColor(255, 180, 200) # Pink
        bounce_speed = 0.08
        bounce_height = 8
        eye_state = "open"

        if self.emotion == "sad":
            color = QColor(120, 160, 255)
            bounce_speed = 0.03
            bounce_height = 3
            eye_state = "half"
        elif self.emotion == "angry":
            color = QColor(255, 100, 100)
            bounce_speed = 0.4
            bounce_height = 5
            eye_state = "angry"
        elif self.emotion == "thinking":
            color = QColor(200, 150, 255)
            bounce_speed = 0.05
            bounce_height = 12
            eye_state = "open"
        elif self.emotion == "bored":
            color = QColor(160, 160, 160)
            bounce_speed = 0.02
            bounce_height = 2
            eye_state = "closed"
        elif self.emotion == "excited":
            color = QColor(255, 220, 100)
            bounce_speed = 0.3
            bounce_height = 20
            eye_state = "open"
        elif self.emotion == "sweating":
            color = QColor(255, 80, 80) # Hot red
            bounce_speed = 0.5 # Fast breathing
            bounce_height = 6
            eye_state = "angry"
        elif self.emotion == "surprised":
            color = QColor(180, 255, 200) # Mint
            bounce_speed = 0.0
            bounce_height = 0
            eye_state = "wide"

        # Time-based slowdown
        hour = datetime.now().hour
        if 0 <= hour < 5 or hour >= 23:
            bounce_speed *= 0.4 # Very tired and slow
        elif 20 <= hour < 23:
            bounce_speed *= 0.7 # Getting sleepy

        # Math for breathing/bouncing animation + Jumping
        offset_y = (math.sin(self.frame * bounce_speed) * bounce_height) + self.jump_offset
        center_x = 100
        center_y = 100 + offset_y

        # Draw Shadow
        shadow_width = max(30, 80 - (offset_y * 1.5))
        painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(center_x - shadow_width/2), 160, int(shadow_width), 15)

        # Draw Body
        painter.setBrush(QBrush(color))
        painter.drawEllipse(int(center_x - 50), int(center_y - 40), 100, 80)
        painter.drawEllipse(int(center_x - 55), int(center_y - 10), 110, 50) 

        # Draw Eyes
        painter.setBrush(QBrush(QColor(40, 40, 40)))
        eye_y = int(center_y - 10)
        left_eye_x = int(center_x - 25)
        right_eye_x = int(center_x + 10)

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

# --- MAIN APP ---
class Tamagotchi(QWidget):
    def __init__(self):
        super().__init__()
        
        # Base Dir & Config
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.base_dir, "config.json")
        self.memory_path = os.path.join(self.base_dir, "memory.json")
        
        self.config = self.load_or_create_config()
        self.pet_name = self.config.get("pet_name", "Tamagotchi")
        self.long_term_memory = self.load_memory()

        self.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.model = "llama3.2:3b"
        self.system_prompt = f"You are a cute, expressive virtual desktop pet named {self.pet_name}. Keep answers short (1-2 sentences)."
        
        # Memory System
        self.chat_history = collections.deque(maxlen=8) 
        self.last_window_title = ""
        self.mouse_travel = 0
        self.is_bored_idle = False

        # Sound System
        os.makedirs(os.path.join(self.base_dir, "sounds"), exist_ok=True)
        self.speech_output_path = "" # Generated dynamically to avoid file locks
        self.media_player = QMediaPlayer()

        self.pop_sound_path = os.path.join(self.base_dir, "sounds", "pop.wav")
        self.squeak_sound_path = os.path.join(self.base_dir, "sounds", "squeak.wav")
        self.pop_sound = QSoundEffect()
        self.pop_sound.setSource(QUrl.fromLocalFile(self.pop_sound_path))
        self.squeak_sound = QSoundEffect()
        self.squeak_sound.setSource(QUrl.fromLocalFile(self.squeak_sound_path))

        # Window setup (Accepts Drops for Feeding!)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(350, 350)
        self.setAcceptDrops(True) 
        self.setMouseTracking(True) # For petting

        layout = QVBoxLayout()
        
        self.speech = QLabel("")
        self.speech.setWordWrap(True)
        self.speech.setAlignment(Qt.AlignCenter)
        self.speech.setStyleSheet("color: white; background-color: rgba(30, 30, 30, 230); border: 2px solid #a8ffb2; border-radius: 10px; padding: 12px; font-size: 14px; font-weight: bold;")
        self.speech.hide() 
        
        self.pet_canvas = AnimatedPetGraphics()
        self.pet_canvas.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Type 'read this' to read clipboard...")
        self.input_box.setStyleSheet("background-color: rgba(255, 255, 255, 0.95); border: 2px solid #a8ffb2; border-radius: 8px; padding: 6px; color: black;")
        self.input_box.hide()
        self.input_box.returnPressed.connect(self.process_user_input)
        self.input_box.textChanged.connect(self.on_typing)

        layout.addWidget(self.speech)
        layout.addWidget(self.pet_canvas, alignment=Qt.AlignCenter)
        layout.addWidget(self.input_box)
        self.setLayout(layout)
        self.move(1200, 600)

        # AI Worker Thread
        self.active_ollama_workers = set()
        self.active_tts_workers = set()
        self.active_memory_workers = set()

        # Idle & System Monitoring Timer
        self.system_timer = QTimer()
        self.system_timer.timeout.connect(self.monitor_system)
        self.system_timer.start(5000) # Check every 5 seconds

        # Start initial context fetch (Weather & Time)
        self.startup_worker = StartupContextWorker()
        self.startup_worker.finished.connect(self.on_startup_context_ready)
        self.startup_worker.start()

    def load_or_create_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # If not exists or corrupted, ask for pet name
        name, ok = QInputDialog.getText(None, "New Pet!", "What should we call your new pet?")
        name = name.strip() if ok and name.strip() else "Tamagotchi"
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

    def on_startup_context_ready(self, context):
        time_str = context.get('time', 'Unknown time')
        weather_str = context.get('weather', 'Unknown weather')
        
        # Add system context to the first prompt
        greeting_prompt = f"*System Note: You just woke up. It's {time_str} and the weather outside is {weather_str}. Give the user a short personalized greeting!*"
        
        QTimer.singleShot(1000, lambda: self.send_to_ollama(greeting_prompt))

    def set_emotion(self, emotion):
        self.pet_canvas.emotion = emotion

    def show_speech(self, text):
        self.speech.setText(text)
        self.speech.show()
        if os.path.exists(self.pop_sound_path):
            self.pop_sound.play()

    # --- SENSORS & BRAIN ---
    def monitor_system(self):
        # 1. Check PC Resources
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        if cpu > 85 or ram > 90:
            self.set_emotion("sweating")
            self.show_speech(f"It's getting hot in here! CPU: {cpu}%, RAM: {ram}% 🥵")
            return

        # 2. Check Active Window (Windows OS specific)
        if sys.platform != "win32":
            return
        
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            active_title = buf.value.lower()

            if active_title != self.last_window_title and active_title:
                self.last_window_title = active_title
                if "spotify" in active_title or "youtube music" in active_title or "apple music" in active_title:
                    self.set_emotion("happy")
                    self.show_speech("Ooo, I love this song! 🎵 *dances*")
                elif "code" in active_title or "visual studio" in active_title:
                    hour = datetime.now().hour
                    if 0 <= hour < 5:
                        self.set_emotion("angry")
                        self.show_speech("Go to sleep! It's too late for coding! 💢")
                    else:
                        self.set_emotion("excited")
                        self.show_speech("Ooo, are we coding something cool? 💻")
                elif "youtube" in active_title:
                    self.set_emotion("happy")
                    self.show_speech("Whatcha watching? 👀")
        except:
            pass # Fails gracefully on non-Windows

        # 3. Check System Idle Time (Windows API)
        try:
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            idle_seconds = millis / 1000.0
            
            if idle_seconds > 600: # 10 minutes
                if not getattr(self, 'is_bored_idle', False):
                    self.is_bored_idle = True
                    self.send_to_ollama("*System Note: The user has been completely idle and away from their computer for 10 minutes. Get their attention or complain about being bored!*")
            else:
                self.is_bored_idle = False
        except:
            pass # Fails gracefully on non-Windows

    # --- INTERACTIVITY ---
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            # Dragging the window
            self.move(event.globalPos() - self.dragPosition)
        elif not event.buttons():
            # Hovering / Petting
            self.mouse_travel += 1
            if self.mouse_travel > 40: # If mouse wiggled a lot over pet
                self.set_emotion("happy")
                self.mouse_travel = 0
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            self.pet_canvas.poke() # Jump!
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
                self.show_speech("I'm listening! 💬")

    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        context_menu.addAction(quit_action)
        context_menu.exec_(event.globalPos())

    # --- FEEDING (DRAG & DROP) ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            self.set_emotion("surprised")
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            if file_path.endswith('.txt') or file_path.endswith('.py') or file_path.endswith('.md'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()[:1000].rsplit('\n', 1)[0] # Read first 1000 chars so we don't crash Ollama
                self.send_to_ollama(f"I just ate a file named {os.path.basename(file_path)}. Here is a taste of it: {content}. What do you think of the flavor?")
            else:
                self.show_speech("I can only eat text files! Yuck! [sad]")
                self.set_emotion("sad")

    # --- LLM COMMUNICATION ---
    def on_typing(self, text):
        if self.active_ollama_workers:
            return  # Don't interrupt "thinking" or waiting state
            
        length = len(text)
        if length == 0:
            self.set_emotion("happy")
        elif length <= 10:
            self.set_emotion("thinking") # Curious at first
        elif length <= 25:
            self.set_emotion("surprised") # Getting invested
        else:
            self.set_emotion("bored") # Impatient, taking too long

    def process_user_input(self):
        text = self.input_box.text().strip()
        if not text: return

        self.input_box.clear()
        self.input_box.hide()

        # Clipboard Awareness
        if text.lower() == "read this":
            clipboard_text = QApplication.clipboard().text()
            if clipboard_text:
                text = f"The user copied this text to their clipboard. Read it and comment on it: '{clipboard_text}'"
            else:
                text = "I tried to read the clipboard but it was empty!"

        self.send_to_ollama(text)

    def handle_memory_extracted(self, fact):
        if fact and "NONE" not in fact.upper() and len(fact) > 5 and len(fact) < 150:
            date_str = datetime.now().strftime("%Y-%m-%d")
            self.long_term_memory.append(f"[{date_str}] {fact}")
            self.long_term_memory = self.long_term_memory[-15:] # Keep latest 15 facts cleaner than pop(0)
            self.save_memory()

    def send_to_ollama(self, user_text):
        self.set_emotion("thinking")
        self.show_speech("Thinking... (-_-)")

        # Trigger Long-Term Memory Extraction but guard against System Notes
        if not user_text.startswith("*System Note"):
            mem_worker = MemoryWorker(self.ollama_url, self.model, user_text)
            self.active_memory_workers.add(mem_worker)
            mem_worker.finished.connect(self.handle_memory_extracted)
            mem_worker.finished.connect(lambda res, w=mem_worker: self.active_memory_workers.discard(w))
            mem_worker.start()

        # Build Memory Context (Keep last 8 messages)
        self.chat_history.append({"role": "User", "content": user_text})

        # Add Long Term Memory Context if it exists
        lt_memory_context = ""
        if self.long_term_memory:
            facts = '\n- '.join(self.long_term_memory)
            lt_memory_context = f"\n[Long-term memories about the user:\n- {facts}]\n"

        full_prompt = f"{self.system_prompt}{lt_memory_context}\n\n"
        for msg in self.chat_history:
            full_prompt += f"{msg['role']}: {msg['content']}\n"
        full_prompt += "Pet:"

        # Start background thread so animation doesn't freeze
        ollama_worker = OllamaWorker(self.ollama_url, self.model, full_prompt)
        self.active_ollama_workers.add(ollama_worker)
        ollama_worker.finished.connect(self.handle_ollama_response)
        ollama_worker.finished.connect(lambda res, w=ollama_worker: self.active_ollama_workers.discard(w))
        ollama_worker.start()

    def handle_ollama_response(self, raw_response):
        if raw_response.startswith("Error") or raw_response.startswith("My brain disconnected"):
            if self.chat_history and self.chat_history[-1]["role"] == "User":
                self.chat_history.pop()

        # Extract Emotion
        match = re.search(r'\[([a-zA-Z]+)\]\s*$', raw_response)
        if match:
            self.set_emotion(match.group(1).lower())
        else:
            self.set_emotion("happy")

        clean_text = re.sub(r'\[.*?\]', '', raw_response).strip()
        self.show_speech(clean_text)
        
        # Start TTS (Voice)
        self.speak_text(clean_text)
        
        # Save to memory
        self.chat_history.append({"role": "Pet", "content": clean_text})

    def speak_text(self, text):
        if not text: return
        
        # 1. Stop current audio and explicitly release the file lock for Windows
        self.media_player.stop()
        self.media_player.setMedia(QMediaContent())
        
        # 2. Clean up any previous speech.mp3 files to prevent folder bloat
        sounds_dir = os.path.join(self.base_dir, "sounds")
        for fname in os.listdir(sounds_dir):
            if (fname.startswith("speech_") and fname.endswith(".mp3")) or fname == "speech.mp3":
                file_to_del = os.path.join(sounds_dir, fname)
                try:
                    os.remove(file_to_del)
                except Exception:
                    pass # Keep going if file is locked
                    
        # 3. Create a unique mp3 name for THIS message so edge-tts never hits "Permission Denied"
        unique_timestamp = int(datetime.now().timestamp() * 1000)
        self.speech_output_path = os.path.join(sounds_dir, f"speech_{unique_timestamp}.mp3")
        
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
