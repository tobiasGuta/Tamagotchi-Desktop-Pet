# Tamagotchi Desktop Pet

A virtual desktop pet built with PyQt5. It features an animated vector interface, responds to user input via local LLMs (Ollama), and interacts with your system by monitoring resources and active windows.

## Features

- **Animated Interface:** Smooth vector graphics and animations reflecting the pet's current emotion (happy, sad, angry, thinking, bored, excited, sweating, surprised).
- **LLM Integration:** Powered by Ollama, enabling intelligent and contextual conversations.
- **System Monitoring:** Keeps track of your CPU and RAM usage, reacting when your system is under heavy load.
- **Context Awareness:** Monitors the active window (on Windows OS) and comments on your activities like coding or watching videos.
- **Interactive:** Follows your mouse, reacts to being poked, and supports drag-and-drop for "feeding" text files.
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

## Configuration

You can customize the Ollama URL via an environment variable if you are running it on a different host or port:

```bash
export OLLAMA_URL="http://localhost:11434/api/generate"
# or on Windows:
# set OLLAMA_URL="http://localhost:11434/api/generate"
```


https://github.com/user-attachments/assets/5044840e-db36-4737-baee-9276e1c903a1

https://github.com/user-attachments/assets/0a6c9f36-4a85-49b0-9c26-1e1cb64fb827

