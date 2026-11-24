"""Makes shop.db: a made-up D2C store for the Signal agent to work on. Everyone and
everything in it is invented. Same data every time (fixed seed).

    python3 make_data.py

It copies the real system's limits: website events for 14 days, orders for 60 days, and
only what the customer wrote in chat.
"""

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB = Path(__file__).with_name("shop.db")
NOW = datetime(2026, 11, 24, 12, 0)
PEOPLE = 600

TABLES = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE profile (field TEXT PRIMARY KEY, value TEXT, source TEXT);
CREATE TABLE products (product TEXT, size TEXT, kind TEXT, price INTEGER);
CREATE TABLE people (person_id TEXT PRIMARY KEY, channel TEXT, city TEXT, first_seen TEXT);
CREATE TABLE orders (order_id INTEGER PRIMARY KEY, person_id TEXT, at TEXT, total INTEGER,
                     payment TEXT, status TEXT, discount TEXT);
CREATE TABLE order_items (order_id INTEGER, product TEXT, size TEXT, quantity INTEGER, price INTEGER);
CREATE TABLE website_events (event_id INTEGER PRIMARY KEY, person_id TEXT, at TEXT, name TEXT,
                             product TEXT, size TEXT, price INTEGER, cart_total INTEGER, search_text TEXT);
CREATE TABLE messages (message_id INTEGER PRIMARY KEY, person_id TEXT, at TEXT, text TEXT);
"""

PROFILE = [
    ("business", "Demo Farms (made up): cold-pressed oils, flours, dals, ghee", "operator"),
    ("free_delivery_above", "₹1,599", "website"),
    ("cod", "Yes, up to ₹5,000", "website"),
    ("areas_served", "All of India; not abroad", "website"),
    ("delivery_days", "3 to 6 days", "website"),
    ("returns", "7 days, unopened packs", "website"),
    ("bulk_orders", "Yes, from 20 packs", "operator"),
    ("largest_pack", "5 L oil, 10 kg flour", "catalogue"),
    ("reorder_days", "30", "operator"),
    ("not_offered", "No delivery abroad, no loose or unpacked products", "operator"),
]

PRODUCTS = [
    ("Mustard Oil", "1 L", "oil", 320), ("Mustard Oil", "3 L", "oil", 930),
    ("Mustard Oil", "5 L", "oil", 1499), ("Groundnut Oil", "1 L", "oil", 380),
    ("Groundnut Oil", "5 L", "oil", 1790), ("Sesame Oil", "1 L", "oil", 520),
    ("Wheat Flour", "5 kg", "flour", 360), ("Wheat Flour", "10 kg", "flour", 690),
    ("Khapli Flour", "5 kg", "flour", 520), ("Arhar Dal", "1 kg", "dal", 210),
    ("Moong Dal", "1 kg", "dal", 190), ("Jaggery", "1 kg", "other", 140),
    ("Ghee", "500 ml", "ghee", 690), ("Ghee", "1 L", "ghee", 1290), ("Honey", "500 g", "other", 340),
]
BIG = [p for p in PRODUCTS if p[1] == "5 L"]
SMALL = [p for p in PRODUCTS if p[1] != "5 L"]
CITIES = ["Delhi", "Mumbai", "Pune", "Jaipur", "Lucknow", "Indore", "Bengaluru", "Hyderabad", "Jhansi", "Kolkata"]

SEGMENTS = {
    "browser": 33, "regular": 16, "chatter": 13, "big_pack": 9, "abandoner": 8,
    "near_free_delivery": 6, "noise": 5, "bulk": 4, "complaint": 3, "lapsed": 3,
}

CHAT = {
    "big_pack": [
        "Need {p} 5 L again, please send to {c}", "Is the {p} 5 litre in stock?",
        "bhaiya {p} 5 L ka tin chahiye, {c} me kab tak aayega?",
        "Last time I took 5 L {p}. Want 2 this month", "What is the price of 5 L {p} with delivery to {c}?",
    ],
    "chatter": [
        "Is COD available?", "cod milega kya {c} me?", "How many days for delivery to {c}?",
        "What is the price of {p}?", "Is your {p} really cold pressed?", "Any offer going on for {p}?",
        "Do you have a smaller pack of {p}?", "ok I will think and tell you", "price bahut zyada hai",
        "Can you give some discount on {p}?", "Which is better for cooking, {p} or sunflower?",
        "I want to order {p}, how do I pay?", "Please send me the link to order {p}",
        "kal tak {c} me mil jayega? ghar me function hai",
    ],
    "bulk": [
        "We are a restaurant in {c}, need 40 packs of {p} every month. Rate please?",
        "Looking for bulk rate of {p}, around 60 packs for Diwali gifting",
        "Do you supply to shops? I need 25 tins of {p}", "Please share GST invoice details for a corporate order",
    ],
    "noise": [
        "Any job vacancy in your company?", "Sir I am looking for an internship in marketing",
        "We do SEO and can rank your website on page 1. Interested?",
        "We make plastic bottles and caps, can I share our catalogue?", "Do you deliver to Dubai?", "hi", "Good morning",
        "Can I get {p} loose, without packing?",
    ],
    "complaint": [
        "Where is my order? It has been 8 days", "My {p} came leaking, I want a refund",
        "Tracking link is not working", "Wrong item sent, I ordered {p}",
    ],
    "lapsed": ["Earlier I used to order {p}. Is the price still the same?", "Do you still make {p}?"],
}


def main() -> None:
    rnd = random.Random(7)
    DB.unlink(missing_ok=True)
    db = sqlite3.connect(DB)
    db.executescript(TABLES)
    db.executemany("INSERT INTO meta VALUES (?,?)", [("now", NOW.isoformat(" ")), ("made_up", "yes")])
    db.executemany("INSERT INTO profile VALUES (?,?,?)", PROFILE)
    db.executemany("INSERT INTO products VALUES (?,?,?,?)", PRODUCTS)

    def ago(days: float) -> datetime:
        return NOW - timedelta(days=days)

    def event(who, at, name, product=None, cart=None, search=None):
        p = product or (None, None, None, None)
        db.execute(
            "INSERT INTO website_events (person_id,at,name,product,size,price,cart_total,search_text) VALUES (?,?,?,?,?,?,?,?)",
            (who, at.isoformat(" ", "seconds"), name, p[0], p[1], p[3], cart, search),
        )

    def order(who, at, items):
        total = sum(p[3] * n for p, n in items)
        discount = rnd.choices(["none", "code", "automatic", "staff"], [70, 15, 10, 5])[0]
        row = db.execute(
            "INSERT INTO orders (person_id,at,total,payment,status,discount) VALUES (?,?,?,?,?,?)",
            (who, at.isoformat(" ", "seconds"), total, rnd.choices(["cod", "prepaid"], [41, 59])[0],
             rnd.choices(["delivered", "cancelled", "returned"], [93, 4, 3])[0], discount),
        )
        db.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)",
                       [(row.lastrowid, p[0], p[1], n, p[3]) for p, n in items])

    def say(who, segment, city, times, within):
        for text in rnd.sample(CHAT[segment], min(times, len(CHAT[segment]))):
            pool = BIG if segment == "big_pack" else PRODUCTS
            at = ago(rnd.uniform(0, within))
            db.execute("INSERT INTO messages (person_id,at,text) VALUES (?,?,?)",
                       (who, at.isoformat(" ", "seconds"), text.format(p=rnd.choice(pool)[0].lower(), c=city)))

    def visit(who, day, product, upto, cart=None):
        """One visit, going as far as `upto`: look, cart or checkout."""
        at = ago(day)
        event(who, at, "page_viewed")
        if rnd.random() < 0.2:
            event(who, at + timedelta(minutes=1), "search_submitted",
                  search=f"{product[0].lower()}{' 5 litre' if product[1] == '5 L' and rnd.random() < .5 else ''}")
        event(who, at + timedelta(minutes=2), "product_viewed", product)
        if upto in ("cart", "checkout"):
            total = cart or product[3]
            event(who, at + timedelta(minutes=4), "product_added_to_cart", product)
            event(who, at + timedelta(minutes=5), "cart_viewed", cart=total)
        if upto == "checkout":
            event(who, at + timedelta(minutes=7), "checkout_started", cart=total)

    names = rnd.choices(list(SEGMENTS), list(SEGMENTS.values()), k=PEOPLE)
    for i, seg in enumerate(names, 1):
        who, city = f"P{i}", rnd.choice(CITIES)
        chat_only = seg in ("noise", "bulk", "chatter")
        channel = rnd.choices(["whatsapp", "instagram", "sheet"], [70, 20, 10])[0] if chat_only else (
            rnd.choices(["website", "whatsapp", "sheet"], [75, 17, 8])[0])
        seen = rnd.uniform(40, 60) if seg in ("big_pack", "regular", "lapsed", "complaint") else rnd.uniform(1, 25)
        db.execute("INSERT INTO people VALUES (?,?,?,?)", (who, channel, city, ago(seen).isoformat(" ", "seconds")))

        if seg == "browser":
            day = rnd.uniform(0, 14)
            for _ in range(rnd.choices([1, 2, 3], [60, 30, 10])[0]):
                visit(who, day, rnd.choice(PRODUCTS), "cart" if rnd.random() < .08 else "look")
        elif seg == "regular":
            for k in range(rnd.choice([1, 1, 2])):
                order(who, ago(rnd.uniform(5, 28) + 26 * k), [(rnd.choice(SMALL), rnd.choice([1, 1, 2])) for _ in range(rnd.randint(1, 4))])
            if rnd.random() < .5:
                visit(who, rnd.uniform(0, 14), rnd.choice(SMALL), rnd.choice(["look", "cart"]))
        elif seg == "big_pack":
            oil, gap = rnd.choice(BIG), rnd.gauss(30, 4)
            last = rnd.uniform(4, gap)
            for k in range(2):
                if last + gap * k < 60:
                    order(who, ago(last + gap * k), [(oil, rnd.choice([1, 1, 2]))] + ([(rnd.choice(SMALL), 1)] if rnd.random() < .6 else []))
            if rnd.random() < .7:
                for day in rnd.sample(range(0, 13), rnd.choice([2, 2, 3])):
                    visit(who, day + rnd.random(), oil, rnd.choice(["look", "look", "cart"]), oil[3] + rnd.choice([0, 360, 690]))
            if rnd.random() < .45:
                say(who, seg, city, rnd.choice([1, 2]), 30)
        elif seg == "abandoner":
            p = rnd.choice(PRODUCTS)
            visit(who, rnd.uniform(2, 13), p, "checkout", p[3] + rnd.randint(0, 1800))
            if rnd.random() < .4:
                visit(who, rnd.uniform(0, 2), p, rnd.choice(["look", "checkout"]), p[3] + rnd.randint(0, 1800))
        elif seg == "near_free_delivery":
            for day in rnd.sample(range(0, 13), rnd.choice([1, 2])):
                visit(who, day + rnd.random(), rnd.choice(SMALL), "cart", rnd.randint(1250, 1590))
        elif seg == "complaint":
            order(who, ago(rnd.uniform(6, 15)), [(rnd.choice(PRODUCTS), 1)])
            say(who, seg, city, rnd.choice([1, 2]), 5)
        elif seg == "lapsed":
            order(who, ago(rnd.uniform(48, 59)), [(rnd.choice(PRODUCTS), 1)])
            if rnd.random() < .6:
                visit(who, rnd.uniform(0, 7), rnd.choice(PRODUCTS), "look")
            if rnd.random() < .5:
                say(who, seg, city, 1, 10)
        else:  # chatter, bulk, noise
            say(who, seg, city, rnd.choice([1, 2, 2, 3]), 30)
    db.commit()
    for table in ("people", "orders", "order_items", "website_events", "messages"):
        print(f"{table:15} {db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]}")
    print(f"Made {DB.name}. Everything in it is made up.")


if __name__ == "__main__":
    main()
