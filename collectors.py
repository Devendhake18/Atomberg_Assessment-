from typing import List, Dict
from datetime import datetime
import requests
import time
import pandas as pd

from config import (
    GOOGLE_API_KEY, GOOGLE_CX, RESULTS_PER_KEYWORD, GOOGLE_MAX_RESULTS_TOTAL,
    GOOGLE_TIMEOUT_SECONDS, YOUTUBE_API_KEY, YOUTUBE_RESULTS_PER_KEYWORD, COMMENTS_PER_VIDEO
)

def search_google(keyword: str, quota_left: int) -> (List[Dict], int):
    # Disabled
    if True or not GOOGLE_API_KEY or not GOOGLE_CX or quota_left <= 0:
        return [], quota_left
    results: List[Dict] = []
    page_size = max(1, min(10, RESULTS_PER_KEYWORD))
    start = 1
    fetched = 0
    while fetched < RESULTS_PER_KEYWORD and quota_left > 0:
        num = min(page_size, RESULTS_PER_KEYWORD - fetched)
        params = {
            'key': GOOGLE_API_KEY,
            'cx': GOOGLE_CX,
            'q': keyword,
            'num': num,
            'start': start,
            'safe': 'off'
        }
        try:
            resp = requests.get('https://www.googleapis.com/customsearch/v1', params=params, timeout=GOOGLE_TIMEOUT_SECONDS)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            break
        items = data.get('items', [])
        if not items:
            break
        for idx, item in enumerate(items, start=0):
            title = item.get('title', '')
            snippet = item.get('snippet', '')
            link = item.get('link', '')
            results.append({
                'platform': 'Google',
                'title': title,
                'description': snippet,
                'url': link,
                'published_date': datetime.now(),
                'engagement_metrics': {'views': 0, 'likes': 0, 'comments': 0, 'engagement_score': 0},
                'keyword': keyword,
                'raw_text': f"{title} {snippet}".strip(),
                'rank': start + idx
            })
            quota_left -= 1
            if quota_left <= 0:
                break
        fetched += len(items)
        start += len(items)
        if len(items) < num or quota_left <= 0:
            break
        time.sleep(0.2)
    return results, quota_left

def search_youtube(keyword: str) -> List[Dict]:
    if not YOUTUBE_API_KEY:
        return []
    try:
        params = {
            'key': YOUTUBE_API_KEY,
            'part': 'snippet',
            'q': keyword,
            'type': 'video',
            'maxResults': min(50, YOUTUBE_RESULTS_PER_KEYWORD),
            'order': 'relevance'
        }
        resp = requests.get('https://www.googleapis.com/youtube/v3/search', params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        items = data.get('items', [])
    except Exception:
        return []
    rows: List[Dict] = []
    for item in items:
        snippet = item.get('snippet', {})
        video_id = (item.get('id') or {}).get('videoId')
        rows.append({
            'platform': 'YouTube',
            'title': snippet.get('title', ''),
            'description': snippet.get('description', ''),
            'channel_title': snippet.get('channelTitle', ''),
            'url': f"https://www.youtube.com/watch?v={video_id}",
            'published_date': datetime.now(),
            'engagement_metrics': _video_stats(video_id),
            'keyword': keyword,
            'raw_text': f"{snippet.get('title', '')} {snippet.get('description', '')}",
            'rank': None
        })
    return rows

def _video_stats(video_id: str) -> Dict:
    if not video_id or not YOUTUBE_API_KEY:
        return {'views': 0, 'likes': 0, 'comments': 0, 'engagement_score': 0}

def _video_comments(video_id: str) -> List[Dict]:
    rows: List[Dict] = []
    if not YOUTUBE_API_KEY or not video_id:
        return rows
    try:
        params = {
            'key': YOUTUBE_API_KEY,
            'part': 'snippet,replies',
            'videoId': video_id,
            'maxResults': min(100, COMMENTS_PER_VIDEO),
            'order': 'relevance',
            'textFormat': 'plainText'
        }
        resp = requests.get('https://www.googleapis.com/youtube/v3/commentThreads', params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get('items', []):
            snippet = ((item.get('snippet') or {}).get('topLevelComment') or {}).get('snippet') or {}
            text = snippet.get('textDisplay') or ''
            clikes = int(snippet.get('likeCount', 0) or 0)
            rows.append({'video_id': video_id, 'comment_text': text, 'comment_likes': clikes})
            # include replies if present
            replies = (item.get('replies') or {}).get('comments') or []
            for r in replies:
                rs = (r.get('snippet') or {})
                rt = rs.get('textDisplay') or ''
                rlikes = int(rs.get('likeCount', 0) or 0)
                if rt:
                    rows.append({'video_id': video_id, 'comment_text': rt, 'comment_likes': rlikes})
    except Exception:
        return rows
    return rows
    try:
        params = {'key': YOUTUBE_API_KEY, 'part': 'statistics', 'id': video_id}
        resp = requests.get('https://www.googleapis.com/youtube/v3/videos', params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        stats = (data.get('items') or [{}])[0].get('statistics', {})
        views = int(stats.get('viewCount', 0))
        likes = int(stats.get('likeCount', 0))
        comments = int(stats.get('commentCount', 0))
        engagement_score = (likes + comments * 3) / max(views / 1000, 1)
        return {'views': views, 'likes': likes, 'comments': comments, 'engagement_score': engagement_score}
    except Exception:
        return {'views': 0, 'likes': 0, 'comments': 0, 'engagement_score': 0}

def collect_for_keywords(keywords: List[str]) -> pd.DataFrame:
    rows: List[Dict] = []
    google_quota = 0
    for kw in keywords:
        y_rows = search_youtube(kw)
        rows.extend(y_rows)
    df = pd.DataFrame(rows)
    if df.empty or 'url' not in df.columns:
        return df
    # Fetch comments for each video
    comments: List[Dict] = []
    for vid in df['url'].str.replace('https://www.youtube.com/watch?v=', '', regex=False).dropna().unique():
        comments.extend(_video_comments(vid))
    comments_df = pd.DataFrame(comments)
    # Aggregate comments per video
    if not comments_df.empty:
        agg = comments_df.groupby('video_id')['comment_text'].apply(lambda s: '\n'.join(s.astype(str))).reset_index()
        agg.rename(columns={'video_id': 'videoId', 'comment_text': 'all_comments'}, inplace=True)
        df['videoId'] = df['url'].str.replace('https://www.youtube.com/watch?v=', '', regex=False)
        df = df.merge(agg, how='left', on='videoId')
        df['raw_text'] = (df['raw_text'].fillna('') + ' ' + df['all_comments'].fillna('')).str.strip()
    return df


