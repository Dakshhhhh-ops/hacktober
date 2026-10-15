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
    # Moved from the held-out set on 15 October 2026: their failures shaped a prompt change.
    "flooded_handpump_chennai": "India - Chennai - Monsoon - 05 (3058218683).jpg",
    "flooded_street_dibrugarh": "Flood in Dibrugarh.jpg",
    "flooded_street_mumbai": "Bombay flooded street2.jpg",
    "ghat_steps_varanasi": "Ghats of Varanasi and Hindu rituals 35.jpg",
    "station_stairs_ernakulam": "Ernakulam Junction railway station platform stairs (10574174465).jpg",
    "promenade_marine_drive": "Marine Drive on an afternoon..jpg",
    "covered_walkway_rajghat": "Rajghat Garden 2.jpg",
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
    # Added 15 October 2026: more ground hazards seen on foot, and more scenes with none.
    "potholes_puddle_auto": "Driving through potholes.jpg",
    "potholes_muddy_lane": "Potholes on road.jpg",
    "pothole_bengaluru": "Roads deformed T munnekollala Bengaluru.jpg",
    "flooded_street_chennai": "India - Chennai - Monsoon - 06 (3059058000).jpg",
    "flooded_street_kanchipuram": "India - Kanchipuram - 010 (1885517933).jpg",
    "manhole_charminar": "Manhole cover at Charminar.jpg",
    "cow_footpath_mumbai": "Lascar Hindu Woman touching a cow, believed to be sacred in Hinduism (4558210703).jpg",
    "blocked_footpath_mumbai": "Homeless people in Mumbai block the side-walks.jpg",
    "cows_dog_road_delhi": "20191205 Krowy i pies na ulicy Delhi 0838 6776.jpg",
    "dog_footpath_pune": "Stray dog in the streets of Pune.jpg",
    "station_stairs_santragachi": "Santragachi railway station at Santragachi, Howrah 05.jpg",
    "crowded_street_kolkata": "Kolkata (4143290213).jpg",
    "footpath_churchgate": "Churchgate2.JPG",
    "footpath_banyan": "Footpath near baniyan tree.JPG",
    "empty_road_kolkata": "Alipore Road - Hastings - Kolkata 2015-02-07 2165.JPG",
    # Added 15 October 2026, after 7 photos above moved to the tuning set, to test the
    # prompt change on photos it was not made from.
    "flooded_colony_hyderabad": "A Flooded Colony in Hyderabad.jpg",
    "flooded_cars_hyderabad": "2020 Hyderabad floods.jpg",
    "waterlogged_street_vadodara": "1.1 Water logged street in front of the home during floods at Vadodara in July 2019.jpg",
    "flooded_house": "Flood affected house (2).jpg",
    "flooded_path": "Flood affected road.jpg",
    "flooded_road_kerala": "Kerala Flood 2024.jpg",
    "temple_steps_palitana": "Palitana, Shatrunjaya, dholis, pilgrims, and steps (9825131513).jpg",
    "hill_steps_mokalla": "Steps at Mokalla parvatam.JPG",
    "metro_entrance_delhi": "Central Secretariat metro station entrance.JPG",
    "metro_stairs_rohini": "Rohini East Metro Station 01.png",
    "ghat_people_varanasi": "People Varanasi Ghats 3.jpg",
    "ghat_rituals_varanasi": "Ghats of Varanasi and Hindu rituals 38.jpg",
    "platform_stairs_ramrajatala": "Ramrajatala railway station 04.jpg",
    "stray_dog_kolkata": "Stray Dog - Kolkata 05907.JPG",
    "crossing_kolkata": "Mahatma Gandhi Road - Amharst Street Crossing - Kolkata 2015-02-09 2282.JPG",
    "footpath_morning_walk": "BEAUTIFUL MORNING WALK WITH MOM.jpg",
    "park_walkway_digha": "Digha Amravati Park walkway 1.jpg",
    "zoo_walkway_vandalur": "VandalurZoo 18Aug2012 Walkway.JPG",
    "rose_garden_walkway": "Walkway through the rose garden.jpg",
    "hill_road_nilgiris": "MDR 700 Below Kalhatty Nilgiris Sep24 A7CR 02953.jpg",
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
