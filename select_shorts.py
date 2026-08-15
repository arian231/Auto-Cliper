import re

SRT = "I Granted 100 Kids Their Biggest Wish! [lVylRtlPOIE].srt"

text = open(SRT, encoding="utf-8").read()

blocks = re.split(r"\n\s*\n", text)

items = []

for block in blocks:
    lines = block.strip().splitlines()

    if len(lines) < 3:
        continue

    timing = lines[1]

    if "-->" not in timing:
        continue

    start, end = timing.split(" --> ")

    start_sec = (
        int(start[0:2]) * 3600
        + int(start[3:5]) * 60
        + float(start[6:].replace(",", "."))
    )

    end_sec = (
        int(end[0:2]) * 3600
        + int(end[3:5]) * 60
        + float(end[6:].replace(",", "."))
    )

    sentence = " ".join(lines[2:]).strip()

    items.append({
        "start": start_sec,
        "end": end_sec,
        "text": sentence
    })


# Build 30–60 second candidate windows
clips = []

for i, item in enumerate(items):

    start = item["start"]
    text_parts = []

    for j in range(i, len(items)):

        end = items[j]["end"]
        duration = end - start

        if duration > 60:
            break

        text_parts.append(items[j]["text"])

        if 30 <= duration <= 60:

            sentence = " ".join(text_parts)

            score = 0

            keywords = [
                "cancer",
                "wish",
                "kids",
                "LeBron",
                "James",
                "Disney",
                "dream",
                "surprise",
                "million",
                "biggest",
                "amazing",
                "unbelievable"
            ]

            for word in keywords:
                if word.lower() in sentence.lower():
                    score += 2

            if "?" in sentence:
                score += 1

            if "!" in sentence:
                score += 1

            clips.append(
                (
                    score,
                    start,
                    end,
                    sentence
                )
            )

            break


# Highest score first
clips.sort(
    key=lambda x: x[0],
    reverse=True
)


with open(
    "short_candidates.txt",
    "w",
    encoding="utf-8"
) as f:

    for i, clip in enumerate(clips[:10], 1):

        score, start, end, sentence = clip

        f.write(
            f"{i}. SCORE={score} | "
            f"START={start:.2f} | "
            f"END={end:.2f} | "
            f"DURATION={end-start:.2f}\n"
        )

        f.write(
            sentence + "\n\n"
        )


print("30–60 second short candidates created!")
print("File: short_candidates.txt")