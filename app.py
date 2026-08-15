from flask import Flask, render_template, request, send_from_directory, redirect, url_for
import os
import re
import subprocess
import uuid
import zipfile

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

    command = [
        "python",
        "make_short2_ass.py",
        str(start),
        str(end),
        output_ass
    ]

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )

        print(result.stdout)

    except subprocess.CalledProcessError as e:
        print("Subtitle generation failed:")
        print(e.stdout)
        print(e.stderr)
        return False

    if not os.path.exists(output_ass):
        print("ASS file was not created.")
        return False

    with open(
        output_ass,
        "r",
        encoding="utf-8-sig"
    ) as f:
        text = f.read()

    dialogue_count = text.count("Dialogue:")

    print(
        "Generated caption lines:",
        dialogue_count
    )

    return dialogue_count > 0
@app.route("/download-all")
def download_all():

    zip_path = os.path.join(
        OUTPUT_FOLDER,
        "all_10_shorts.zip"
    )

    files = [
        f for f in os.listdir(OUTPUT_FOLDER)
        if f.endswith("_final.mp4")
    ]

    if not files:
        return "No completed Shorts found."

    with zipfile.ZipFile(
        zip_path,
        "w",
        zipfile.ZIP_DEFLATED
    ) as zipf:

        for filename in files:

            filepath = os.path.join(
                OUTPUT_FOLDER,
                filename
            )

            zipf.write(
                filepath,
                arcname=filename
            )

    return send_from_directory(
        OUTPUT_FOLDER,
        "all_10_shorts.zip",
        as_attachment=True
    )


@app.route("/create-all", methods=["POST", "GET"])
def create_all():
    candidates = []

    filename = "short_candidates.txt"

    if not os.path.exists(filename):
        return "short_candidates.txt not found."

    text = open(
        filename,
        encoding="utf-8"
    ).read()

    blocks = re.split(
        r"\n\s*\n",
        text
    )

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

    # Highest score first
    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    candidates = candidates[:10]

    source = find_video()

    if not source:
        return "No uploaded video found."

    created = []

    for candidate in candidates:

        start = candidate["start"]
        end = candidate["end"]

        duration = end - start

        if duration < 30 or duration > 60:
            continue

        job_id = uuid.uuid4().hex[:8]

        raw_output = os.path.join(
            OUTPUT_FOLDER,
            f"short_{job_id}_raw.mp4"
        )

        final_output = os.path.join(
            OUTPUT_FOLDER,
            f"short_{candidate['number']}_{job_id}_final.mp4"
        )

        shifted_ass = os.path.join(
            OUTPUT_FOLDER,
            f"captions_{job_id}.ass"
        )

        print(
            f"\nCreating Short #{candidate['number']}: "
            f"{start:.2f} -> {end:.2f}"
        )

        # 1. Create vertical video
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

        # 2. Generate subtitles
        has_captions = create_shifted_ass(
            start,
            end,
            shifted_ass
        )

        # 3. Burn subtitles
        if has_captions:

            caption_path = os.path.abspath(
                shifted_ass
            ).replace("\\", "/")

            caption_path = caption_path.replace(
                ":",
                "\\:"
            )

            caption_filter = (
                f"ass='{caption_path}'"
            )

            caption_command = [
                "ffmpeg",
                "-y",
                "-i", raw_output,
                "-vf", caption_filter,
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

            try:
                os.remove(raw_output)
            except:
                pass

        else:

            os.rename(
                raw_output,
                final_output
            )

        created.append({
            "number": candidate["number"],
            "start": start,
            "end": end,
            "duration": duration,
            "file": os.path.basename(final_output)
        })

        print(
            f"Finished Short #{candidate['number']}"
        )

    return render_template(
        "all_created.html",
        created=created
    )
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

    # 1. Create 9:16 video
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

    # 2. Shift captions to selected clip
    has_captions = create_shifted_ass(
        start,
        end,
        shifted_ass
    )

    # 3. Burn captions
    if has_captions:

        caption_path = os.path.abspath(
            shifted_ass
        ).replace("\\", "/")

        caption_path = caption_path.replace(
            ":",
            "\\:"
        )

        caption_filter = (
            f"ass='{caption_path}'"
        )

        caption_command = [
            "ffmpeg",
            "-y",
            "-i", raw_output,
            "-vf", caption_filter,
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

        try:
            os.remove(raw_output)
        except:
            pass

    else:

        os.rename(
            raw_output,
            final_output
        )

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Short Created</title>
        <style>
            body {{
                background:#0f1117;
                color:white;
                font-family:Arial;
                text-align:center;
                padding:40px;
            }}

            video {{
                max-width:360px;
                width:100%;
            }}

            a {{
                display:inline-block;
                margin:20px;
                padding:12px 24px;
                background:#6c5ce7;
                color:white;
                text-decoration:none;
                border-radius:8px;
            }}
        </style>
    </head>

    <body>

        <h1>🔥 Short Created Successfully!</h1>

        <p>
            Duration: {duration:.2f} seconds
        </p>

        <video controls>
            <source
                src="/outputs/{os.path.basename(final_output)}"
                type="video/mp4"
            >
        </video>

        <br>

        <a href="/outputs/{os.path.basename(final_output)}"
           download>
            Download Short 🎬
        </a>

        <a href="/candidates">
            ← Back to Candidates
        </a>

    </body>
    </html>
    """


if __name__ == "__main__":
    app.run()