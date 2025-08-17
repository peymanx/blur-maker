from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance
import numpy as np

input_path = "me.jpg"
output_path = "animated_edge_strong.gif"

img = Image.open(input_path).convert("RGB")
width, height = img.size

box_size = 150
step_x = box_size
step_y = box_size

frames = []

# تصویر سمت راست برای لبه‌یابی تدریجی روی باکس‌ها
edge_canvas = Image.new("RGB", (width, height))
edge_canvas.paste(img)

# فونت برای متن بیشینه و جدول کرنل
try:
    font_max = ImageFont.truetype("arial.ttf", 24)
    font_kernel = ImageFont.truetype("arial.ttf", 14)
except:
    font_max = ImageFont.load_default()
    font_kernel = ImageFont.load_default()

kernel_size = 3
passed_boxes = []

for y in range(0, height, step_y):
    for x in range(0, width, step_x):
        x1, y1 = x, y
        x2, y2 = min(x + box_size, width), min(y + box_size, height)

        # سمت راست: اعمال لبه‌یابی تدریجی روی باکس‌های عبور کرده
        passed_boxes.append((x1, y1, x2, y2))
        right_display = img.copy()
        for bx in passed_boxes:
            region = right_display.crop(bx).filter(ImageFilter.FIND_EDGES)

            # افزایش شدت لبه با Contrast و Sharpen
            enhancer = ImageEnhance.Contrast(region)
            region = enhancer.enhance(1.5)  # افزایش کنتراست
            region = region.filter(ImageFilter.SHARPEN)  # شارپ کردن لبه

            edge_canvas.paste(region, bx)
        right_display = edge_canvas.copy()

        # سمت چپ: تصویر اصلی ثابت بدون تغییر
        left_half = img.copy()
        draw_left = ImageDraw.Draw(left_half)
        draw_left.rectangle([x1, y1, x2, y2], outline="green", width=4)

        # گرفتن کرنل 3x3 از باکس لبه‌یابی شده سمت راست
        kernel_region = right_display.crop((x1, y1, min(x1+kernel_size, x2), min(y1+kernel_size, y2)))
        kernel_data = np.array(kernel_region)

        # محاسبه بیشینه (max) پیکسل‌ها
        max_r = int(np.max(kernel_data[:, :, 0]))
        max_g = int(np.max(kernel_data[:, :, 1]))
        max_b = int(np.max(kernel_data[:, :, 2]))
        max_text = f"Max: R={max_r} G={max_g} B={max_b}"

        # رسم جدول اعداد زیر باکس سمت چپ
        cell_height = 35
        start_y = y2 + 10
        start_x = x1
        for i in range(kernel_data.shape[0]):
            for j in range(kernel_data.shape[1]):
                r, g, b = kernel_data[i, j]
                text = f"{r},{g},{b}"
                draw_left.text((start_x + j*100, start_y + i*cell_height), text, fill="yellow", font=font_kernel)

        draw_left.text((start_x, start_y + kernel_size*cell_height + 5), max_text, fill="red", font=font_max)

        # ترکیب تصویر نهایی کنار هم
        combined = Image.new("RGB", (width*2, height))
        combined.paste(left_half, (0, 0))
        combined.paste(right_display, (width, 0))
        frames.append(combined)

frames[0].save(
    output_path,
    save_all=True,
    append_images=frames[1:],
    duration=200,
    loop=0,
    optimize=True
)

print(f"GIF ساخته شد: {output_path}")
