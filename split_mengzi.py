#!/usr/bin/env python3
"""
Split Mengzi chapters 7-8 into sentence-aligned passages.
Splits Chinese on sentence-ending punctuation (。！？) and aligns with English sentences.
Only splits when Chinese and English sentence counts match closely.
"""

import json
import re


def split_chinese_sentences(text):
    """Split Chinese text on sentence-ending punctuation."""
    sentences = []
    current = ""
    i = 0
    while i < len(text):
        char = text[i]
        current += char
        # Check if this is a sentence-ending punctuation
        if char in '。！？':
            # Check for closing quotes after punctuation
            while i + 1 < len(text) and text[i + 1] in '」』"\'':
                i += 1
                current += text[i]
            sentences.append(current.strip())
            current = ""
        i += 1

    # Don't forget any remaining text
    if current.strip():
        sentences.append(current.strip())

    return [s for s in sentences if s.strip()]


def split_english_sentences(text):
    """Split English text into sentences carefully."""
    if not text.strip():
        return []

    # Normalize whitespace
    text = ' '.join(text.split())

    # Common abbreviations that shouldn't trigger splits
    abbrevs = {
        'Mr.': '__MR__',
        'Mrs.': '__MRS__',
        'Dr.': '__DR__',
        'etc.': '__ETC__',
        'i.e.': '__IE__',
        'e.g.': '__EG__',
        'vs.': '__VS__',
    }

    protected = text
    for abbrev, placeholder in abbrevs.items():
        protected = protected.replace(abbrev, placeholder)

    # Split on sentence-ending punctuation followed by space and capital letter or quote
    # This regex captures the punctuation with the preceding text
    parts = re.split(r'(?<=[.!?]["\']?)\s+(?=[A-Z"\'\(])', protected)

    # Restore abbreviations
    result = []
    for part in parts:
        for abbrev, placeholder in abbrevs.items():
            part = part.replace(placeholder, abbrev)
        if part.strip():
            result.append(part.strip())

    return result


def align_passages(zh_sentences, en_sentences, chapter_num, start_ref):
    """
    Align Chinese and English sentences into passages.
    Only splits when sentence counts match exactly.
    """
    passages = []
    zh_count = len(zh_sentences)
    en_count = len(en_sentences)

    if zh_count == 0 and en_count == 0:
        return passages, start_ref

    if zh_count == 0:
        passages.append({
            "ref": f"{chapter_num}:{start_ref}",
            "zh": "",
            "en": " ".join(en_sentences)
        })
        return passages, start_ref + 1

    if en_count == 0:
        passages.append({
            "ref": f"{chapter_num}:{start_ref}",
            "zh": "".join(zh_sentences),
            "en": ""
        })
        return passages, start_ref + 1

    # Only split if counts match exactly
    if zh_count == en_count:
        for i in range(zh_count):
            passages.append({
                "ref": f"{chapter_num}:{start_ref + i}",
                "zh": zh_sentences[i],
                "en": en_sentences[i]
            })
        return passages, start_ref + zh_count

    # If counts are close (differ by 1), try to align
    if abs(zh_count - en_count) == 1:
        # If one more Chinese sentence, combine the last two Chinese
        if zh_count == en_count + 1:
            for i in range(en_count - 1):
                passages.append({
                    "ref": f"{chapter_num}:{start_ref + i}",
                    "zh": zh_sentences[i],
                    "en": en_sentences[i]
                })
            # Combine last two Chinese with last English
            passages.append({
                "ref": f"{chapter_num}:{start_ref + en_count - 1}",
                "zh": zh_sentences[-2] + zh_sentences[-1],
                "en": en_sentences[-1]
            })
            return passages, start_ref + en_count

        # If one more English sentence, combine the last two English
        if en_count == zh_count + 1:
            for i in range(zh_count - 1):
                passages.append({
                    "ref": f"{chapter_num}:{start_ref + i}",
                    "zh": zh_sentences[i],
                    "en": en_sentences[i]
                })
            # Combine last two English with last Chinese
            passages.append({
                "ref": f"{chapter_num}:{start_ref + zh_count - 1}",
                "zh": zh_sentences[-1],
                "en": en_sentences[-2] + " " + en_sentences[-1]
            })
            return passages, start_ref + zh_count

    # Counts differ too much - keep as single passage
    passages.append({
        "ref": f"{chapter_num}:{start_ref}",
        "zh": "".join(zh_sentences),
        "en": " ".join(en_sentences)
    })
    return passages, start_ref + 1


def process_chapter(input_file, output_file, chapter_num):
    """Process a chapter file and create sentence-aligned version."""

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_passages = []
    ref_counter = 1

    for orig_passage in data['chapter']['passages']:
        zh_text = orig_passage['zh']
        en_text = orig_passage['en']

        # Split into sentences
        zh_sentences = split_chinese_sentences(zh_text)
        en_sentences = split_english_sentences(en_text)

        # Align and create new passages
        new_passages, ref_counter = align_passages(
            zh_sentences, en_sentences, chapter_num, ref_counter
        )

        all_passages.extend(new_passages)

    # Create output structure
    output_data = {
        "id": data['id'],
        "title": data['title'],
        "titleEn": data['titleEn'],
        "source": data['source'],
        "chapter": {
            "number": str(chapter_num),
            "title": data['chapter']['title'],
            "slug": data['chapter']['slug'],
            "passages": all_passages
        }
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"Created {output_file} with {len(all_passages)} passages")

    # Print some stats
    empty_en = sum(1 for p in all_passages if not p['en'].strip())
    empty_zh = sum(1 for p in all_passages if not p['zh'].strip())
    if empty_en:
        print(f"  Warning: {empty_en} passages with empty English")
    if empty_zh:
        print(f"  Warning: {empty_zh} passages with empty Chinese")

    return len(all_passages)


if __name__ == '__main__':
    import os

    base_dir = os.path.dirname(os.path.abspath(__file__))
    chunks_dir = os.path.join(base_dir, 'translations', 'chunks')

    # Process chapter 7
    process_chapter(
        os.path.join(chunks_dir, 'mengzi_chunk_07_li-lou-i.json'),
        os.path.join(chunks_dir, 'mengzi_chunk_07_li-lou-i_split.json'),
        7
    )

    # Process chapter 8
    process_chapter(
        os.path.join(chunks_dir, 'mengzi_chunk_08_li-lou-ii.json'),
        os.path.join(chunks_dir, 'mengzi_chunk_08_li-lou-ii_split.json'),
        8
    )
