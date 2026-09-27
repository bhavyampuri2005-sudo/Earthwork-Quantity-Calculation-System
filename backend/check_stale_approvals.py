import csv
from database import get_db

conn = get_db()
cur = conn.cursor()
cur.execute("SELECT chainage FROM RowReview WHERE project_id=1 AND status='approved'")
approved_chainages = set(float(r[0]) for r in cur.fetchall())
print('total approved:', len(approved_chainages))

with open('review.csv') as f:
    rows = list(csv.DictReader(f))

stale = []
for r in rows:
    ch = float(r['chainage'])
    if ch in approved_chainages:
        gl = (r.get('ground_level') or '').strip()
        fl = (r.get('formation_level') or '').strip()
        if not gl or not fl:
            stale.append((ch, gl, fl))

print('approved but now fails current checks:', len(stale))
for ch, gl, fl in stale:
    print(ch, 'gl=', gl or 'BLANK', 'fl=', fl or 'BLANK')
