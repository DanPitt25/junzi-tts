# Claude Code Instructions for Junzi

## Git Commits

Do NOT add Co-Authored-By lines to commit messages. Just write the commit message.

## IMPORTANT: Do NOT run the server yourself!

The user runs the server manually. Do not use `python3 server.py` or try to start/restart the server. Just make changes to the code and let the user test.

## Project Overview

Classical Chinese Reader app with:
- Python backend (`server.py`) using aiohttp
- React frontend (vanilla JS with createElement, no JSX) in `index.html`
- Pre-scraped translations in `translations/*.json` (from CTP with Legge translations)

## API Endpoints

- `/api/catalog` - List available texts
- `/api/chapters?id=<bookId>` - Get chapters for a book
- `/api/text?id=<bookId>&chapter=<slug>` - Get text content
- `/api/tts?text=<text>&voice=<voice>` - Text-to-speech

## Translation Files

Located in `translations/`:
- `analects.json` - 20 chapters, 503 passages
- `mengzi.json` - Mencius (partial)
- `zhongyong.json` - Doctrine of the Mean
- `daodejing.json` - Dao De Jing, 81 chapters

Each has format:
```json
{
  "id": "analects",
  "title": "論語",
  "titleEn": "Analects",
  "source": "Chinese Text Project (ctext.org) - James Legge translation",
  "chapters": [
    {
      "number": "1",
      "title": "Xue Er",
      "slug": "xue-er",
      "passages": [
        {"ref": "1:1", "zh": "子曰：...", "en": "The Master said..."}
      ]
    }
  ]
}
```

## Scraping

- `scrape_ctp.py` - Scrapes ctext.org for Chinese + Legge English (be careful of rate limiting)
- `scrape_muller.py` - Scrapes acmuller.net for Muller translations (not currently used)

## Manual Sentence-Level Splitting Process

**IMPORTANT: This process CANNOT be done automatically. It requires manual review and alignment.**

### Why Manual Splitting is Required
The scraped translations from CTP have paragraph-level alignment, but the app needs sentence-level alignment for proper reading. Automated splitting fails because:
1. Chinese punctuation marks don't always correspond to English sentence boundaries
2. Translators often combine or reorder sentences for readability
3. Some translations are incomplete or contain scraping artifacts ("Enjoy this site? Please help")

### Process Overview
1. **Split into chunks**: Break large files into chapter-based chunks for manageable processing
2. **Manual splitting**: For each chunk, split Chinese text at sentence boundaries (。！？；) and align English translations
3. **Fix bad translations**: Replace scraping artifacts with "[Translation not available]"
4. **Concatenate**: Merge split chunks back into the final file

### Step-by-Step Instructions

#### Step 1: Create Chunk Files
For a file like `translations/shiji.json`:
```bash
# Create chunks directory
mkdir -p translations/chunks

# Split by chapter - each chunk gets one chapter
# Chunk filename format: {text}_chunk_{##}_{slug}.json
```

Each chunk file structure:
```json
{
  "id": "shiji",
  "title": "史記",
  "titleEn": "Records of the Grand Historian",
  "source": "Chinese Text Project (ctext.org) - James Legge translation",
  "chapter": {
    "number": "1",
    "title": "Wu Di Ben Ji",
    "slug": "wu-di-ben-ji",
    "passages": [...]
  }
}
```

#### Step 2: Manual Sentence Splitting
For each passage in a chunk:

1. **Read the Chinese text** and identify sentence boundaries at: `。` `！` `？` `；`
2. **Read the English translation** and identify corresponding sentence breaks
3. **Create aligned passage pairs** - each Chinese sentence gets its matching English sentence(s)
4. **Update refs** using format `chapter:passage.sentence` (e.g., "1:1.1", "1:1.2", etc.)

Example transformation:
```json
// BEFORE (paragraph-level)
{
  "ref": "1:1",
  "zh": "黃帝者，少典之子，姓公孫，名曰軒轅。生而神靈，弱而能言，幼而徇齊，長而敦敏，成而聰明。",
  "en": "Huangdi (Yellow emperor) was the son of Shaodian. His surname was Gongsun, and his prename Xuanyuan. Born with spiritual powers, he could talk when quite young, as a boy he was sharp-witted, as a youth simple and earnest, and when grown up intelligent."
}

// AFTER (sentence-level)
{
  "ref": "1:1",
  "zh": "黃帝者，少典之子，姓公孫，名曰軒轅。",
  "en": "Huangdi (Yellow emperor) was the son of Shaodian. His surname was Gongsun, and his prename Xuanyuan."
},
{
  "ref": "1:2",
  "zh": "生而神靈，弱而能言，幼而徇齊，長而敦敏，成而聰明。",
  "en": "Born with spiritual powers, he could talk when quite young, as a boy he was sharp-witted, as a youth simple and earnest, and when grown up intelligent."
}
```

#### Step 3: Fix Bad Translations
Replace scraping artifacts like "Enjoy this site? Please help" with:
```json
"en": "[Translation not available]"
```

#### Step 4: Save Split Chunk
Save the manually split chunk as `{original_chunk_name}_split.json`

#### Step 5: Concatenate Chunks
After all chunks are split, merge them back into the main file:
```json
{
  "id": "shiji",
  "title": "史記",
  "titleEn": "Records of the Grand Historian",
  "source": "Chinese Text Project (ctext.org) - James Legge translation",
  "chapters": [
    // chapter from chunk 1
    // chapter from chunk 2
    // etc.
  ]
}
```

### Files Completed
- `daxue.json` - Great Learning (already sentence-level)
- `zhongyong.json` - Doctrine of the Mean (already sentence-level)
- `xiaojing.json` - Classic of Filial Piety (already sentence-level)
- `shangshu.json` - Book of Documents (manually split)
- `mozi.json` - Mozi (manually split)
- `daodejing.json` - Dao De Jing (81 verses, no splitting needed)

### Files In Progress
- `shiji.json` - Records of the Grand Historian (16 chapters, chunked)
  - Chunk 01 (Wu Di Ben Ji): COMPLETED - 29→245 passages
  - Chunks 02-16: In progress

### Files Pending
- `zhuangzi.json` - 151 passages
- `analects.json` - 503 passages
- `mengzi.json` - 690 passages
- `yijing.json` - 1012 passages
- `book-of-poetry.json` - 1016 passages
- `liji.json` - 1729 passages

### Prompt for Parallel Claude Instances
To have another Claude instance work on a text, use:
```
Split and align [text name] according to CLAUDE.md
```

The Claude instance will:
1. Read CLAUDE.md to understand the process
2. Split the file into chapter chunks (if large)
3. Manually split each chunk at sentence boundaries
4. Align English translations with Chinese sentences
5. Fix any bad translations
6. Concatenate chunks back together
