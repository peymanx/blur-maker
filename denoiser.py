import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk

# --- تنظیمات اولیه ---
root = tk.Tk()
root.title("نمایش فیلترها روی تصویر | @peymanx")

effect_mode = tk.StringVar(value="gaussian")
box_size = 200
motion_angle = 0  # زاویه موشن بلر
motion_length = 15  # شدت موشن بلر

img_path = r"me.jpg"
img = cv2.imread(img_path)
if img is None:
    raise FileNotFoundError(f"تصویر {img_path} پیدا نشد")

h, w = img.shape[:2]

# --- Canvas ---
canvas = tk.Canvas(root, width=w, height=h, cursor="cross")
canvas.pack(side="left")
img_tk = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
canvas_img = canvas.create_image(0, 0, anchor="nw", image=img_tk)

mouse_x, mouse_y = -1, -1

# --- افکت محدب برای Liquid Glass ---
def create_radial_gradient(shape, center=None, radius=None):
    h, w = shape[:2]
    if center is None:
        center = (w//2, h//2)
    if radius is None:
        radius = min(w,h)//2
    Y, X = np.ogrid[:h, :w]
    dist = np.sqrt((X - center[0])**2 + (Y - center[1])**2)
    mask = np.clip(1 - dist/radius, 0, 1)
    return mask[..., np.newaxis]

def apply_convex_effect(roi):
    h_roi, w_roi = roi.shape[:2]
    Y,X = np.meshgrid(np.arange(h_roi), np.arange(w_roi), indexing='ij')
    cx, cy = w_roi/2, h_roi/2
    dx = (X - cx)/(w_roi/2)
    dy = (Y - cy)/(h_roi/2)
    r = np.sqrt(dx**2 + dy**2)
    r = np.clip(r,0,1)
    k = 0.15
    X_new = X - dx*k*w_roi*r
    Y_new = Y - dy*k*h_roi*r
    map_x = X_new.astype(np.float32)
    map_y = Y_new.astype(np.float32)
    warped = cv2.remap(roi, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return warped

def motion_blur_kernel(length, angle):
    """ساخت کرنل Motion Blur"""
    rad = np.deg2rad(angle)
    x = int(length*np.cos(rad))
    y = int(length*np.sin(rad))
    size = max(abs(x), abs(y), 1)
    kernel = np.zeros((size*2+1, size*2+1), dtype=np.float32)
    cx = cy = size
    for i in range(length):
        xi = int(cx + i*np.cos(rad))
        yi = int(cy + i*np.sin(rad))
        if 0 <= xi < kernel.shape[1] and 0 <= yi < kernel.shape[0]:
            kernel[yi, xi] = 1
    kernel /= kernel.sum() if kernel.sum()!=0 else 1
    return kernel

def apply_effect():
    global img_tk, mouse_x, mouse_y, img, motion_angle
    temp = img.copy()
    if mouse_x==-1 or mouse_y==-1:
        img_tk = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(temp, cv2.COLOR_BGR2RGB)))
        canvas.itemconfig(canvas_img, image=img_tk)
        canvas.image = img_tk
        return

    x1, y1 = max(0, mouse_x-box_size//2), max(0, mouse_y-box_size//2)
    x2, y2 = min(w, mouse_x+box_size//2), min(h, mouse_y+box_size//2)
    roi = temp[y1:y2, x1:x2]

    if effect_mode.get()=="gaussian":
        roi_effect = cv2.GaussianBlur(roi, (15,15),0)
        method = "mean"
    elif effect_mode.get()=="box":
        roi_effect = cv2.blur(roi,(15,15))
        method = "mean"
    elif effect_mode.get()=="edge":
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray,100,200)
        roi_effect = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        method = "max"
    elif effect_mode.get()=="median":
        roi_effect = cv2.medianBlur(roi,15)
        method = "median"
    elif effect_mode.get()=="motion":
        k = motion_blur_kernel(motion_length, motion_angle)
        roi_effect = cv2.filter2D(roi,-1,k)
        method = "motion"
    elif effect_mode.get()=="liquid":
        blur = cv2.GaussianBlur(roi,(15,15),0)
        warped = apply_convex_effect(blur)
        gradient = create_radial_gradient(warped.shape)
        light = np.ones_like(warped, dtype=np.float32)*255
        base_float = warped.astype(np.float32)
        base_float = base_float*(1-gradient*0.5)+light*(gradient*0.5)
        h_roi, w_roi = warped.shape[:2]
        reflection = np.zeros_like(base_float,dtype=np.float32)
        rx = int((mouse_x-x1)/max(1,x2-x1)*w_roi)
        ry = int((mouse_y-y1)/max(1,y2-y1)*h_roi)
        for i in range(h_roi):
            intensity = max(0,1-abs(i-ry)/(h_roi/4))
            reflection[i,:,:] = intensity*255
        roi_effect = np.clip(base_float + reflection*0.15,0,255).astype(np.uint8)
        method = "liquid"
    else:
        roi_effect = roi
        method = "none"

    temp[y1:y2, x1:x2] = roi_effect
    cv2.rectangle(temp,(x1,y1),(x2,y2),(0,255,0),2)
    img_tk = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(temp, cv2.COLOR_BGR2RGB)))
    canvas.itemconfig(canvas_img,image=img_tk)
    canvas.image = img_tk

    # --- نمایش RGB و کرنل 3x3 ---
    if roi_effect.shape[0]>=3 and roi_effect.shape[1]>=3:
        r = roi_effect[0:3,0:3,2]
        g = roi_effect[0:3,0:3,1]
        b = roi_effect[0:3,0:3,0]
        label_r.config(text=f"R:\n{r}")
        label_g.config(text=f"G:\n{g}")
        label_b.config(text=f"B:\n{b}")
    if effect_mode.get()=="motion":
        k = motion_blur_kernel(motion_length,motion_angle)
        label_kernel.config(text=f"Kernel 3x3:\n{k[:3,:3]}")

def mouse_move(event):
    global mouse_x, mouse_y
    mouse_x, mouse_y = event.x, event.y
    apply_effect()

def mouse_leave(event):
    global mouse_x, mouse_y
    mouse_x, mouse_y = -1,-1
    apply_effect()

def mouse_scroll(event):
    global box_size, motion_angle
    shift = (event.state & 0x1)!=0
    if shift:
        if event.delta>0:
            motion_angle = (motion_angle+5)%360
        else:
            motion_angle = (motion_angle-5)%360
    else:
        if event.delta>0:
            box_size = min(box_size+10,min(w,h))
        else:
            box_size = max(box_size-10,10)
    apply_effect()

def open_image():
    global img, w, h, canvas
    path = filedialog.askopenfilename(filetypes=[("Images","*.jpg *.png *.bmp")])
    if not path:
        return
    img = cv2.imread(path)
    if img is None:
        tk.messagebox.showerror("Error","Cannot open image")
        return
    h,w = img.shape[:2]
    canvas.config(width=w,height=h)
    apply_effect()

# --- Bind ها ---
canvas.bind("<Motion>", mouse_move)
canvas.bind("<Leave>", mouse_leave)
canvas.bind_all("<MouseWheel>", mouse_scroll)
canvas.bind_all("<Button-4>", lambda e: mouse_scroll(e))
canvas.bind_all("<Button-5>", lambda e: mouse_scroll(e))

# --- Frame کنترل‌ها ---
ctrl_frame = ttk.Frame(root)
ctrl_frame.pack(side="right", fill="y", padx=10, pady=10)

# انتخاب فیلتر
ttk.Label(ctrl_frame,text="Filter:").pack()
filters = [("Gaussian Blur","gaussian"),("Box Blur","box"),("Median","median"),
           ("Edge","edge"),("Motion Blur","motion"),("Liquid Glass","liquid")]
for t,v in filters:
    ttk.Radiobutton(ctrl_frame,text=t,variable=effect_mode,value=v,command=apply_effect).pack(anchor="w")

# ترک‌بار موشن
ttk.Label(ctrl_frame,text="Motion Angle").pack(pady=(10,0))
motion_slider = ttk.Scale(ctrl_frame, from_=0, to=360, orient="horizontal", command=lambda x: apply_effect())
motion_slider.pack(fill="x")
motion_slider.set(motion_angle)

# دکمه Open
ttk.Button(ctrl_frame,text="Open Image",command=open_image).pack(pady=10)

# --- نمایش RGB و Kernel ---
label_r = ttk.Label(ctrl_frame,text="R:"); label_r.pack()
label_g = ttk.Label(ctrl_frame,text="G:"); label_g.pack()
label_b = ttk.Label(ctrl_frame,text="B:"); label_b.pack()
label_kernel = ttk.Label(ctrl_frame,text="Kernel 3x3:"); label_kernel.pack(pady=(10,0))

# --- کلید میانبر ---
def shortcut(event):
    key = event.char
    mapping = {"1":"gaussian","2":"box","3":"median","4":"edge","5":"motion","6":"liquid"}
    if key in mapping:
        effect_mode.set(mapping[key])
        apply_effect()
root.bind("<Key>", shortcut)

# --- اجرای اولیه ---
apply_effect()
root.mainloop()
