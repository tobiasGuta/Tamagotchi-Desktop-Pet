# Tamagotchi Desktop Pet

A virtual desktop pet built with PyQt5. It features an animated vector interface, responds to user input via local LLMs (Ollama), and interacts with your system by monitoring resources and active windows.

## Features

- **Animated Interface & Personality:** Smooth vector graphics reflecting various emotions. Animations naturally slow down at night as the pet gets sleepy.
- **Voice Responses:** Speaks your LLM's responses out loud dynamically using high-quality Microsoft Edge TTS ("JennyNeural").
- **Time & Weather Aware:** Understands your local weather/time dynamically on startup to give context-aware greetings.
- **Long-Term Memory:** Extracts facts and preferences about you during conversations (saved to `memory.json`), letting it remember things days later!
- **System & App Monitoring:** Keeps track of CPU/RAM load. Detects when you open music apps (Spotify, Apple Music) to dance or groans if you're coding well past midnight.
- **Idle Detection:** Notices if you've been AFK for over 10 minutes and complains about being bored.
- **Interactive & Expressive:** Reacts in real-time letter-by-letter as you type (curious -> invested -> impatient). Follows your mouse, and loves being feed text files via drag-and-drop.
- **Clipboard Reading:** Type "read this" in the input box to let the pet read and comment on your clipboard content.

## Prerequisites

- Python 3.x
- Ollama running locally (by default, it uses the llama3.2:3b model).

## Installation

1. Install the required dependencies using pip:

```bash
pip install -r requirements.txt
```

## Windows 

```bash
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

```bash
.\venv\Scripts\activate
```

2. Ensure Ollama is running in the background with the proper model pulled:

```bash
ollama run llama3.2:3b
```

## Usage

Run the main Python script to launch your pet:

```bash
python Tamagotchi.py
```

### Controls

- **Move:** Click and drag the pet to move it around your screen.
- **Poke/Jump:** Left-click the pet to make it jump.
- **Petting:** Wiggle your mouse over the pet to make it happy.
- **Chat:** Double-click the pet to open/close the text input box.
- **Feed:** Drag and drop text files (.txt, .py, .md) onto the pet.
- **Quit:** Right-click the pet to open a context menu to exit the app.

## Configuration

You can customize the Ollama URL via an environment variable if you are running it on a different host or port:

```bash
export OLLAMA_URL="http://localhost:11434/api/generate"
# or on Windows:
# set OLLAMA_URL="http://localhost:11434/api/generate"
```
https://github.com/user-attachments/assets/5044840e-db36-4737-baee-9276e1c903a1

https://github.com/user-attachments/assets/0a6c9f36-4a85-49b0-9c26-1e1cb64fb827
