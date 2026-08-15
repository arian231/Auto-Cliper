import json
from moviepy import VideoFileClip, TextClip, CompositeVideoClip

VIDEO = "short2_9x16.mp4"
JSON_FILE = "audio.json"
OUTPUT = "animated_caption.mp4"

with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

video = VideoFileClip(VIDEO)
caption_clips = []

for segment in data.get("segments", []):
    for word_data in segment.get("words", []):
        word = word_data.get("word", "").strip()
        start = word_data.get("start")
        end = word_data.get("end")

        if not word or start is None or end is None:
            continue

        caption = TextClip(
            text=word,
            font_size=75,
            color="white",
            stroke_color="black",
            stroke_width=4
        )

        caption = (
            caption
            .with_position(("center", 1500))
            .with_start(float(start))
            .with_end(float(end))
        )

        caption_clips.append(caption)

final = CompositeVideoClip([video] + caption_clips)

final.write_videofile(
    OUTPUT,
    codec="libx264",
    audio_codec="aac",
    fps=video.fps
)

video.close()
final.close()

print("DONE! Created:", OUTPUT)