from typing import Dict
import pandas as pd
import numpy as np

from config import (
    BRAND_NAME, COMPETITOR_BRANDS,
    SOV_WEIGHT_BASIC, SOV_WEIGHT_ENGAGEMENT, SOV_WEIGHT_SENTIMENT, SOV_WEIGHT_VISIBILITY
)
from nlp_utils import sentiment_scores, extract_brand_mentions, preprocess_text

def enrich_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    # Build processed_text consistently
    df['processed_text'] = df['raw_text'].fillna('').apply(preprocess_text)
    # engagement_norm percentile
    if (df['engagement_metrics'].apply(lambda x: isinstance(x, dict) and x.get('engagement_score', 0) > 0)).any():
        df['engagement_score'] = df['engagement_metrics'].apply(lambda x: x.get('engagement_score', 0) if isinstance(x, dict) else 0)
        eng_pos = df['engagement_score'].where(df['engagement_score'] > 0)
        df['engagement_norm'] = eng_pos.rank(pct=True).fillna(0.0)
    else:
        df['engagement_score'] = 0.0
        df['engagement_norm'] = 0.0
    # visibility weights
    def _vis(row):
        if row.get('platform') == 'YouTube':
            metrics = row.get('engagement_metrics') or {}
            try:
                views = int(metrics.get('views', 0))
            except Exception:
                views = 0
            return min(5.0, np.log10(max(views, 1) + 1))
        return 1.0
    df['visibility_weight'] = df.apply(_vis, axis=1)
    # Ensure sentiment fields exist for downstream metrics
    if 'brand_adjusted_sentiment' not in df.columns:
        df['brand_adjusted_sentiment'] = df['processed_text'].apply(lambda t: sentiment_scores(t)['brand_adjusted'])
    if 'sentiment_overall' not in df.columns:
        def _cls(s: float) -> str:
            if s > 0.1:
                return 'positive'
            if s < -0.1:
                return 'negative'
            return 'neutral'
        df['sentiment_overall'] = df['brand_adjusted_sentiment'].apply(_cls)
    # comments text helper
    if 'all_comments' not in df.columns:
        df['all_comments'] = ''
    return df

def compute_metrics(df: pd.DataFrame) -> Dict:
    if df.empty:
        return {
            'basic_sov': 0, 'engagement_sov': 0, 'sentiment_sov': 0, 'quality_sov': 0,
            'visibility_weighted_sov': 0, 'composite_sov': 0, 'platform_sov': {},
            'total_mentions': 0, 'atomberg_mentions': 0, 'competitor_mentions': {}, 'brand_benchmark': {}
        }
    df = df.copy()
    # Ensure brand_mentions exists; if missing or empty, extract from raw_text
    if 'brand_mentions' not in df.columns:
        df['brand_mentions'] = df['raw_text'].apply(extract_brand_mentions)
    else:
        def _ensure_list(v, text):
            if isinstance(v, list) and v:
                return v
            return extract_brand_mentions(text)
        df['brand_mentions'] = [
            _ensure_list(v, t) for v, t in zip(df['brand_mentions'], df['raw_text'])
        ]
    # Respect existing atomberg_mention if present; otherwise create case-insensitive
    if 'atomberg_mention' not in df.columns:
        brand_lc = str(BRAND_NAME).lower()
        def _ci_flag(xs):
            try:
                return any(str(v).lower() == brand_lc for v in (xs or []))
            except Exception:
                return False
        df['atomberg_mention'] = df['brand_mentions'].apply(_ci_flag)
    total_mentions = len(df)
    atomberg_data = df[df['atomberg_mention'] == True]
    atomberg_mentions = len(atomberg_data)
    # Content mention SoV (titles+descriptions)
    basic_sov = atomberg_mentions / total_mentions * 100 if total_mentions > 0 else 0
    
    # Comments-based mentions SoV
    def _count_brand_in_comments(text: str, brand: str) -> int:
        if not isinstance(text, str) or not text:
            return 0
        return text.lower().count(brand.lower())
    total_comment_mentions = sum(_count_brand_in_comments(t, b) for t in df.get('all_comments', '').astype(str) for b in [BRAND_NAME] + COMPETITOR_BRANDS)
    atomberg_comment_mentions = sum(df.get('all_comments', '').astype(str).apply(lambda t: _count_brand_in_comments(t, BRAND_NAME)))
    comments_sov = (atomberg_comment_mentions / total_comment_mentions * 100) if total_comment_mentions > 0 else 0
    
    df_eng = df[df['engagement_norm'] > 0]
    # Engagement share using actual video stats
    # comment count per video from fetched comments (fallback)
    if 'all_comments' in df.columns:
        df['comment_count'] = df['all_comments'].fillna('').apply(lambda t: sum(1 for _ in str(t).split('\n') if _.strip()))
    else:
        df['comment_count'] = 0
    # estimate comment likes if present
    def _sum_comment_likes(text: str) -> int:
        return 0
    if 'all_comments' in df.columns:
        df['comment_likes'] = 0
    def _eng_value(metrics: dict, cc: int, cl: int) -> float:
        if not isinstance(metrics, dict):
            base = 0.0
        else:
            views = float(metrics.get('views', 0) or 0)
            likes = float(metrics.get('likes', 0) or 0)
            comments = float(metrics.get('comments', 0) or 0)
            base = (views / 1000.0) + (likes * 2.0) + (comments * 3.0) + (cl * 1.0)
        # Fallback if API stats are zero
        if base <= 0 and (cc > 0 or cl > 0):
            return float(cc + cl)
        return base
    df['eng_value'] = [
        _eng_value(m, c, l) for m, c, l in zip(df['engagement_metrics'], df['comment_count'], df.get('comment_likes', pd.Series([0]*len(df))))
    ]
    # Count towards Atomberg if content, comments, or channel title mentions brand variants
    brand_regex = '|'.join([BRAND_NAME, BRAND_NAME.replace(' ', ''), BRAND_NAME.replace(' ', '-'), BRAND_NAME.replace(' ', '_'), 'atom berg'])
    atomberg_any = df[(df['atomberg_mention']) |
                      (df.get('raw_text', '').astype(str).str.contains(brand_regex, case=False, na=False)) |
                      (df.get('title', '').astype(str).str.contains(brand_regex, case=False, na=False)) |
                      (df.get('description', '').astype(str).str.contains(brand_regex, case=False, na=False)) |
                      (df.get('all_comments', '').astype(str).str.contains(brand_regex, case=False, na=False)) |
                      (df.get('channel_title', '').astype(str).str.contains(brand_regex, case=False, na=False)) |
                      (df.get('keyword', '').astype(str).str.contains('atomberg', case=False, na=False))]
    # Ensure flagged Atomberg videos contribute minimally even if stats/comments unavailable
    df.loc[atomberg_any.index, 'eng_value'] = df.loc[atomberg_any.index, 'eng_value'].replace(0, 1.0)
    total_eng_value = df['eng_value'].sum()
    atomberg_eng_value = atomberg_any['eng_value'].sum()
    engagement_sov = atomberg_eng_value / total_eng_value * 100 if total_eng_value > 0 else 0
    
    # Positive share from comments mentioning Atomberg
    def _pos_from_comments(text: str) -> int:
        if not isinstance(text, str) or not text:
            return 0
        positives = 0
        total = 0
        for line in text.split('\n'):
            if BRAND_NAME.lower() in line.lower():
                sc = sentiment_scores(line)['brand_adjusted']
                positives += 1 if sc > 0.1 else 0
                total += 1
        if total == 0:
            return None
        return int(positives / total * 100)
    pos_rates = []
    for t in df.get('all_comments', '').astype(str):
        r = _pos_from_comments(t)
        if r is not None:
            pos_rates.append(r)
    sentiment_sov = float(np.mean(pos_rates)) if pos_rates else 0.0
    
    # Quality SoV using eng_value weighted by sentiment score from content (fallback)
    atomberg_quality_score = (df_eng[df_eng['atomberg_mention'] == True]['engagement_norm'] * df_eng[df_eng['atomberg_mention'] == True]['brand_adjusted_sentiment'])
    total_quality_score = df_eng['engagement_norm'] * df_eng['brand_adjusted_sentiment']
    quality_sov = (atomberg_quality_score.sum() / total_quality_score.sum() * 100) if total_quality_score.sum() > 0 else 0
    platform_sov = {}
    for platform in df['platform'].unique():
        if platform == 'Instagram':
            continue
        pdata = df[df['platform'] == platform]
        platform_sov[platform] = (pdata[pdata['atomberg_mention'] == True].shape[0] / len(pdata) * 100) if len(pdata) > 0 else 0
    competitor_mentions = {}
    for brand in COMPETITOR_BRANDS:
        bdata = df[df['brand_mentions'].apply(lambda x: brand in x)]
        if len(bdata) > 0:
            competitor_mentions[brand] = {
                'mentions': len(bdata),
                'sov': len(bdata) / total_mentions * 100,
                'avg_sentiment': bdata['brand_adjusted_sentiment'].mean(),
                'avg_engagement': bdata['engagement_norm'].mean(),
                'positive_rate': (bdata['brand_adjusted_sentiment'] > 0.1).mean() * 100,
                'eng_value_sum': float(bdata['eng_value'].sum()),
                'videos': int(len(bdata))
            }
    atomberg_visibility = atomberg_data['visibility_weight'].sum()
    total_visibility = df['visibility_weight'].sum()
    visibility_weighted_sov = atomberg_visibility / total_visibility * 100 if total_visibility > 0 else 0
    w_sum = max(1e-6, SOV_WEIGHT_BASIC + SOV_WEIGHT_ENGAGEMENT + SOV_WEIGHT_SENTIMENT + SOV_WEIGHT_VISIBILITY)
    wb = SOV_WEIGHT_BASIC / w_sum
    we = SOV_WEIGHT_ENGAGEMENT / w_sum
    ws = SOV_WEIGHT_SENTIMENT / w_sum
    wv = SOV_WEIGHT_VISIBILITY / w_sum
    composite_sov = wb * basic_sov + we * engagement_sov + ws * sentiment_sov + wv * visibility_weighted_sov
    brands_all = [BRAND_NAME] + COMPETITOR_BRANDS
    tv = max(1e-9, df['visibility_weight'].sum())
    te = max(1e-9, df['engagement_norm'].sum())
    benchmark = {}
    for b in brands_all:
        rows = df[df['brand_mentions'].apply(lambda x: b in x)]
        if len(rows) == 0:
            continue
        bb = len(rows) / total_mentions * 100
        be = rows['engagement_norm'].sum() / te * 100 if te > 0 else 0
        bv = rows['visibility_weight'].sum() / tv * 100 if tv > 0 else 0
        bp = (rows['brand_adjusted_sentiment'] > 0.1).mean() * 100
        comp = wb * bb + we * be + ws * bp + wv * bv
        benchmark[b] = {
            'basic_sov': bb,
            'engagement_sov': be,
            'sentiment_positive_rate': bp,
            'visibility_sov': bv,
            'composite_sov': comp,
            'eng_value_sum': float(rows['eng_value'].sum()),
            'videos': int(len(rows))
        }
    return {
        'basic_sov': basic_sov,
        'engagement_sov': engagement_sov,
        'presence_rate': (len(atomberg_any) / len(df) * 100.0) if len(df) > 0 else 0.0,
        'sentiment_sov': sentiment_sov,
        'quality_sov': quality_sov,
        'visibility_weighted_sov': visibility_weighted_sov,
        'composite_sov': composite_sov,
        'comments_sov': comments_sov,
        'platform_sov': platform_sov,
        'total_mentions': total_mentions,
        'atomberg_mentions': atomberg_mentions,
        'competitor_mentions': competitor_mentions,
        'brand_benchmark': benchmark,
        'totals': {
            'eng_total': float(total_eng_value),
            'eng_atomberg': float(atomberg_eng_value),
            'comment_mentions_total': int(total_comment_mentions),
            'comment_mentions_atomberg': int(atomberg_comment_mentions)
        }
    }


