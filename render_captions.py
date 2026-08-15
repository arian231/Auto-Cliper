import json
import subprocess
from PIL import Image, ImageDraw, ImageFont

VIDEO = "short1_vertical.mp4"
DATA = "I Granted 100 Kids Their Biggest Wish! [lVylRtlPOIE].json"
OUT = "animated_caption.mp4"

W, H = 1080, 1920
FPS = 30

d = json.load(open(DATA, encoding="utf-8"))
words = [
    w for s in d["segments"]
    for w in s.get("words", [])
    if w["start"] < 33.03
]

font_path = "C:/Windows/Fonts/arialbd.ttf"
font = ImageFont.truetype(font_path, 78)

frames_dir = "caption_frames"
import os
os.makedirs(frames_dir, exist_ok=True)

def make_frame(t):
    img = Image.new("RGBA", (W, 400), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    active = None
    for i, w in enumerate(words):
        if w["start"] <= t <= w["end"]:
            active = i
            break

    if active is None:
        return img

    start = max(0, active - 2)
    end = min(len(words), active + 3)
    selected = words[start:end]

    text = " ".join(x["word"].strip() for x in selected)

    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=4)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2
    y = 120

    current_x = x

    for i in range(start, end):
        word = words[i]["word"].strip()
        if not word:
            continue

        # Pop effect
        scale = 1.0
        if i == active:
            progress = min(1.0, max(0.0, (t - words[i]["start"]) / 0.12))
            scale = 1.0 + 0.15 * (1 - progress)

        fsize = int(78 * scale)
        f = ImageFont.truetype(font_path, fsize)

        color = (255, 220, 40, 255) if i == active else (255, 255, 255, 255)

        draw.text(
            (current_x, y),
            word,
            font=f,
            fill=color,
            stroke_width=6,
            stroke_fill=(0, 0, 0, 255)
        )

        bb = draw.textbbox((0, 0), word, font=f)
        current_x += bb[2] - bb[0] + 18

    return img

# Create transparent caption video
cmd = [
    "ffmpeg", "-y",
    "-i", VIDEO,
    "-vf",
    "drawtext=text='':x=0:y=0",
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-an",
    "base_video.mp4"
]

subprocess.run(cmd)

print("Caption renderer prepared!")
print("Words:", len(words))
print("Output:", OUT)