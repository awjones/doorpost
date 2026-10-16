"""What each built-in special-day picture shows and when it comes up, grouped the way Settings > Special days lists
them (each group folded away until you open it; tap a picture for this write-up and its code)."""

GROUPS = [
    ("Church year", ["palm", "goodfriday", "easter", "reformation", "xmaseve", "christmas", "churchglass", "vbs"]),
    ("U.S. holidays", ["newyear", "mlk", "valentine", "presidents", "mothers", "memorial", "fathers", "july4", "labor",
                       "veterans", "thanksgiving"]),
    ("Family days", ["school", "camping", "pattern"]),
    ("Trips and vacations", ["beach", "roadtrip", "flight", "trip", "cruise"]),
    ("Parks and water parks", ["park", "waterpark"]),
    ("Trains", ["gardentrain", "trains"]),
    ("Family milestones", ["birthday", "anniversary", "firstday", "graduation"]),
    ("Kids' activities", ["baseball", "soccer", "football", "recital", "schoolplay", "movienight"]),
    ("Scouts", ["courtofhonor", "pinewood", "scoutcamp"]),
    ("Church life", ["picnic", "missiontrip", "churchcamp", "christmasprogram", "fallfestival", "baptism"]),
    ("Seasons", ["spring", "summer", "fall", "winter", "snowday"]),
    ("Outings", ["zoo", "aquarium", "fair", "statepark", "lake", "pumpkinpatch", "applepicking", "christmaslights", "treefarm"]),
    ("Visitors and evenings", ["grandparents", "reunion", "datenight"]),
]

NAMES = {
    "palm": "Palm Sunday", "goodfriday": "Good Friday", "easter": "Resurrection Sunday", "reformation": "Reformation Day",
    "xmaseve": "Christmas Eve", "christmas": "Christmas Day", "churchglass": "Generic for church", "vbs": "VBS",
    "newyear": "New Year's", "mlk": "MLK Day", "valentine": "Valentine's Day", "presidents": "Presidents' Day",
    "mothers": "Mother's Day", "memorial": "Memorial Day", "fathers": "Father's Day", "july4": "4th of July",
    "labor": "Labor Day", "veterans": "Veterans Day", "thanksgiving": "Thanksgiving", "school": "School's out",
    "camping": "Camping", "pattern": "Gold pattern (no picture)", "beach": "Beach", "roadtrip": "Road trip",
    "flight": "Air travel", "trip": "Any trip", "cruise": "Cruise",
    "park": "Any amusement park", "waterpark": "Water park lodge",
    "gardentrain": "Garden train / train show", "trains": "Train chasing",
}

ABOUT = {
    "palm": "Palm branches crossed on deep green, for the Sunday Jesus rode into Jerusalem.",
    "goodfriday": "Three crosses on a dark hill. A quiet, solemn picture with no countdown.",
    "easter": "The empty tomb at sunrise, the stone rolled away.",
    "reformation": "The Wittenberg church door with the 95 Theses nailed to it.",
    "xmaseve": "Three candles glowing in the dark.",
    "christmas": "The star over the stable.",
    "churchglass": "A stained-glass cross in a church window, for any church event.",
    "vbs": "A white church under a bright sun with pennants and an open Bible.",
    "newyear": "Fireworks over the new year's number.",
    "mlk": "A mountain at sunrise, from the “I have been to the mountaintop” speech.",
    "valentine": "Hearts on deep red.",
    "presidents": "A columned capitol under a ring of stars.",
    "mothers": "A pot of pink flowers.",
    "memorial": "Rows of white headstones with a flag at half staff.",
    "fathers": "A fishing pole cast at sunset.",
    "july4": "Fireworks over the flag.",
    "labor": "A golden wheat field under a full moon.",
    "veterans": "The flag on its pole above five stars.",
    "thanksgiving": "A wheat sheaf, pumpkins and a pie.",
    "school": "A yellow school bus heading off under the sun.",
    "camping": "A tent and campfire among pines under the moon.",
    "pattern": "The gold lattice with the family monogram. Use it for a special day that needs no picture.",
    "beach": "A palm tree, umbrella and the sun setting over the water.",
    "roadtrip": "A red car with luggage on top driving toward the mountains.",
    "flight": "A plane climbing through the clouds.",
    "trip": "A map with a dotted route, a pin and a suitcase.",
    "cruise": "A big modern cruise ship from the side, heading right, with foam at the bow and stern.",
    "park": "A Ferris wheel, coaster and carousel. The sign shows the park's name from the event title or location (add your parks' names under Words).",
    "waterpark": "A timber lodge entrance with the water park behind: a play fort, a tipping bucket and slides.",
    "gardentrain": "A large-scale steam engine and caboose on a trestle among rocks and flowers.",
    "trains": "A steam engine on the main line at sunset with a crossing sign.",
    "birthday": "Their photo (Settings › Family) in a round gold frame, their name on the banner, a cake and balloons. A present waits in the frame for anyone without a photo.",
    "anniversary": "Two gold rings with roses and hearts.",
    "firstday": "An apple on a stack of books in front of a chalkboard.",
    "graduation": "A cap with its tassel and a diploma.",
    "baseball": "A ball and bat over a diamond under the lights.",
    "soccer": "A ball in front of the goal.",
    "football": "A football in front of the goal posts.",
    "recital": "A grand piano on stage in the spotlight, with music notes.",
    "schoolplay": "Comedy and drama masks between red curtains.",
    "movienight": "Popcorn, pillows and a movie on the screen.",
    "courtofhonor": "A silver eagle medal on its red, white and blue ribbon, with a scroll.",
    "pinewood": "Pinewood Derby cars racing down the track toward the checkered flag.",
    "scoutcamp": "A canoe on the lake with pines and a flagpole.",
    "picnic": "A checked blanket and basket under a tree, the church in the distance.",
    "missiontrip": "A globe with a route and a pin marked with a cross, and a suitcase.",
    "churchcamp": "Cabins by a hill with a cross and a campfire.",
    "christmasprogram": "A choir and manger on stage under the star.",
    "fallfestival": "Hay bales, pumpkins, corn stalks and string lights.",
    "baptism": "A dove coming down over the water in rays of light.",
    "spring": "A blossoming tree and tulips.",
    "summer": "Sunflowers under a big sun.",
    "fall": "An orange maple with leaves falling.",
    "winter": "Snowy pines under the moon.",
    "snowday": "A snowman and sled by a house with smoke from the chimney.",
    "zoo": "A giraffe, an elephant and an acacia tree.",
    "aquarium": "A sea turtle, fish and a jellyfish under the water.",
    "fair": "A blue first-place ribbon, a red barn and a Ferris wheel.",
    "statepark": "A trail through the pines to a waterfall, with a trail sign.",
    "lake": "A boat by the dock on a sunny lake.",
    "pumpkinpatch": "A pumpkin field with a red wagon and barn.",
    "applepicking": "Apple trees, a ladder and a full basket.",
    "christmaslights": "A car driving past houses strung with lights.",
    "treefarm": "A tree tied on the car roof at a snowy tree farm.",
    "grandparents": "A house with rocking chairs on the porch and a heart in the window.",
    "reunion": "A big tree full of hearts over a long picnic table.",
    "datenight": "A candlelit table for two with a rose, the city at night behind.",
}

# What brings these up by themselves (besides title words and "photo:" lines).
AUTOMATIC = {
    "palm": "Comes up by itself on Palm Sunday when it's checked under Church year.",
    "goodfriday": "Comes up by itself on Good Friday (Church year).",
    "easter": "Comes up by itself on Resurrection Sunday (Church year).",
    "reformation": "Comes up by itself on October 31 (Church year).",
    "xmaseve": "Comes up by itself on December 24 (Church year).",
    "christmas": "Comes up by itself on December 25 (Church year).",
    **{k: "Comes up by itself on the holiday when it's set to Special under Holidays from Google."
       for k in ("newyear", "mlk", "valentine", "presidents", "mothers", "memorial", "fathers", "july4", "labor",
                 "veterans", "thanksgiving")},
    **{k: "Comes up by itself on the first day of the season, on quiet days (not Sundays)."
       for k in ("spring", "summer", "fall", "winter")},
    "birthday": "Comes up by itself on birthdays set on the Family page, and for calendar events like “Child 1's birthday”.",
}


def guide(themes: set, words: list[dict]) -> list[dict]:
    """The groups for Settings, each picture with its name, write-up, what brings it up and its code."""
    from .scenes_family import NAMES as FAMILY_NAMES
    names = {**NAMES, **{k: v[0] for k, v in FAMILY_NAMES.items()}}
    picked_by: dict[str, list[str]] = {}
    for w in words or []:
        if w.get("look"):
            picked_by.setdefault(w["look"], []).append(w["word"] + (" (with ⭐)" if w.get("picture_only") else ""))
    out = []
    for title, keys in GROUPS:
        items = [{"key": k, "name": names.get(k, k), "about": ABOUT.get(k, ""), "auto": AUTOMATIC.get(k, ""),
                  "words": picked_by.get(k, []), "code": f"photo: {k}"} for k in keys if k in themes or k == "pattern"]
        if items:
            out.append({"name": title, "items": items})
    return out


def guide_from_packs(packs, words: list[dict]) -> list[dict]:
    """The same groups, from the turned-on art packs (app/packs.py): only pictures that are really there."""
    picked_by: dict[str, list[str]] = {}
    for w in words or []:
        if w.get("look"):
            picked_by.setdefault(w["look"], []).append(w["word"] + (" (with ⭐)" if w.get("picture_only") else ""))
    out = []
    for g in packs.groups:
        items = [{"key": k, "name": packs.title(k), "about": packs.scenes[k].get("about", ""), "auto": packs.scenes[k].get("auto", ""),
                  "words": picked_by.get(k, []), "code": f"photo: {k}", "pack": packs.scenes[k]["pack"]}
                 for k in g["scenes"] if k in packs.scenes]
        if items:
            out.append({"name": g["name"], "items": items})
    return out
