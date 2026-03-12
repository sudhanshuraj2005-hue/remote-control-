import socketio, pyautogui, cv2, numpy as np, base64, time, threading, psutil, ctypes, os, sys, argparse
from pystray import Icon
from PIL import Image, ImageDraw

# --- CONFIGURATION ---
parser = argparse.ArgumentParser(description="Sudhanshu Remote Agent")

# HARDCODED YOUR IP HERE:
# This ensures that when the user runs the EXE, it automatically connects to 192.168.1.4
DEFAULT_URL = "http://10.214.252.182:3000"

parser.add_argument("--url", help="Server URL", default=os.getenv("SERVER_URL", DEFAULT_URL))
args = parser.parse_args()

SERVER_URL = args.url

# --- PERFORMANCE OPTIMIZATIONS ---
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False
pyautogui.MINIMUM_DURATION = 0

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

# Enable automatic reconnection logic
sio = socketio.Client(reconnection=True, reconnection_attempts=0, reconnection_delay=1)
current_room = None
streaming_active = False

@sio.event
def connect():
    global current_room
    print(f"✅ Connected to: {SERVER_URL}")
    sio.emit("agent-ready")
    
    # Re-join room if connection flickers during Viva
    if current_room:
        print(f"🔄 Re-joining session: {current_room}")
        sio.emit("join-meeting", current_room)

@sio.event
def disconnect():
    print("❌ Connection lost. Searching for server...")

@sio.on("start-streaming")
def start(data):
    global current_room, streaming_active
    current_room = data["room"]
    print(f"🚀 Stream authorized for room: {current_room}")
    sio.emit("join-meeting", current_room)
    
    if not streaming_active:
        threading.Thread(target=stream_loop, daemon=True).start()

def stream_loop():
    global current_room, streaming_active
    streaming_active = True
    print("📺 Streaming thread started.")
    
    while True:
        if not current_room or not sio.connected:
            time.sleep(1)
            continue
            
        try:
            img = pyautogui.screenshot()
            frame = cv2.resize(np.array(img), (960, 540)) 
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 40])
            
            sio.emit("screen-data", {
                "room": current_room,
                "image": base64.b64encode(buffer).decode('utf-8'),
                "stats": {
                    "cpu": psutil.cpu_percent(), 
                    "ram": psutil.virtual_memory().percent
                }
            })
            time.sleep(0.05) 
            
        except Exception as e:
            print(f"Stream flicker: {e}")
            time.sleep(1)

@sio.on("mouse-event")
def mouse(data):
    try:
        w, h = pyautogui.size()
        x = max(0, min(w, int(data["x"] * w)))
        y = max(0, min(h, int(data["y"] * h)))
        
        if data["type"] == "move":
            pyautogui.moveTo(x, y, _pause=False)
        elif data["type"] == "mousedown":
            pyautogui.mouseDown(x, y)
        elif data["type"] == "mouseup":
            pyautogui.mouseUp(x, y)
    except:
        pass

@sio.on("keyboard-event")
def keyboard(data):
    key = data["key"]
    special_keys = {
        "Control": "ctrl", "Shift": "shift", "Alt": "alt", "Meta": "win",
        "Enter": "enter", "Backspace": "backspace", "Tab": "tab",
        "Escape": "esc", "ArrowUp": "up", "ArrowDown": "down",
        "ArrowLeft": "left", "ArrowRight": "right", " ": "space"
    }
    target_key = special_keys.get(key, key.lower())
    try:
        if data["type"] == "down":
            pyautogui.keyDown(target_key)
        elif data["type"] == "up":
            pyautogui.keyUp(target_key)
    except:
        pass

def create_tray():
    try:
        image = Image.new('RGB', (64,64), color='green')
        d = ImageDraw.Draw(image)
        d.text((18,20), "R", fill="white")
        icon = Icon("RemoteAgent", image, "Remote Agent Active")
        icon.run()
    except:
        pass

if __name__=="__main__":
    threading.Thread(target=create_tray, daemon=True).start()
    
    print(f"📡 Attempting connection to {SERVER_URL}...")
    
    while True:
        try:
            if not sio.connected:
                sio.connect(SERVER_URL)
            sio.wait()
        except Exception as e:
            print(f"Waiting for server at {SERVER_URL}...")
            time.sleep(2)