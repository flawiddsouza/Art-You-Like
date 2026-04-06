import sqlite3, os, sys

sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = os.path.join(os.path.dirname(__file__), "store.db")
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "static", "images")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT a.id, a.title, ar.name AS artist_name, ai.url
    FROM art_image ai
    JOIN art     a  ON ai.art_id    = a.id
    LEFT JOIN artist ar ON a.artist_id = ar.id
    ORDER BY a.id, ai.position
""").fetchall()

# also find art with no images at all
no_images = conn.execute("""
    SELECT a.id, a.title, ar.name AS artist_name
    FROM art a
    LEFT JOIN artist ar ON a.artist_id = ar.id
    WHERE a.id NOT IN (SELECT DISTINCT art_id FROM art_image)
    ORDER BY a.id
""").fetchall()

conn.close()

missing = {}  # art_id -> {title, artist_name, missing_files}
for row in rows:
    path = os.path.join(IMAGES_DIR, row["url"])
    if not os.path.isfile(path):
        entry = missing.setdefault(
            row["id"],
            {
                "title": row["title"],
                "artist_name": row["artist_name"],
                "missing_files": [],
            },
        )
        entry["missing_files"].append(row["url"])

total_missing_files = sum(len(v["missing_files"]) for v in missing.values())
print(
    f"=== Art with missing image files ({len(missing)} items, {total_missing_files} files) ==="
)
if missing:
    for art_id, info in missing.items():
        count = len(info["missing_files"])
        print(
            f"\n  [{art_id}] {info['title']}  (artist: {info['artist_name']})  [{count} missing]"
        )
        for f in info["missing_files"]:
            print(f"      - {f}")
else:
    print("  None")

print(f"\n=== Art with no images at all ({len(no_images)} items) ===")
if no_images:
    for row in no_images:
        print(f"  [{row['id']}] {row['title']}  (artist: {row['artist_name']})")
else:
    print("  None")
