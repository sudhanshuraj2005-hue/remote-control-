import socketio, pyautogui, cv2, numpy as np, base64, time, threading, psutil
from pystray import Icon
from PIL import Image, ImageDraw
import threading

sio = socketio.Client()
current_room = None
pyautogui.FAILSAFE = False

# Optional popup at start
def show_startup_message():
    try:
        from tkinter import Tk, Label
        root = Tk()
        root.overrideredirect(True)
        root.geometry("200x50+500+300")
        label = Label(root, text="Agent Running", bg="green", fg="white")
        label.pack(expand=True, fill="both")
        root.after(2000, root.destroy)
        root.mainloop()
    except:
        pass

threading.Thread(target=show_startup_message, daemon=True).start()

# Optional tray icon
def create_tray():
    image = Image.new('RGB', (64,64), color='green')
    d = ImageDraw.Draw(image)
    d.text((18,20), "R", fill="white")
    icon = Icon("BBSBEC", image, "Agent Running")
    threading.Thread(target=icon.run, daemon=True).start()

create_tray()

@sio.event
def connect():
    sio.emit('agent-ready')

@sio.on('start-streaming')
def start_stream(data):
    global current_room
    current_room = data['room']
    sio.emit('join-meeting', current_room)
    threading.Thread(target=stream, daemon=True).start()

def stream():
    global current_room
    while current_room:
        try:
            img = pyautogui.screenshot()
            frame = cv2.resize(np.array(img), (960,540))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 40])
            stats = {'cpu': psutil.cpu_percent(), 'ram': psutil.virtual_memory().percent}
            sio.emit('screen-data', {'room': current_room, 'image': base64.b64encode(buffer).decode('utf-8'), 'stats': stats})
            time.sleep(0.05)
        except:
            break

@sio.on('mouse-event')
def mouse(data):
    w,h = pyautogui.size()
    x = data["x"]*w
    y = data["y"]*h
    if data["type"]=="move": pyautogui.moveTo(x,y)
    elif data["type"]=="mousedown": pyautogui.mouseDown(x,y,button=data.get("button","left"))
    elif data["type"]=="mouseup": pyautogui.mouseUp(x,y,button=data.get("button","left"))

@sio.on('keyboard-event')
def keyboard(data):
    key = data["key"]
    if data["type"]=="down": pyautogui.keyDown(key)
    elif data["type"]=="up": pyautogui.keyUp(key)

if __name__=="__main__":
    try:
        sio.connect('http://192.168.1.4:3000')  # Replace with your server IP
        sio.wait()
    except:
        pass