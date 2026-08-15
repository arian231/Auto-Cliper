import json
import subprocess
import os

VIDEO = "short1_vertical.mp4"
DATA = "I Granted 100 Kids Their Biggest Wish! [lVylRtlPOIE].json"
ASS = "animated.ass"
OUTPUT = "short1_animated.mp4"

d = json.load(open(DATA, encoding="utf-8"))

words = [
    w for s in d["segments"]
    for w in s.get("words", [])
    if w["start"] < 33.03
]

def ass_time(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"

header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Caption,Arial,82,&H00FFFFFF,&H0000FFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,6,2,5,40,40,100,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""

events = []

for i, w in enumerate(words):
    start = w["start"]
    end = w["end"]

    a = max(0, i - 2)
    b = min(len(words), i + 3)

    parts = []

    for j in range(a, b):
        text = words[j]["word"].strip()

        if j == i:
            # Yellow + slightly larger current word
            parts.append(
                r"{\c&H00FFFF&\fscx115\fscy115}" + text +
                r"{\c&HFFFFFF&\fscx100\fscy100}"
            )
        else:
            parts.append(text)

    caption = " ".join(parts)
    events.append(
        f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{caption}"
    )

with open(ASS, "w", encoding="utf-8-sig") as f:
    f.write(header)
    f.write("\n".join(events))

subprocess.run([
    "ffmpeg", "-y",
    "-i", VIDEO,
    "-vf", f"ass={ASS}",
    "-c:v", "libx264",
    "-preset", "fast",
    "-crf", "20",
    "-c:a", "copy",
    OUTPUT
])

print("DONE!")
print("Created:", OUTPUT)