"""Lord's Day pictures: every Sunday gets a picture, a verse and a short note on what the picture
shows and why, from one of five series, taking turns one Sunday from each.

The turns start fresh on the first Sunday of January 2027 (Lord's Day #1). Sundays before that
count backward, so the weeks just before land on the end of each series. A Sunday that is a
holiday (Resurrection Sunday, Christmas on a Sunday, Mother's Day set to Special...) shows the
holiday and doesn't count: the series pause that week and pick up the next open Sunday.

Signs and objects only (Second Commandment; 1689 Confession ch. 22): an empty cross, never a
crucifix; no picture of the Father, the Son or the Spirit.
"""
from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

from . import lordsday_art as art

START = date(2027, 1, 3)  # first Sunday of January 2027

LORDS_DAY_ABOUT = [
    "A sunrise behind an open church door. Christ rose on the first day of the week, so his people gather on that day to rest and worship.",
    "The light shines out of the open Bible, not onto it. Scripture alone is God's own Word and the final rule for what we believe and how we live.",
    "A shield doesn't fight; it takes the blows. Faith alone receives Christ's righteousness and quenches the enemy's accusations.",
    "A gift with a ribbon: received, never earned. Salvation is God's free grace to people who could never deserve it.",
    "An empty cross in the light: the work is finished. Christ alone stands between God and sinners; nothing needs to be added.",
    "Bach and other heirs of the Reformation signed their work S.D.G., to God alone be the glory. All we have comes from him, and all praise goes back to him.",
    "Ripples spreading in still water. Believers are baptized by immersion, a picture of being buried and raised with Christ.",
    "Plain bread and a simple cup on a table, not an altar. The Supper remembers Christ's once-for-all sacrifice and feeds believers by faith.",
    "The open Bible sits on the pulpit because preaching serves the text. God uses the faithful preaching of his Word to save and grow his people.",
    "An oil lamp lights only the next few steps. God's Word gives enough light for each step of obedience.",
    "A stone fortress on a rock, as in Luther's hymn on Psalm 46. God himself is the refuge his people run to when the world shakes.",
    "A shepherd's crook and sheep in a green pasture. The Lord provides for, leads and protects his own.",
    "An anchor holds a ship steady in a storm. Hope in God's promise, fastened in Christ, keeps the soul from drifting.",
    "Grapes grow only on branches joined to the vine. Life and fruit come from abiding in Christ.",
    "A lit town on a hill can't be hidden at night. Christ's people are meant to shine where they are, so others glorify God.",
    "A rock doesn't move with the weather. God is the unchanging safe place for those who trust him.",
    "A spring running through dry land. Christ gives a life that keeps welling up and satisfies the deepest thirst.",
    "Loaves in a basket, like the feeding of the thousands. Christ himself is the bread that gives eternal life.",
    "Only those inside the ark came safely through the flood. Salvation is found in Christ, who carries his people through judgment.",
    "One open door with light inside. Christ is the only way into God's family and safe pasture.",
    "A helmet, shield and sword: God's provision, not our own strength. Believers stand firm in what God supplies.",
    "A sword laid over the Bible, because they are the same thing. The Spirit's weapon against temptation and lies is the Word of God.",
    "The rainbow God set in the cloud after the flood. He keeps his covenant promises.",
    "A sealed scroll is a promise that cannot be broken. In the covenant of grace, revealed in God's promises and fulfilled in Christ, God binds himself to be our God.",
    "Sun, moon and stars speak without words. Creation shows God's glory every day and every night.",
    "A sparrow on a branch. Sparrows were cheap and common, yet none falls without the Father; his care reaches the smallest things.",
    "A ripe wheat field waiting for workers. Many still need to hear, so we pray for laborers and go ourselves.",
    "A globe and a compass. The gospel is for every nation, and Christ sends his church to make disciples, baptizing and teaching them.",
    "A tiny seed and a great tree where birds nest. God's kingdom starts small and grows beyond what we expect.",
    "One pearl worth more than everything the merchant owned. Christ and his kingdom are worth more than all we have.",
    "A salt jar and a candle. Christians are called to be distinct and useful: to preserve what is good and show the way.",
    "Rain beats on a house built on the rock, and it stands. A life built on hearing and doing Christ's words holds firm.",
    "A narrow arch and a hard path that leads to the light. There is one way to life, through Christ.",
    "Music notes rising from an open hymnal. God's people teach and encourage each other as they sing his Word together.",
    "Incense rising from a golden bowl, as in the tabernacle. Our prayers rise to God through Christ and are welcome.",
    "Lights making their way to a lit church. God calls his people to meet together, not to go it alone.",
    "A shepherd's crook and a basin with a towel. Christ gives his church two offices: elders to shepherd and teach, deacons to serve.",
    "Names written in a book. God chose his people in Christ before the world began, by grace and not for anything in them.",
    "A clean white robe, given not earned. Christ's righteousness covers the believer completely before God.",
    "Broken chains in the light. For those in Christ the sentence is gone; nothing is left to condemn them for.",
    "A home with lit windows and a heart above it. God brings believers into his family as sons and daughters.",
    "Silver in a crucible over the fire. God uses trials to burn away what is worthless and make his people more like Christ.",
    "A running track and a laurel wreath. The Christian life is a long race, run with endurance, looking to Jesus.",
    "A crown on a cushion, waiting. God promises the crown of life to those who endure and love him.",
    "A trumpet sounding through the clouds. Christ will return visibly, and the dead in Christ will rise.",
    "The tree of life beside the river of the new creation. What was lost in Eden is restored forever.",
    "Two stone tablets with the Ten Commandments. God's moral law shows his holiness, our sin, and how to love God and neighbor.",
    "Still waters and resting sheep. The weekly rest points to the eternal rest God has prepared for his people.",
    "A signpost turning the traveler back toward home. Jesus calls sinners to turn from sin and trust him.",
    "The Second London Baptist Confession of 1689, with a quill. It sums up what Scripture teaches; we hold the faith once delivered, not something new.",
    "In Bunyan's Pilgrim's Progress, Christian's burden falls off at the cross and rolls into the tomb. Christ carried our sins so we don't have to.",
    "Sunrise over the fields. God's mercies never run out; every morning brings fresh mercy.",
]
COMMANDMENT_ABOUT = [
    "A toppled idol lies broken. Nothing and no one may take God's place in our hearts.",
    "Carving tools laid down beside an uncarved stone. God is to be worshiped as he commands, not through images we make.",
    "The word Hallowed on a scroll. God's name is to be treated as holy in our words and in our lives.",
    "Seven days with the first one lit. Since Christ rose, the first day of the week is the Christian Sabbath, a day for worship and rest.",
    "Deep roots under a family home. Honoring parents is the first commandment with a promise.",
    "A sword beaten into a plowshare. Life is God's gift; we are to protect it, not take it.",
    "Two rings joined. Marriage is a lifelong covenant of one man and one woman, kept pure in body and heart.",
    "Level, honest scales. We are to deal fairly and work honestly, so we have something to share.",
    "A plumb line hanging straight beside a true wall. Our words should be true and fair to our neighbor.",
    "Bread enough for today. Contentment with what God gives guards us from wanting what is our neighbor's.",
]
TRINITY_ABOUT = [
    "One light and one word. There is only one living and true God.",
    "The old Shield of the Trinity uses words, not pictures: the Father, the Son and the Spirit each is God, yet the Father is not the Son, the Son is not the Spirit, and the Spirit is not the Father. One God in three persons.",
    "Light streaming down from above. The Father is the source of every good gift, who planned our salvation.",
    "Alpha and Omega, the first and last letters of the Greek alphabet. The eternal Son, who became man for us, is the beginning and the end.",
    "Wind can't be seen, only what it does to the grass. The Spirit gives new birth and life, unseen but real.",
    "Holy, three times, as the seraphim cry in Isaiah 6. God is utterly holy; the church has long sung this threefold cry to the Trinity.",
    "The closing blessing of 2 Corinthians names all three persons: the grace of the Son, the love of the Father and the fellowship of the Spirit.",
]
CONFESSION_ABOUT = [
    "An open Bible. In the Confession's own words, the Holy Scripture is the only sufficient, certain and infallible rule of all saving knowledge, faith and obedience.",
    "The Shield of the Trinity, in words only. The one true God exists in three persons, Father, Son and Holy Spirit, equal in power and glory.",
    "A sealed scroll. From eternity God decreed all that comes to pass, by his wise and holy will, without being the author of sin.",
    "The earth, sun and stars. God made the world from nothing, in six days, and all very good.",
    "Footsteps along a path. God upholds, directs and governs every creature and event, down to each step.",
    "Fruit with a bite and thorny ground. By Adam's sin all mankind fell into sin and death, and creation bears the curse.",
    "Stars to count, as God told Abraham. The covenant of grace, first promised in Genesis 3:15, is fully revealed in Christ.",
    "A ladder from earth to heaven, as in Jacob's dream and John 1:51. Christ is the only mediator between God and man: prophet, priest and king.",
    "A signpost at a crossroads. Fallen man freely chooses sin; only God's grace frees the will to choose good.",
    "A sheep at the gate of the fold. Those God chose he calls by his Word and Spirit, and they come willingly.",
    "A scale with a cross on one side. God declares sinners righteous, not for anything in them, but by counting Christ's obedience to them, received by faith.",
    "A key to the house. No longer slaves but sons and daughters, with full access to the Father and an inheritance.",
    "A young plant growing and bearing fruit. Those made new keep growing in holiness by the Spirit, through the Word.",
    "Abraham's tent under the stars. Faith trusts God's promise and obeys, even without seeing where it leads.",
    "A road that turns back toward the light. Repentance is turning from sin to God with real grief over sin, and it is God's gift.",
    "A basket of fruit. Good works don't earn salvation; they are the fruit and evidence of true faith.",
    "A path that reaches the summit. Those God has saved he will keep to the end; they can never finally fall away.",
    "A sealed letter. Believers can know they have eternal life, though that assurance may grow and may be shaken.",
    "The two tablets. God's moral law still binds everyone as a rule of life, though believers are not under it as a covenant of works.",
    "A messenger's sandals on the mountain. The promise of salvation in Christ is known only through the gospel, so it must be preached.",
    "A broken yoke. Christ frees believers from the guilt of sin and the curse of the law, and God alone is Lord of the conscience.",
    "A church on the Lord's Day. God is to be worshiped only as he has commanded, and the first day of the week is the Christian Sabbath.",
    "A Yes, signed and sealed. Lawful oaths and vows are solemn acts of worship, made with care and kept.",
    "A government building. God has ordained civil rulers for the public good; Christians honor them and pray for them.",
    "Two rings. Marriage is between one man and one woman, for mutual help, for children and for purity.",
    "A church built on the rock. Christ is the head of his church, which gathers in local congregations under elders and deacons.",
    "One table with many places. Believers are united to Christ and to one another, sharing gifts and burdens.",
    "Water, bread and the cup. Christ gave his church two ordinances, and only two, to keep until he returns.",
    "Rippling water. Baptism is for those who profess repentance and faith, and immersion is the right way to administer it.",
    "Bread and cup. The Supper proclaims Christ's death until he comes; he is present spiritually to believers who receive it by faith.",
    "An empty tomb at sunrise. At death believers go to be with Christ, and their bodies will be raised on the last day.",
    "Open books, as in Revelation 20. God has appointed a day when Christ will judge the world in righteousness.",
]
BIBLE_ABOUT = [
    "The earth, sun and stars. Genesis tells of creation, the fall, and God's promise of a Redeemer through Abraham's family.",
    "The Red Sea parted. God rescued his people from slavery, a picture of redemption.",
    "Fire on the altar. God is holy, and sinners come near him only through the sacrifice he provides, fulfilled in Christ.",
    "Tents under the pillar of cloud. God led and kept Israel through the wilderness, grumbling and all.",
    "The two tablets. Moses renewed the covenant and called Israel to love the Lord with all their heart.",
    "Jericho's fallen walls and the ram's horn. God gave his people the land; the victory was his.",
    "Gideon's jar and torch. When Israel strayed, God raised up deliverers, showing the need for a true King.",
    "A sheaf of barley. From the harvest fields God brought Ruth into his people and into King David's line.",
    "David's sling and five stones. God chooses the humble and fights for his people.",
    "David's crown. God promised David a throne forever, fulfilled in Christ, the Son of David.",
    "Solomon's temple. God dwelt among his people, but the kingdom split when its kings turned away.",
    "A chariot wheel of fire. Elijah was taken up, and God's prophets stayed faithful while the kingdoms fell.",
    "A family scroll. The genealogies trace God's faithfulness through the generations to David.",
    "The ark of the covenant. The temple and its worship, and God's promise to hear when his people humble themselves.",
    "The scroll of the Law. Back from exile, God's people rebuilt and returned to his Word.",
    "The wall, the trowel and the sword. Jerusalem's walls were rebuilt by people who worked and kept watch.",
    "The golden scepter. God is never named in the book, yet he saved his people through Esther.",
    "The whirlwind. God answered Job out of the storm, and Job learned to trust God's wisdom in suffering.",
    "The harp. The Psalms are Israel's songbook of praise, lament and trust, still sung by the church.",
    "The honeycomb. Wisdom is sweet, and it begins with the fear of the Lord.",
    "The hourglass. Life under the sun is brief, so fear God and keep his commandments.",
    "The lily. The love of husband and wife is God's good gift.",
    "Tongs holding a coal from the altar. Isaiah was cleansed and sent, and he foretold the suffering Servant who bore our sins.",
    "The potter's wheel. God is sovereign over nations as a potter over clay, and he promised a new covenant.",
    "A tear and the dawn. Grief over Jerusalem's fall, with hope in God's faithful mercies.",
    "Wheels within wheels. Ezekiel's vision of God's glory, and his promise of a new heart.",
    "The lion. God shut the lions' mouths, and he rules over the kingdoms of the world.",
    "Silver and barley. Hosea bought back his unfaithful wife, as God redeems his wayward people.",
    "Rain on the land. The day of the Lord, and God's promise to pour out his Spirit.",
    "A basket of summer fruit. God calls for justice and warns that judgment is ripe.",
    "The eagle's rock. Proud Edom fell, but the kingdom will be the Lord's.",
    "The great fish. God's mercy reaches even Nineveh; salvation belongs to the Lord.",
    "Bethlehem under the star. Micah foretold the ruler born in Bethlehem and called us to walk humbly with God.",
    "The stronghold. The Lord is a refuge for those who trust him and the judge of the wicked.",
    "The watchtower. Habakkuk waited for God's answer and learned that the righteous live by faith.",
    "Music over a home. After judgment, God will rejoice over his people with singing.",
    "The foundation stone. God called the returned exiles to rebuild his house and promised greater glory.",
    "The lampstand between olive trees. God's work is done not by might, but by his Spirit.",
    "The rising sun. The last prophet promised the sun of righteousness and a messenger to prepare the way.",
    "A crown and a star. Jesus is the promised King, the Son of David, who fulfills the Scriptures.",
    "A lamp on its stand. Mark shows Jesus the servant, who came to give his life as a ransom for many.",
    "The manger. Luke's careful account of the Savior born for all people.",
    "Light in the darkness. The eternal Word became flesh, so that believing we might have life in his name.",
    "Paul's ship. The church, empowered by the Spirit, carried the gospel to the ends of the earth.",
    "A Roman arch around the open Word. The gospel is the power of God for salvation; the righteous live by faith.",
    "A heart with 13 on it, for 1 Corinthians 13. Love is the greatest gift, and it should shape the life of the church.",
    "A jar of clay with light. God's treasure is carried in weak vessels, so the power is plainly his.",
    "A broken yoke. We are justified by faith in Christ, not by works of the law, and set free.",
    "The cornerstone. Jew and Gentile are built together on Christ into one household of God.",
    "The prize cup. Paul pressed on with joy toward the goal of knowing Christ.",
    "A crown with stars. Christ is supreme over creation and the church; in him all things hold together.",
    "Light above the clouds. Believers wait for the Lord's return and will be with him forever.",
    "A workbench and hammer. While waiting for Christ, keep working and don't grow weary in doing good.",
    "A pillar. The church holds up the truth, so it must be ordered and led faithfully.",
    "A laurel around the open Word. Paul finished his race and charged Timothy to preach the Word.",
    "A church on the island of Crete. Sound doctrine leads to godly living and good works.",
    "A letter and broken shackles. The gospel makes a runaway slave a beloved brother.",
    "The curtain torn in two. Christ, our great high priest, opened the way into God's presence once for all.",
    "A mirror. Don't just look into the Word and walk away; do what it says.",
    "Living stones. Suffering believers are built into a spiritual house with Christ as cornerstone.",
    "The morning star. Hold fast to Scripture, a lamp in a dark place until Christ returns.",
    "A heart in the light. God is light and God is love, and those who know him walk in both.",
    "Footsteps and a letter. Walk in truth and love, and don't welcome false teaching.",
    "An open, lit door. Welcome those who serve the truth.",
    "A shield with a star. Contend for the faith, kept by the God who is able to keep you from stumbling.",
    "A city with gates of pearl and a river. Christ wins, and God will make all things new.",
]
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def _series() -> list[dict]:
    s = [
        {"key": "lordsday", "name": "The Lord's Day", "items": [
            {"title": t, "verse": v, "ref": r, "about": a, "draw": art.DRAW[t]}
            for (t, _sym, v, r), a in zip(art.SUNDAYS, LORDS_DAY_ABOUT)]},
        {"key": "commandments", "name": "The Ten Commandments", "items": [
            {"title": f"{ROMAN[i]}. {t}", "verse": v, "ref": r, "about": a, "draw": f}
            for i, ((t, _sym, v, r, f), a) in enumerate(zip(art.COMMANDMENTS, COMMANDMENT_ABOUT))]},
        {"key": "trinity", "name": "The Holy Trinity", "items": [
            {"title": t, "verse": v, "ref": r, "about": a, "draw": f}
            for (t, _sym, v, r, f), a in zip(art.TRINITY, TRINITY_ABOUT)]},
        {"key": "confession", "name": "The 1689 Confession", "items": [
            {"title": f"Chapter {i + 1}: {t}", "verse": v, "ref": r, "about": a,
             "draw": (lambda n=i + 1, k=key: art.confession_scene(n, k))}
            for i, ((t, key, v, r), a) in enumerate(zip(art.CONFESSION, CONFESSION_ABOUT))]},
        {"key": "bible", "name": "Through the Bible", "items": [
            {"title": name, "verse": v, "ref": f"{name} {ref}", "about": a, "draw": (lambda n=i: art.book_scene(n))}
            for i, ((name, v, ref, _sym), a) in enumerate(zip(art.BOOKS, BIBLE_ABOUT))]},
    ]
    for x in s:
        assert all(it["about"] for it in x["items"])
    return s


SERIES = _series()
assert [len(x["items"]) for x in SERIES] == [52, 10, 7, 32, 66]


@lru_cache(maxsize=256)
def _picture(series: int, i: int) -> str:
    return SERIES[series]["items"][i]["draw"]()


def sunday_number(d: date, paused=None, start: date = START) -> int:
    """How many Sundays from `start` to d (negative before it). Sundays that
    `paused(day)` says belong to a holiday don't count, so the series simply wait a week."""
    step = timedelta(days=7)
    count = lambda a, b: sum(1 for i in range((b - a).days // 7) if not (paused and paused(a + i * step)))
    return count(start, d) if d >= start else -count(d, start)


def pick(counts: list[int], start: date, d: date, paused=None) -> tuple[int, int]:
    """(series, picture) for Sunday d: the series take turns, one Sunday each, each going through its pictures in order.
    The art packs (app/packs.py) use this with the faith pack's series.json; for_sunday uses it with SERIES below."""
    k = sunday_number(d, paused, start)
    s = k % len(counts)
    return s, (k // len(counts)) % counts[s]


def for_sunday(d: date, paused=None) -> dict:
    """The picture, verse and note for Sunday d (from the drawing code; the frame gets them from the faith pack)."""
    s, i = pick([len(x["items"]) for x in SERIES], START, d, paused)
    series = SERIES[s]
    it = series["items"][i]
    return {"series": series["name"], "series_key": series["key"], "n": i + 1, "count": len(series["items"]),
            "title": it["title"], "verse": f"“{it['verse']}{'' if it['verse'][-1:] in '!?' else '.'}” {it['ref']}",
            "about": it["about"], "svg": _picture(s, i)}
