from flask import Flask, render_template, request, send_from_directory, redirect, url_for
import os
import re
import subprocess
import uuid

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
ASS_FILE = "short2_animated.ass"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    video = request.files.get("video")

    if not video or video.filename == "":
        return "No video selected"

    filepath = os.path.join(UPLOAD_FOLDER, video.filename)
    video.save(filepath)

    return redirect(url_for("candidates_page"))


@app.route("/outputs/<path:filename>")
def output_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)


@app.route("/candidates")
def candidates_page():

    candidates = []

    filename = "short_candidates.txt"

    if os.path.exists(filename):

        text = open(filename, encoding="utf-8").read()

        blocks = re.split(r"\n\s*\n", text)

        for block in blocks:

            lines = block.strip().splitlines()

            if len(lines) < 2:
                continue

            first = lines[0]
            sentence = " ".join(lines[1:]).strip()

            match = re.search(
                r"(\d+)\.\s*SCORE=(\d+)\s*\|\s*START=([\d.]+)\s*\|\s*END=([\d.]+)",
                first
            )

            if not match:
                continue

            candidates.append({
                "number": int(match.group(1)),
                "score": int(match.group(2)),
                "start": float(match.group(3)),
                "end": float(match.group(4)),
                "text": sentence
            })

    return render_template(
        "candidates.html",
        candidates=candidates
    )


def find_video():

    videos = [
        os.path.join(UPLOAD_FOLDER, f)
        for f in os.listdir(UPLOAD_FOLDER)
        if f.lower().endswith(
            (".mp4", ".mov", ".mkv", ".webm")
        )
    ]

    if not videos:
        return None

    return max(videos, key=os.path.getmtime)


def create_shifted_ass(start, end, output_ass):

    if not os.path.exists(ASS_FILE):
        return False

    with open(
        ASS_FILE,
        "r",
        encoding="utf-8-sig"
    ) as f:
        lines = f.readlines()

    output_lines = []

    for line in lines:

        if not line.startswith("Dialogue:"):
            output_lines.append(line)
            continue

        parts = line.rstrip("\n").split(",", 9)

        if len(parts) < 10:
            continue

        old_start = parts[1]
        old_end = parts[2]

        def parse_ass_time(t):
            h, m, s = t.split(":")
            return (
                int(h) * 3600
                + int(m) * 60
                + float(s)
            )

        def ass_time(seconds):

            seconds = max(0, seconds)

            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = seconds % 60

            return f"{h}:{m:02d}:{s:05.2f}"

        caption_start = parse_ass_time(old_start)
        caption_end = parse_ass_time(old_end)

        # Keep captions that overlap the selected clip
        if caption_end <= start:
            continue

        if caption_start >= end:
            continue

        new_start = max(caption_start, start) - start
        new_end = min(caption_end, end) - start

        if new_end <= new_start:
            continue

        parts[1] = ass_time(new_start)
        parts[2] = ass_time(new_end)

        output_lines.append(
            ",".join(parts) + "\n"
        )

    with open(
        output_ass,
        "w",
        encoding="utf-8-sig"
    ) as f:
        f.writelines(output_lines)

    return True


@app.route("/create-short", methods=["POST"])
def create_short():

    start = float(request.form["start"])
    end = float(request.form["end"])

    duration = end - start

    if duration < 30 or duration > 60:
        return "Short must be between 30 and 60 seconds."

    source = find_video()

    if not source:
        return "No uploaded video found."

    job_id = uuid.uuid4().hex[:8]

    raw_output = os.path.join(
        OUTPUT_FOLDER,
        f"short_{job_id}_raw.mp4"
    )

    final_output = os.path.join(
        OUTPUT_FOLDER,
        f"short_{job_id}_final.mp4"
    )

    shifted_ass = os.path.join(
        OUTPUT_FOLDER,
        f"captions_{job_id}.ass"
    )

    # Create vertical clip
    crop_command = [
        "ffmpeg",
        "-y",
        "-ss", str(start),
        "-i", source,
        "-t", str(duration),
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        raw_output
    ]

    subprocess.run(
        crop_command,
        check=True
    )

    # Create caption file shifted to clip timeline
    has_captions = create_shifted_ass(
        start,
        end,
        shifted_ass
    )

    if has_captions:

        caption_path = shifted_ass.replace(
            "\\",
            "/"
        ).replace(
            ":",
            "\\:"
        )

        caption_command = [
            "ffmpeg",
            "-y",
            "-i", raw_output,
            "-vf",
            f"ass='{caption_path}'",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-c:a", "copy",
            final_output
        ]

        subprocess.run(
            caption_command,
            check=True
        )

        os.remove(raw_output)

    else:

        os.rename(
            raw_output,
            final_output
        )

    return f"""
    <h1>Short Created Successfully 🔥</h1>

    <p>
        Duration: {duration:.2f} seconds
    </p>

    <video width="360" controls>
        <source
            src="/outputs/{os.path.basename(final_output)}"
            type="video/mp4"
        >
    </video>

    <br><br>

    <a href="/outputs/{os.path.basename(final_output)}"
       download>
        Download Short 🎬
    </a>

    <br><br>

    <a href="/candidates">
        ← Back to Candidates
    </a>
    """


if __name__ == "__main__":
    app.run(debug=True)