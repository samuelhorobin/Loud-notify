import tkinter as tk
from tkinter import ttk
import threading
import pyaudio
import numpy as np
import math
import pygame
import pystray
from PIL import Image, ImageDraw

MIN_DB = -60
MAX_DB = 0
threshold_db = -30
current_db = -100
triggered = False
running = True

p = pyaudio.PyAudio()

def select_microphone():
    win = tk.Tk()
    win.title("Select Microphone")
    mic_list = []
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info.get("maxInputChannels", 0) > 0:
            mic_list.append((i, info.get("name")))
    selected = tk.IntVar(value=mic_list[0][0] if mic_list else -1)
    lbl = ttk.Label(win, text="Select Microphone:")
    lbl.pack(padx=10, pady=10)
    combo = ttk.Combobox(win, values=[f"{i}: {name}" for i, name in mic_list],
                         state="readonly", width=50)
    combo.current(0)
    combo.pack(padx=10, pady=10)
    def on_select():
        selected.set(mic_list[combo.current()][0])
        win.destroy()
    btn = ttk.Button(win, text="OK", command=on_select)
    btn.pack(padx=10, pady=10)
    win.mainloop()
    return selected.get()

mic_index = select_microphone()

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=mic_index,
                frames_per_buffer=CHUNK)

pygame.mixer.pre_init(RATE, -16, 2, 512)
pygame.mixer.init()

def generate_tone(frequency=2000, duration=0.2, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = 0.5 * np.sin(2 * np.pi * frequency * t)
    tone = (tone * 32767).astype(np.int16)
    tone = np.column_stack((tone, tone))
    return tone

tone_samples = generate_tone()
tone_sound = pygame.sndarray.make_sound(tone_samples)

root = tk.Tk()
root.title("Sound Detector")
root.geometry("400x280")
root.resizable(False, False)
style = ttk.Style()
style.theme_use("clam")

main_frame = ttk.Frame(root, padding=20)
main_frame.pack(expand=True, fill="both")

title_label = ttk.Label(main_frame, text="Sound Detector", font=("Arial", 18))
title_label.pack(pady=(0, 10))

threshold_slider = ttk.Scale(main_frame, from_=MIN_DB, to=MAX_DB, orient=tk.HORIZONTAL, length=300)
threshold_slider.set(threshold_db)
threshold_slider.pack(pady=(0, 10))

threshold_label = ttk.Label(main_frame, text=f"Threshold: {threshold_db:.1f} dB", font=("Arial", 12))
threshold_label.pack(pady=(0, 10))

current_label = ttk.Label(main_frame, text=f"Current: {current_db:.1f} dB", font=("Arial", 12))
current_label.pack(pady=(0, 10))

level_canvas_width = 300
level_canvas_height = 20
level_canvas = tk.Canvas(main_frame, width=level_canvas_width, height=level_canvas_height, bd=0, highlightthickness=0)
level_canvas.pack(pady=(0, 10))

def draw_gradient(canvas, width, height):
    for x in range(width):
        frac = x / width
        r = int(255 * frac)
        g = int(255 * (1 - frac))
        color = f'#{r:02x}{g:02x}00'
        canvas.create_line(x, 0, x, height, fill=color)

draw_gradient(level_canvas, level_canvas_width, level_canvas_height)
overlay_id = level_canvas.create_rectangle(0, 0, level_canvas_width, level_canvas_height, fill="gray", outline="gray")

button_frame = ttk.Frame(main_frame)
button_frame.pack(pady=(10, 0))
minimize_button = ttk.Button(button_frame, text="Minimize to Tray", command=lambda: root.withdraw())
minimize_button.pack(side=tk.LEFT, padx=5)
quit_button = ttk.Button(button_frame, text="Quit", command=lambda: on_quit())
quit_button.pack(side=tk.LEFT, padx=5)

def on_threshold_change(value):
    global threshold_db
    threshold_db = float(value)
    threshold_label.config(text=f"Threshold: {threshold_db:.1f} dB")
threshold_slider.config(command=on_threshold_change)

def update_level_bar(db_val):
    frac = (db_val - MIN_DB) / (MAX_DB - MIN_DB)
    if frac < 0:
        frac = 0
    elif frac > 1:
        frac = 1
    fill_length = frac * level_canvas_width
    level_canvas.coords(overlay_id, fill_length, 0, level_canvas_width, level_canvas_height)

def update_display(db_val):
    current_label.config(text=f"Current: {db_val:.1f} dB")
    update_level_bar(db_val)

def audio_loop():
    global current_db, triggered, running
    while running:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
        except Exception as e:
            print("Error reading microphone:", e)
            continue
        audio_data = np.frombuffer(data, dtype=np.int16)
        if audio_data.size == 0:
            continue
        mean_square = np.mean(audio_data.astype(np.float64)**2)
        rms = np.sqrt(mean_square)
        current_db = 20 * math.log10(rms / 32768) if rms > 0 else -100
        if current_db > threshold_db:
            if not triggered:
                triggered = True
                tone_sound.play()
        else:
            triggered = False
        root.after(0, update_display, current_db)

audio_thread = threading.Thread(target=audio_loop, daemon=True)
audio_thread.start()

def create_icon_image():
    image = Image.new("RGB", (64, 64), "black")
    dc = ImageDraw.Draw(image)
    dc.rectangle((16, 16, 48, 48), fill="white")
    return image

def on_show(icon, item):
    root.after(0, root.deiconify)

def on_exit(icon, item):
    root.after(0, on_quit)

def on_quit():
    global running
    running = False
    stream.stop_stream()
    stream.close()
    p.terminate()
    tray_icon.stop()
    root.destroy()

menu = pystray.Menu(pystray.MenuItem("Show", on_show), pystray.MenuItem("Exit", on_exit))
tray_icon = pystray.Icon("sound_detector", create_icon_image(), "Sound Detector", menu)

def run_tray():
    tray_icon.run()

tray_thread = threading.Thread(target=run_tray, daemon=True)
tray_thread.start()

root.mainloop()
