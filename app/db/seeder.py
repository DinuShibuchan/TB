"""
Database seeder — inserts 10 sample travel entries on first run.
Covers: Tokyo, Paris, Rome, Munnar (includes RAG test entry).
"""
from sqlalchemy.orm import Session
from app.services.retrieval_service import RetrievalService
from app.services.embedding_service import EmbeddingService

SEED_DATA = [
    # ── Tokyo ──────────────────────────────────────────────────────────────────
    {
        "name": "Tokyo",
        "description": (
            "Senso-ji is Tokyo's oldest Buddhist temple, founded in 628 AD and located in "
            "Asakusa. It draws over 30 million visitors per year. The Nakamise shopping street "
            "leading to the temple is lined with traditional snack and souvenir stalls."
        ),
        "category": "place",
    },
    {
        "name": "Tokyo",
        "description": (
            "Shibuya Crossing is the world's busiest pedestrian crossing, located in front of "
            "Shibuya Station. Surrounding the crossing are department stores, restaurants, and "
            "the famous Hachiko statue. Best visited at night for the full neon spectacle."
        ),
        "category": "place",
    },
    {
        "name": "Tokyo",
        "description": (
            "Ramen is a must-try in Tokyo. Ichiran Ramen in Shibuya serves tonkotsu ramen in "
            "private booths ideal for solo diners. Expect to pay 900–1200 yen per bowl. "
            "Sushi at Tsukiji Outer Market costs roughly 500–2000 yen per plate."
        ),
        "category": "food",
    },
    {
        "name": "Tokyo",
        "description": (
            "Budget accommodation in Tokyo: Khaosan Tokyo Origami hostel in Asakusa offers "
            "dorm beds from 2500 yen/night. Mid-range: Shinjuku Granbell Hotel from 8000 yen. "
            "Luxury: The Park Hyatt Tokyo in Shinjuku featured in Lost in Translation."
        ),
        "category": "stay",
    },

    # ── Paris ──────────────────────────────────────────────────────────────────
    {
        "name": "Paris",
        "description": (
            "The Eiffel Tower stands 330 m tall on the Champ de Mars. Entry to the top costs "
            "€29.40 for adults. The tower is free to view from Trocadéro gardens. "
            "The Louvre Museum houses the Mona Lisa and over 35,000 works — plan 3–4 hours."
        ),
        "category": "place",
    },
    {
        "name": "Paris",
        "description": (
            "Parisian food essentials: fresh croissants cost €1–€2 at any boulangerie. "
            "A classic croque-monsieur at a café runs €8–€12. "
            "Le Marais district has excellent falafel at L'As du Fallafel for €7. "
            "Dinner at a mid-range bistro is typically €25–€40 per person."
        ),
        "category": "food",
    },

    # ── Rome ───────────────────────────────────────────────────────────────────
    {
        "name": "Rome",
        "description": (
            "The Colosseum is Rome's iconic amphitheatre, built in 70 AD and holding 50,000 "
            "spectators. Entry costs €16. Nearby is the Roman Forum and Palatine Hill — "
            "a combined ticket covers all three. Book online to skip the 2-hour queues."
        ),
        "category": "place",
    },
    {
        "name": "Rome",
        "description": (
            "Roman cuisine highlights: Cacio e Pepe pasta costs €10–€14 at trattorias near "
            "Trastevere. Gelato at Fatamorgana near Campo de' Fiori is excellent — €2.50 per "
            "scoop. Avoid tourist traps around the Trevi Fountain — prices inflate 3x."
        ),
        "category": "food",
    },

    # ── Munnar ─────────────────────────────────────────────────────────────────
    {
        "name": "Munnar",
        "description": (
            "Secret Valley Waterfall is a hidden gem in Munnar, Kerala. Located 14 km off "
            "the main Munnar–Udumalpet road, it requires a 45-minute trek through cardamom "
            "and tea plantations. The waterfall drops 60 ft into a clear natural pool. "
            "Very few tourists visit it, making it ideal for a peaceful, scenic experience. "
            "Best visited between October and February when water flow is at its peak."
        ),
        "category": "place",
    },
    {
        "name": "Munnar",
        "description": (
            "Munnar is famous for its rolling tea plantations at altitudes of 1,500–2,700 m "
            "in the Western Ghats, Kerala. Top Tea Museum entry is ₹75. "
            "Local Kerala sadya (traditional meal on banana leaf) costs ₹150–₹250. "
            "Eravikulam National Park hosts the endangered Nilgiri Tahr mountain goat. "
            "Mattupetty Dam and Echo Point are popular half-day excursions from Munnar town."
        ),
        "category": "place",
    },
]


def seed_database(db: Session, embedding_service: EmbeddingService) -> int:
    """Insert seed data if the destinations table is empty. Returns count inserted."""
    from app.models.models import Destination
    existing = db.query(Destination).count()
    if existing > 0:
        print(f"[Seeder] Database already has {existing} entries — skipping seed.")
        return 0

    retrieval = RetrievalService(db, embedding_service)
    inserted = 0
    for entry in SEED_DATA:
        try:
            retrieval.add_destination(
                name=entry["name"],
                description=entry["description"],
                category=entry["category"],
            )
            inserted += 1
        except Exception as e:
            print(f"[Seeder] Failed to insert '{entry['name']}': {e}")

    print(f"[Seeder] Successfully seeded {inserted} travel entries into the database.")
    return inserted
