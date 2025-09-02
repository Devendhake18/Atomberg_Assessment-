# Atomberg YouTube Share of Voice (SoV)

Clean, reproducible pipeline for YouTube-only SoV with comment-aware sentiment and a composite index.

## Overview

- Extract YouTube videos and comments for target keywords
- Save extracted data to CSV (reproducible snapshots)
- Reload CSV and compute Presence %, Basic SoV, Comments SoV, Positive Share, Composite Index
- Generate a publication-ready dashboard

## Project structure

```
Atomberg/
├── main.py            # Single entrypoint (extract → CSV → process → plots)
├── collectors.py      # YouTube search/videos/comments
├── metrics.py         # Metrics and formulas
├── nlp_utils.py       # Preprocessing, sentiment, brand mentions
├── visuals.py         # Plotting and dashboard
├── config.py          # Config (limits, weights, paths)
├── reports/           # Saved CSVs (extracted snapshots)
└── plots/             # Generated dashboards
```

## Quick start

Install dependencies:
```bash
pip install -r requirements.txt
```

Set your YouTube API key in `config.env`:
```
YOUTUBE_API_KEY=your_youtube_api_key
```

Run extract + process (creates CSV, then computes and plots):
```bash
python main.py --extract
```

Process latest saved CSV (no API calls):
```bash
python main.py
```

Process a specific CSV:
```bash
python main.py reports/sov_extracted_YYYYMMDD_HHMMSS.csv
```

## Metrics (formulas)

- Presence Rate = videos_with_brand / total_videos × 100
- Basic SoV = atomberg_content_mentions / total_content_mentions × 100
- Comments SoV = atomberg_comment_mentions / total_brand_comment_mentions × 100
- Engagement value = views/1000 + 2×likes + 3×comments + commentLikes (fallback to comment count/likes if stats missing)
- Composite Index = weighted sum of Basic SoV, Positive Share, Visibility, Engagement (weights in `config.py`)

## Dashboard

- Saved to `plots/ai_analysis_*.png`
- Shows Presence vs Positive, Sentiment Distribution, Engagement vs Sentiment, Composite by Brand, Keyword Performance, Comments Sentiment

## Report

See `REPORT.md` for a two-page PDF-ready report (tech stack and recommendations) including a dashboard image.

## Notes

- Google data is removed; pipeline is YouTube-only.
- Everything runs off CSVs to avoid reusing API quota.
