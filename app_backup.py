from flask import Flask, render_template, request, send_from_directory, redirect, url_for
import os
import re
import subprocess

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

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

    filepath = os.path.join(
        UPLOAD_FOLDER,
        video.filename
    )

    video.save(filepath)

    return redirect(url_for("candidates_page"))


@app.route("/outputs/<path:filename>")
def output_file(filename):
    return send_from_directory(
        OUTPUT_FOLDER,
        filename
    )


@app.route("/candidates")
def candidates_page():

    candidates = []

    filename = "short_candidates.txt"

    if os.path.exists(filename):

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

            sentence = " ".join(
                lines[1:]
            ).strip()

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


@app.route("/create-short", methods=["POST"])
def create_short():

    start = float(request.form["start"])
    end = float(request.form["end"])

    duration = end - start

    videos = [
        os.path.join(
            UPLOAD_FOLDER,
            f
        )
        for f in os.listdir(UPLOAD_FOLDER)
        if f.lower().endswith(
            (".mp4", ".mov", ".mkv", ".webm")
        )
    ]

    if not videos:
        return "No uploaded video found."

    source = videos[-1]

    base_name = (
        f"short_{int(start * 100)}_"
        f"{int(end * 100)}"
    )

    raw_output = os.path.join(
        OUTPUT_FOLDER,
        base_name + "_raw.mp4"
    )

    ass_file = os.path.join(
        OUTPUT_FOLDER,
        base_name + ".ass"
    )

    final_output = os.path.join(
        OUTPUT_FOLDER,
        base_name + "_final.mp4"
    )

    # 1. Cut + 9:16
    cut_command = [
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
        cut_command,
        check=True
    )

    # 2. Create animated ASS caption
    caption_command = [
        "python",
        "make_short2_ass.py",
        str(start),
        str(end),
        ass_file
    ]

    subprocess.run(
        caption_command,
        check=True
    )

    # 3. Burn animated caption into video
    subtitle_path = ass_file.replace(
        "\\",
        "/"
    ).replace(
        ":",
        "\\:"
    )

    final_command = [
        "ffmpeg",
        "-y",
        "-i", raw_output,
        "-vf", f"ass='{subtitle_path}'",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        final_output
    ]

    subprocess.run(
        final_command,
        check=True
    )

    return f"""
    <h1>Short Created Successfully 🔥</h1>

    <p>
        {os.path.basename(final_output)}
    </p>

    <video
        width="360"
        controls
        playsinline
    >
        <source
            src="/outputs/{os.path.basename(final_output)}"
            type="video/mp4"
        >
    </video>

    <br><br>

    <a href="/candidates">
        ← Back to Candidates
    </a>
    """


if __name__ == "__main__":
    app.run(debug=True)