import json
import sys


INPUT = "I Granted 100 Kids Their Biggest Wish! [lVylRtlPOIE].json"


def ass_time(seconds):
    seconds = max(0, seconds)

    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60

    return f"{h}:{m:02d}:{s:05.2f}"


if len(sys.argv) < 4:
    print("Usage: python make_short2_ass.py <start> <end> <output.ass>")
    sys.exit(1)


CLIP_START = float(sys.argv[1])
CLIP_END = float(sys.argv[2])
OUTPUT = sys.argv[3]


with open(INPUT, "r", encoding="utf-8") as f:
    data = json.load(f)


words = []

for segment in data.get("segments", []):

    for w in segment.get("words", []):

        text = w.get("word", "").strip()
        start = w.get("start")
        end = w.get("end")

        if not text or start is None or end is None:
            continue

        start = float(start)
        end = float(end)

        # Only words inside selected clip
        if end <= CLIP_START:
            continue

        if start >= CLIP_END:
            continue

        words.append({
            "text": text,
            "start": max(start, CLIP_START) - CLIP_START,
            "end": min(end, CLIP_END) - CLIP_START
        })


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


lines = [header]


# 3-word rolling animated caption
for i, current in enumerate(words):

    selected = words[
        max(0, i - 2):
        min(len(words), i + 3)
    ]

    caption_words = []

    for item in selected:

        if item is current:

            caption_words.append(
                r"{\c&H00FFFF&\fscx115\fscy115}"
                + item["text"] +
                r"{\c&HFFFFFF&\fscx100\fscy100}"
            )

        else:

            caption_words.append(
                item["text"]
            )

    text = " ".join(caption_words)

    line = (
        f"Dialogue: 0,"
        f"{ass_time(current['start'])},"
        f"{ass_time(current['end'])},"
        f"Caption,,0,0,0,,{text}\n"
    )

    lines.append(line)


with open(OUTPUT, "w", encoding="utf-8-sig") as f:
    f.writelines(lines)


print("DONE:", OUTPUT)