import sys
import os
import re
import requests
import math
import psutil
import ctypes
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QLineEdit
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen
from PyQt5.QtMultimedia import QSoundEffect

DEBUG = True

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
        
        self.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.model = "llama3.2:3b"
        self.system_prompt = "You are a cute, expressive virtual desktop pet. Keep answers short (1-2 sentences). You MUST end EVERY response with exactly one emotion tag in brackets. Choose from: [happy], [sad], [angry], [thinking], [bored], [excited], [sweating], [surprised]."
        
        # Memory System
        self.chat_history = [] 
        self.last_window_title = ""
        self.mouse_travel = 0

        # Sound System
        self.pop_sound = QSoundEffect()
        self.pop_sound.setSource(QUrl.fromLocalFile("sounds/pop.wav"))
        self.squeak_sound = QSoundEffect()
        self.squeak_sound.setSource(QUrl.fromLocalFile("sounds/squeak.wav"))

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

        layout.addWidget(self.speech)
        layout.addWidget(self.pet_canvas, alignment=Qt.AlignCenter)
        layout.addWidget(self.input_box)
        self.setLayout(layout)
        self.move(1200, 600)

        # AI Worker Thread
        self.worker = None

        # Idle & System Monitoring Timer
        self.system_timer = QTimer()
        self.system_timer.timeout.connect(self.monitor_system)
        self.system_timer.start(5000) # Check every 5 seconds

    def set_emotion(self, emotion):
        self.pet_canvas.emotion = emotion

    def show_speech(self, text):
        self.speech.setText(text)
        self.speech.show()
        if os.path.exists("sounds/pop.wav"):
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
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            active_title = buf.value.lower()

            if active_title != self.last_window_title and active_title:
                self.last_window_title = active_title
                if "code" in active_title or "visual studio" in active_title:
                    self.set_emotion("excited")
                    self.show_speech("Ooo, are we coding something cool? 💻")
                elif "youtube" in active_title:
                    self.set_emotion("happy")
                    self.show_speech("Whatcha watching? 👀")
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
            if os.path.exists("sounds/squeak.wav"):
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
                    content = f.read()[:1000] # Read first 1000 chars so we don't crash Ollama
                self.send_to_ollama(f"I just ate a file named {os.path.basename(file_path)}. Here is a taste of it: {content}. What do you think of the flavor?")
            else:
                self.show_speech("I can only eat text files! Yuck! [sad]")
                self.set_emotion("sad")

    # --- LLM COMMUNICATION ---
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

    def send_to_ollama(self, user_text):
        self.set_emotion("thinking")
        self.show_speech("Thinking... (-_-)")

        # Build Memory Context (Keep last 4 messages)
        self.chat_history.append({"role": "User", "content": user_text})
        if len(self.chat_history) > 4:
            self.chat_history.pop(0)

        full_prompt = f"{self.system_prompt}\n\n"
        for msg in self.chat_history:
            full_prompt += f"{msg['role']}: {msg['content']}\n"
        full_prompt += "Pet:"

        # Start background thread so animation doesn't freeze
        self.worker = OllamaWorker(self.ollama_url, self.model, full_prompt)
        self.worker.finished.connect(self.handle_ollama_response)
        self.worker.start()

    def handle_ollama_response(self, raw_response):
        # Extract Emotion
        match = re.search(r'\[([a-zA-Z]+)\]\s*$', raw_response)
        if match:
            self.set_emotion(match.group(1).lower())
        else:
            self.set_emotion("happy")

        clean_text = re.sub(r'\[.*?\]', '', raw_response).strip()
        self.show_speech(clean_text)
        
        # Save to memory
        self.chat_history.append({"role": "Pet", "content": clean_text})


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = Tamagotchi()
    pet.show()
    sys.exit(app.exec_())