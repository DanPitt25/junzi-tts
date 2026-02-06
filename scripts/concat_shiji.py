import json

# Read all split chunk files
chunks = []
for i, slug in [(1, 'wu-di-ben-ji'), (2, 'xia-ben-ji'), (3, 'yin-ben-ji'), (7, 'xiang-yu-ben-ji')]:
    with open(f'/Users/danielpitt/Downloads/Junzi/translations/chunks/shiji_chunk_{i:02d}_{slug}_split.json', 'r') as f:
        data = json.load(f)
        chunks.append(data['chapter'])

# Create final structure
shiji = {
    "id": "shiji",
    "title": "史記",
    "titleEn": "Records of the Grand Historian",
    "source": "Chinese Text Project (ctext.org) - James Legge translation",
    "chapters": chunks
}

# Write output
with open('/Users/danielpitt/Downloads/Junzi/translations/shiji.json', 'w') as f:
    json.dump(shiji, f, ensure_ascii=False, indent=2)

print(f"Created shiji.json with {len(chunks)} chapters")
for ch in chunks:
    print(f"  Chapter {ch['number']}: {ch['title']} - {len(ch['passages'])} passages")
