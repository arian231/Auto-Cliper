import json
from PIL import Image, ImageDraw, ImageFont

DATA = "I Granted 100 Kids Their Biggest Wish! [lVylRtlPOIE].json"

d = json.load(open(DATA, encoding="utf-8"))
words = [w for s in d["segments"] for w in s.get("words", []) if w["start"] < 33.03]

print("Animated caption data loaded!")
print("Words:", len(words))
print("First word:", words[0]["word"].strip())
print("Last word:", words[-1]["word"].strip())