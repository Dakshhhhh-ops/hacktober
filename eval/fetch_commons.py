"""Download the evaluation photos from Wikimedia Commons and write eval/SOURCES.md.

    python eval/fetch_commons.py

The photos are already committed in eval/images/, so you only need this to rebuild the
set. Each file is fetched at about 800 px wide and keeps its own licence (see SOURCES.md).
Standard library only.
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "DrishtiAI-eval/1.0 (https://github.com/Dakshhhhh-ops/hacktober)"}

# local file name -> Commons file title
PHOTOS = {
    "wet_floor_sign_1": "Wet floor sign CANEX.jpg",
    "wet_floor_sign_2": "Wet floor caution sugn.jpg",
    "wet_floor_sign_3": "Wet floor sign, Broen, Esbjerg, 1.jpg",
    "sign_subway": "Down the stairs for subway (4313246851).jpg",
    "stairs_down": "Down Stairs (5919861589).jpg",
    "stairs_pedway": "Stairs down to Pedway, Chicago (52730318979).jpg",
    "trip_hazard_pavement": "A trip hazard on Philip Lane, Haringey, London 02.jpg",
    "stair_edge_mall": "Stair TGSI and trip hazard, Westfield Chermside IMGP1749.jpg",
    "pothole_1": "Pothole in Villeray, Montréal.jpg",
    "pothole_2": "A pothole in Dilova Street in Kyiv.jpg",
    "open_manhole": "Open Manhole - New Orleans September 2020.jpg",
    "sidewalk_obstruction": "Moscow, Maroseyka Street, VTB advertising obstructing sidewalk 02.jpg",
    "plastic_barriers": "The Stow, Harlow, Essex, England - plastic barriers.jpg",
    "puddle_station": "Interior of Helsinki Central railway station with a puddle on the floor.jpg",
    "escalators": "Copenhagen Metro escalators.jpg",
    "empty_hallway_1": "Empty hallway in Blakney Building.jpg",
    "empty_hallway_2": "Empty hallway, Katzen Art Museum.jpg",
    "empty_hallway_exit": "Empty hallway with exit sign.jpg",
    "empty_office": "Empty room of office.jpg",
    "exit_sign": "EXIT SIGN.jpg",
    "fire_exit_sign": "Old-style fire exit sign (26009222722).jpg",
}


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as r:
        return r.read()


def plain(html: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", "", html or "").split())


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    images = HERE / "images"
    images.mkdir(exist_ok=True)
    rows = []
    for name, title in PHOTOS.items():
        query = urllib.parse.urlencode({
            "action": "query", "titles": "File:" + title, "prop": "imageinfo",
            "iiprop": "url|extmetadata", "iiurlwidth": 800, "format": "json"})
        page = next(iter(json.loads(get(f"{API}?{query}"))["query"]["pages"].values()))
        if "imageinfo" not in page:
            print(f"MISSING  {title}")
            continue
        info = page["imageinfo"][0]
        meta = info.get("extmetadata", {})
        data = get(info["thumburl"])
        if not data.startswith(b"\xff\xd8\xff"):
            print(f"NOT JPEG {title}")
            continue
        (images / f"{name}.jpg").write_bytes(data)
        licence = plain(meta.get("LicenseShortName", {}).get("value", "unknown"))
        licence_url = meta.get("LicenseUrl", {}).get("value", "")
        author = plain(meta.get("Artist", {}).get("value", "unknown"))[:80]
        rows.append((name, title, info["descriptionurl"], author, licence, licence_url))
        print(f"ok {len(data) // 1024:>4} KB  {name}.jpg  [{licence}]")

    lines = [
        "# Evaluation photo sources",
        "",
        "The photographs in `images/` (everything except `synthetic_*.png`) come from",
        "Wikimedia Commons, resized to about 800 px wide and otherwise unchanged. Each keeps",
        "the licence shown here, which is separate from this project's MIT licence.",
        "",
        "| File | Original | Author | Licence |",
        "| --- | --- | --- | --- |",
    ]
    for name, title, url, author, licence, licence_url in rows:
        shown = f"[{licence}]({licence_url})" if licence_url else licence
        lines.append(f"| `{name}.jpg` | [{title}]({url}) | {author} | {shown} |")
    (HERE / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(rows)} of {len(PHOTOS)} photos saved; SOURCES.md written")


if __name__ == "__main__":
    main()
