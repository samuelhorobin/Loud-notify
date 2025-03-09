import tkinter as tk
from tkinter import ttk
import threading, pyaudio as pa, numpy as np, math, pygame, pystray
from PIL import Image, ImageDraw
MIN_DB, MAX_DB, thr_db, cur_db, trig, runn = -60, 0, -30, -100, False, True
p=pa.PyAudio()
def sMic():
 w=tk.Tk(); w.title("Select Mic")
 m=[(i, p.get_device_info_by_index(i)["name"]) for i in range(p.get_device_count()) if p.get_device_info_by_index(i).get("maxInputChannels",0)]
 sel=tk.IntVar(value=m[0][0] if m else -1)
 ttk.Label(w, text="Select Mic:").pack(padx=10,pady=10)
 c=ttk.Combobox(w, values=[f"{i}: {n}" for i,n in m], state="readonly", width=50)
 c.current(0); c.pack(padx=10,pady=10)
 ttk.Button(w, text="OK", command=lambda:[sel.set(m[c.current()][0]),w.destroy()]).pack(padx=10,pady=10)
 w.mainloop(); return sel.get()
mi=sMic()
CH, F, CHN, R = 1024, pa.paInt16, 1, 44100
st = p.open(format=F, channels=CHN, rate=R, input=True, input_device_index=mi, frames_per_buffer=CH)
pygame.mixer.pre_init(R,-16,2,512); pygame.mixer.init()
def tone(f=2000,d=0.2,sr=R):
 t=np.linspace(0,d,int(sr*d),False)
 t0=(0.5*np.sin(2*np.pi*f*t)*32767).astype(np.int16)
 return np.column_stack((t0,t0))
snd=pygame.sndarray.make_sound(tone())
root=tk.Tk(); root.title("Sound Detector"); root.geometry("400x280"); root.resizable(False,False)
s=ttk.Style(); s.theme_use("clam")
mf=ttk.Frame(root, padding=20); mf.pack(expand=True,fill="both")
ttk.Label(mf, text="Sound Detector", font=("Arial",18)).pack(pady=(0,10))
sl=ttk.Scale(mf, from_=MIN_DB, to=MAX_DB, orient=tk.HORIZONTAL, length=300)
sl.set(thr_db); sl.pack(pady=(0,10))
tl=ttk.Label(mf, text=f"Threshold: {thr_db:.1f} dB", font=("Arial",12)); tl.pack(pady=(0,10))
cl=ttk.Label(mf, text=f"Current: {cur_db:.1f} dB", font=("Arial",12)); cl.pack(pady=(0,10))
W, H = 300,20
cv=tk.Canvas(mf, width=W, height=H, bd=0, highlightthickness=0); cv.pack(pady=(0,10))
for x in range(W):
 frac=x/W; cv.create_line(x,0,x,H,fill=f'#{int(255*frac):02x}{int(255*(1-frac)):02x}00')
ov=cv.create_rectangle(0,0,W,H,fill="gray",outline="gray")
bf=ttk.Frame(mf); bf.pack(pady=(10,0))
ttk.Button(bf, text="Minimize to Tray", command=lambda: root.withdraw()).pack(side=tk.LEFT,padx=5)
ttk.Button(bf, text="Quit", command=lambda: q()).pack(side=tk.LEFT,padx=5)
def upd_thr(v):
 global thr_db; thr_db=float(v); tl.config(text=f"Threshold: {thr_db:.1f} dB")
sl.config(command=upd_thr)
def upd_bar(db):
 f=(db-MIN_DB)/(MAX_DB-MIN_DB); f=max(0,min(f,1))
 cv.coords(ov, f*W,0,W,H)
def upd_disp(db):
 cl.config(text=f"Current: {db:.1f} dB"); upd_bar(db)
def aud():
 global cur_db, trig, runn
 while runn:
  try: d=st.read(CH, exception_on_overflow=False)
  except Exception as e: print("Mic error:", e); continue
  ad=np.frombuffer(d, dtype=np.int16)
  if not ad.size: continue
  rms=math.sqrt(np.mean(ad.astype(np.float64)**2))
  cur_db=20*math.log10(rms/32768) if rms>0 else -100
  if cur_db>thr_db:
   if not trig: trig=True; snd.play()
  else: trig=False
  root.after(0, upd_disp, cur_db)
threading.Thread(target=aud, daemon=True).start()
def mk_ic():
 im=Image.new("RGB",(64,64),"black"); ImageDraw.Draw(im).rectangle((16,16,48,48), fill="white"); return im
def sh(ic, it): root.after(0, root.deiconify)
def ex(ic, it): root.after(0, q())
def q():
 global runn; runn=False; st.stop_stream(); st.close(); p.terminate(); ti.stop(); root.destroy()
m=pystray.Menu(pystray.MenuItem("Show", sh), pystray.MenuItem("Exit", ex))
ti=pystray.Icon("sd", mk_ic(), "Sound Detector", m)
threading.Thread(target=ti.run, daemon=True).start()
root.mainloop()
