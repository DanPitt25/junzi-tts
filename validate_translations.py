#!/usr/bin/env python3
"""
Validate scraped translations and identify chapters with bad/missing English.

Usage:
    python validate_translations.py              # Check all translations
    python validate_translations.py --fix        # Remove bad chapters so they can be re-scraped
    python validate_translations.py mengzi       # Check specific text
"""

import json
import sys
from pathlib import Path

TRANSLATIONS_DIR = Path("translations")

# Known bad patterns that indicate no real translation
BAD_PATTERNS = [
    "Enjoy this site? Please help",
    "Please help",
    "Site feedback",
    "ctext.org",
    "Log in",
    "Sign up",
    "Privacy policy",
    "Terms of service",
]

def has_chinese(text: str) -> bool:
    """Check if text contains Chinese characters."""
    for char in text:
        if '\u4e00' <= char <= '\u9fff' or '\u3400' <= char <= '\u4dbf':
            return True
    return False

def is_bad_translation(en: str) -> bool:
    """Check if English text is a bad/missing translation."""
    if not en or len(en.strip()) < 10:
        return True

    # Check for known bad patterns
    en_lower = en.lower()
    for pattern in BAD_PATTERNS:
        if pattern.lower() in en_lower:
            return True

    # If "translation" is mostly Chinese, it's bad
    chinese_count = sum(1 for c in en if '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf')
    if len(en) > 0 and chinese_count / len(en) > 0.3:
        return True

    return False

def validate_translation(text_id: str, fix: bool = False) -> dict:
    """Validate a single translation file."""
    path = TRANSLATIONS_DIR / f"{text_id}.json"
    if not path.exists():
        return {"error": f"File not found: {path}"}

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    results = {
        "text_id": text_id,
        "title": data.get("titleEn", ""),
        "total_chapters": len(data.get("chapters", [])),
        "total_passages": 0,
        "bad_chapters": [],
        "bad_passages": 0,
    }

    chapters_to_remove = []

    for ch_idx, chapter in enumerate(data.get("chapters", [])):
        chapter_bad_passages = 0
        passages = chapter.get("passages", [])
        results["total_passages"] += len(passages)

        for passage in passages:
            en = passage.get("en", "")
            if is_bad_translation(en):
                chapter_bad_passages += 1

        # If more than 50% of passages are bad, flag the chapter
        if len(passages) > 0 and chapter_bad_passages / len(passages) > 0.5:
            results["bad_chapters"].append({
                "number": chapter.get("number", "?"),
                "slug": chapter.get("slug", ""),
                "title": chapter.get("title", ""),
                "bad_passages": chapter_bad_passages,
                "total_passages": len(passages),
            })
            chapters_to_remove.append(ch_idx)
            results["bad_passages"] += chapter_bad_passages
        elif chapter_bad_passages > 0:
            # Some bad passages but not majority
            results["bad_passages"] += chapter_bad_passages

    # Fix mode: remove bad chapters so they can be re-scraped
    if fix and chapters_to_remove:
        # Remove in reverse order to preserve indices
        for idx in reversed(chapters_to_remove):
            del data["chapters"][idx]

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        results["fixed"] = True
        results["chapters_removed"] = len(chapters_to_remove)

    return results

def main():
    fix_mode = "--fix" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if args:
        text_ids = args
    else:
        # Check all translations
        text_ids = [p.stem for p in sorted(TRANSLATIONS_DIR.glob("*.json"))]

    print(f"Validating {len(text_ids)} translation(s)...")
    if fix_mode:
        print("FIX MODE: Bad chapters will be removed for re-scraping\n")
    else:
        print("Use --fix to remove bad chapters for re-scraping\n")

    total_bad_chapters = 0
    total_bad_passages = 0

    for text_id in text_ids:
        results = validate_translation(text_id, fix=fix_mode)

        if "error" in results:
            print(f"  {text_id}: {results['error']}")
            continue

        bad_count = len(results["bad_chapters"])
        total_bad_chapters += bad_count
        total_bad_passages += results["bad_passages"]

        if bad_count > 0:
            status = "FIXED" if results.get("fixed") else "BAD"
            print(f"  {results['title']} ({text_id}): {status}")
            print(f"    {bad_count} bad chapters, {results['bad_passages']} bad passages")
            for ch in results["bad_chapters"]:
                print(f"      - Chapter {ch['number']} ({ch['slug']}): {ch['bad_passages']}/{ch['total_passages']} bad")
        else:
            print(f"  {results['title']} ({text_id}): OK ({results['total_chapters']} chapters, {results['total_passages']} passages)")

    print(f"\nSummary: {total_bad_chapters} bad chapters, {total_bad_passages} bad passages total")

    if total_bad_chapters > 0 and not fix_mode:
        print("\nRun with --fix to remove bad chapters, then re-run scrape_ctp.py to fetch them again.")

if __name__ == "__main__":
    main()
