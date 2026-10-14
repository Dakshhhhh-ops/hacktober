"""Download the evaluation photos from Wikimedia Commons and write eval/SOURCES.md.

    python eval/fetch_commons.py                 # the tuning set, into eval/images/
    python eval/fetch_commons.py --set heldout   # the held-out set, into eval/heldout/images/

The photos are already committed, so you only need this to rebuild a set. Each file is fetched at about 800 px wide and keeps its own licence (see SOURCES.md).
Standard library only.
"""
import argparse
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

# Held out: never used while writing or tuning the prompts. Chosen to look like where the
# app would really be used in India, and to include more scenes with no hazard at all.
HELDOUT = {
    "broken_road_delhi": "Broken Roads in India's Capital New Delhi.jpg",
    "potholed_road_kolkata": "Potholed road outside Kolkata Airport.jpg",
    "potholes_bihar": "Roads in Bihar have potholes.jpg",
    "cow_street_delhi": "Cow on Delhi street.jpg",
    "cow_street_madurai": "Cow in Street - Madurai - India.JPG",
    "cows_road_delhi": "India - Delhi - 009 - cows hanging out on the road (2129391055).jpg",
    "autos_ahmedabad": "Auto rickshaws in Ahmedabad.jpg",
    "manhole_delhi": "Manhole in Delhi.jpg",
    "drain_unbuilt": "Drain yet to build (1).jpg",
    "platform_kanpur": "Platform 1 of Kanpur Central Railway Station, India.jpg",
    "platform_new_delhi": "Platform 16 of New Delhi Railway Station, India.jpg",
    "empty_road_1": "Empty roads.jpg",
    "empty_road_trees": "An empty road with trees along side.jpg",
    "living_room_kolkata": "Living Room - Acharya Bhaban - Kolkata 2009-08-14 1050.JPG",
    "gandhi_room": "Mahatma Gandhi's living room, sabarmati aashram.jpg",
    "station_board_hapur": "Hapur Junction railway station - Station board.jpg",
    "station_board_chandi_mandir": "Chandi Mandir railway station - Station board.jpg",
}
# Indian money, for the Money mode: official scans of both sides and photos of real notes.
CURRENCY = {
    "note_10_front": "India new 10 INR, MG series, 2018, obverse.jpg",
    "note_10_back": "India new 10 INR, MG series, 2018, reverse.jpg",
    "note_20_front": "India new 20 INR, MG series, 2019, obverse.jpg",
    "note_20_back": "India new 20 INR, MG series, 2019, reverse.jpg",
    "note_50_back_old": "India 50 INR, MG series, 2011, reverse.jpg",
    "note_100_front": "Rs 100 note front view.jpg",
    "note_100_back": "Rs 100 note back view.jpg",
    "note_100_photo": "Hundred rupee note India.jpg",
    "note_200_front": "India, 200 INR, 2018, obverse.jpg",
    "note_200_back": "India, 200 INR, 2018, reverse.jpg",
    "note_200_photo": "Indian Note 200.jpg",
    "note_200_photo_back": "Indian Note 200 Back side.jpg",
    "note_200_photo_2": "200 rupee note.jpg",
    "note_500_front": "India new 500 INR, MG series, 2016, obverse.jpg",
    "note_500_back": "India new 500 INR, MG series, 2016, reverse.jpg",
    "notes_100_2000": "Indian 100 and 2000 rupee notes (32190943222).jpg",
    "coin_20": "Indian 20 Rupee coin.png",
    "coin_1": "One Rupee.jpg",
}
SETS = {"tuning": (PHOTOS, HERE), "heldout": (HELDOUT, HERE / "heldout"),
        "currency": (CURRENCY, HERE / "currency")}


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as r:
        return r.read()


def plain(html: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", "", html or "").split())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", choices=SETS, default="tuning")
    photos, folder = SETS[parser.parse_args().set]
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    images = folder / "images"
    images.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, title in photos.items():
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
        suffix = (".jpg" if data.startswith(b"\xff\xd8\xff")
                  else ".png" if data.startswith(b"\x89PNG") else "")
        if not suffix:
            print(f"NOT AN IMAGE {title}")
            continue
        (images / f"{name}{suffix}").write_bytes(data)
        licence = plain(meta.get("LicenseShortName", {}).get("value", "unknown"))
        licence_url = meta.get("LicenseUrl", {}).get("value", "")
        author = plain(meta.get("Artist", {}).get("value", "unknown"))[:80]
        rows.append((name + suffix, title, info["descriptionurl"], author, licence, licence_url))
        print(f"ok {len(data) // 1024:>4} KB  {name}{suffix}  [{licence}]")

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
        lines.append(f"| `{name}` | [{title}]({url}) | {author} | {shown} |")
    (folder / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(rows)} of {len(photos)} photos saved; SOURCES.md written")


if __name__ == "__main__":
    main()
