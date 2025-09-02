import os
import glob
import sys
import ast
import numpy as np
import pandas as pd
from datetime import datetime

from metrics import enrich_dataframe, compute_metrics
from visuals import AtombergAIAgent
from collectors import collect_for_keywords
from config import REPORTS_DIR
from nlp_utils import extract_brand_mentions


def _find_latest_csv() -> str | None:
    extracted = sorted(glob.glob(os.path.join('reports', 'sov_extracted_*.csv')))
    processed = sorted(glob.glob(os.path.join('reports', 'sov_processed_*.csv')))
    candidates = (extracted or []) + (processed or [])
    return candidates[-1] if candidates else None


def _maybe_parse(val):
    if isinstance(val, str):
        s = val.strip()
        if (s.startswith('{') and s.endswith('}')) or (s.startswith('[') and s.endswith(']')):
            try:
                return ast.literal_eval(s)
            except Exception:
                return val
    return val


def load_latest_csv(path: str | None = None) -> pd.DataFrame:
    if path and os.path.exists(path):
        csv_path = path
    else:
        csv_path = _find_latest_csv()
        if not csv_path:
            raise FileNotFoundError('No CSV found in reports/. Use --extract to fetch and save one.')
    df = pd.read_csv(csv_path)
    for col in ['brand_mentions', 'engagement_metrics']:
        if col in df.columns:
            df[col] = df[col].apply(_maybe_parse)
    if 'raw_text' not in df.columns and 'title' in df.columns and 'description' in df.columns:
        df['raw_text'] = (df['title'].fillna('') + ' ' + df['description'].fillna('')).str.strip()
    return df


def main():
    args = sys.argv[1:]
    csv_arg = args[0] if args and not args[0].startswith('--') else None
    do_extract = ('--extract' in args)

    if do_extract or (not csv_arg and not _find_latest_csv()):
        print('Extracting YouTube data...')
        keywords = [
            'smart fan', 'ceiling fan', 'atomberg fan', 'energy efficient fan',
            'BLDC fan', 'smart ceiling fan', 'atomberg smart fan', 'premium fan',
            'atomberg ceiling fan', 'energy saving fan', 'smart home fan', 'IoT fan',
            'atomberg BLDC', 'atomberg energy efficient', 'smart ceiling fan review'
        ]
        rows = collect_for_keywords(keywords)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs(REPORTS_DIR, exist_ok=True)
        out_path = os.path.join(REPORTS_DIR, f'sov_extracted_{ts}.csv')
        rows.to_csv(out_path, index=False)
        print(f'Saved: {out_path}')
        csv_arg = out_path

    df = load_latest_csv(csv_arg)
    df = enrich_dataframe(df)
    metrics = compute_metrics(df)

    print('=' * 70)
    print('OFFLINE METRICS (from CSV, no API calls)')
    print('=' * 70)
    print(f"Rows: {len(df)}")
    print(f"Presence Rate: {metrics.get('presence_rate', 0):.2f}%")
    print(f"Basic SoV: {metrics.get('basic_sov', 0):.2f}%")
    print(f"Positive Share: {metrics.get('sentiment_sov', 0):.2f}%")
    print(f"Comments SoV: {metrics.get('comments_sov', 0):.2f}%")
    print(f"Composite Index: {metrics.get('composite_sov', 0):.2f}%")
    totals = metrics.get('totals', {})
    if totals:
        print(f"Eng Total: {totals.get('eng_total', 0):.2f}")
        print(f"Eng Atomberg: {totals.get('eng_atomberg', 0):.2f}")
        print(f"Comment Mentions Total: {totals.get('comment_mentions_total', 0)}")
        print(f"Comment Mentions Atomberg: {totals.get('comment_mentions_atomberg', 0)}")
    print('=' * 70)

    agent = AtombergAIAgent()
    embedding_analysis = {
        'cluster_analysis': {},
        'tfidf_2d': np.zeros((0, 2)),
        'cluster_labels': np.array([])
    }
    df_plot = df.copy()
    if 'brand_mentions' not in df_plot.columns:
        df_plot['brand_mentions'] = df_plot['raw_text'].apply(extract_brand_mentions)
    if 'keyword' not in df_plot.columns:
        df_plot['keyword'] = 'all'
    agent._create_ai_visualizations(df_plot, metrics, {}, embedding_analysis)


if __name__ == '__main__':
    main()


