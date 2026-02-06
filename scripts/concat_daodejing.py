import json
import glob

# Read all split chunk files
chunks = []
for f in sorted(glob.glob('/Users/danielpitt/Downloads/Junzi/translations/chunks/daodejing_chunk_*_split.json')):
    with open(f, 'r') as fp:
        data = json.load(fp)
        chunks.append(data['chapter'])

# Create final structure
daodejing = {
    "id": "daodejing",
    "title": "道德經",
    "titleEn": "Dao De Jing",
    "source": "Chinese Text Project (ctext.org) - James Legge translation",
    "chapters": chunks
}

# Write output
with open('/Users/danielpitt/Downloads/Junzi/translations/daodejing.json', 'w') as f:
    json.dump(daodejing, f, ensure_ascii=False, indent=2)

print(f"Created daodejing.json with {len(chunks)} chapters")
total = 0
for ch in chunks:
    count = len(ch['passages'])
    total += count
    print(f"  Chapter {ch['number']}: {count} passages")
print(f"\nTotal: {total} passages")
