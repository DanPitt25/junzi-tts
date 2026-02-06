import json
import glob

# Read all split chunk files
chunks = []
for f in sorted(glob.glob('/Users/danielpitt/Downloads/Junzi/translations/chunks/zhuangzi_chunk_*_split.json')):
    with open(f, 'r') as fp:
        data = json.load(fp)
        chunks.append(data['chapter'])

# Create final structure
zhuangzi = {
    "id": "zhuangzi",
    "title": "莊子",
    "titleEn": "Zhuangzi",
    "source": "Chinese Text Project (ctext.org) - James Legge translation",
    "chapters": chunks
}

# Write output
with open('/Users/danielpitt/Downloads/Junzi/translations/zhuangzi.json', 'w') as f:
    json.dump(zhuangzi, f, ensure_ascii=False, indent=2)

print(f"Created zhuangzi.json with {len(chunks)} chapters")
total = 0
for ch in chunks:
    count = len(ch['passages'])
    total += count
    print(f"  Chapter {ch['number']}: {ch['title']} - {count} passages")
print(f"\nTotal: {total} passages")
