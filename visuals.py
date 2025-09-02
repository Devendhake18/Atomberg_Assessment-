import os
from typing import Dict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from config import PLOTS_DIR


class AtombergAIAgent:
    def __init__(self):
        self.colors = {
            'atomberg': '#FF6B6B',
            'competitors': '#4ECDC4',
            'positive': '#2ECC71',
            'negative': '#E74C3C',
            'neutral': '#95A5A6',
            'cluster1': '#FF6B6B',
            'cluster2': '#4ECDC4',
        }
        os.makedirs(PLOTS_DIR, exist_ok=True)

    def _create_ai_visualizations(self, df: pd.DataFrame, sov_metrics: Dict, insights: Dict, embedding_analysis: Dict):
        print("  Creating visualizations...")
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")

        fig = plt.figure(figsize=(18, 12))

        ax1 = plt.subplot(2, 3, 1)
        self._plot_presence_vs_positive(ax1, sov_metrics)

        ax2 = plt.subplot(2, 3, 2)
        self._plot_sentiment_distribution(ax2, df)

        ax3 = plt.subplot(2, 3, 3)
        self._plot_engagement_vs_sentiment(ax3, df)

        ax4 = plt.subplot(2, 3, 4)
        self._plot_competitive_analysis(ax4, sov_metrics)

        ax5 = plt.subplot(2, 3, 5)
        self._plot_keyword_performance(ax5, df)

        ax6 = plt.subplot(2, 3, 6)
        self._plot_comments_sentiment(ax6, df)

        plt.tight_layout()
        out_path = os.path.join(PLOTS_DIR, f'ai_analysis_{timestamp}.png')
        plt.savefig(out_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  Visualizations saved to {out_path}")

    def _plot_presence_vs_positive(self, ax, sov_metrics: Dict):
        labels = ['Presence %', 'Positive %']
        vals = [sov_metrics.get('presence_rate', 0), sov_metrics.get('sentiment_sov', 0)]
        bars = ax.bar(labels, vals, color=[self.colors['atomberg'], self.colors['positive']])
        ax.set_title('Brand Presence vs Positive Share', fontweight='bold')
        ax.set_ylabel('%')
        for bar, value in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1, f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')

    def _plot_sentiment_distribution(self, ax, df: pd.DataFrame):
        sentiment_counts = df.get('sentiment_overall', pd.Series([], dtype=str)).value_counts()
        if sentiment_counts.empty:
            ax.text(0.5, 0.5, 'No sentiment data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Sentiment Distribution', fontweight='bold')
            return
        colors = [self.colors['positive'], self.colors['negative'], self.colors['neutral']]
        ax.pie(sentiment_counts.values, labels=sentiment_counts.index, autopct='%1.1f%%', colors=colors)
        ax.set_title('Sentiment Distribution', fontweight='bold')

    def _plot_engagement_vs_sentiment(self, ax, df: pd.DataFrame):
        if df.empty or 'brand_adjusted_sentiment' not in df.columns or 'engagement_norm' not in df.columns:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Engagement vs Sentiment', fontweight='bold')
            return
        ax.scatter(df['brand_adjusted_sentiment'], df['engagement_norm'], alpha=0.6, color=self.colors['atomberg'])
        ax.set_title('Engagement vs Sentiment', fontweight='bold')
        ax.set_xlabel('Sentiment Score')
        ax.set_ylabel('Engagement Score (norm)')

    def _plot_competitive_analysis(self, ax, sov_metrics: Dict):
        benchmark = sov_metrics.get('brand_benchmark', {})
        if not benchmark:
            ax.text(0.5, 0.5, 'No brand data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Composite by Brand', fontweight='bold')
            return
        brands = list(benchmark.keys())
        composites = [benchmark[b]['composite_sov'] for b in brands]
        bars = ax.bar(brands, composites, color=[self.colors['atomberg'] if b == 'Atomberg' else self.colors['competitors'] for b in brands])
        ax.set_title('Composite SoV by Brand', fontweight='bold')
        ax.set_ylabel('Composite SoV (%)')
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

    def _plot_keyword_performance(self, ax, df: pd.DataFrame):
        if df.empty or 'keyword' not in df.columns:
            ax.text(0.5, 0.5, 'No keyword data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Keyword Performance', fontweight='bold')
            return
        keyword_analysis = {}
        for kw in df['keyword'].unique():
            kdf = df[df['keyword'] == kw]
            total = len(kdf)
            atomberg_mentions = sum(1 for mentions in kdf.get('brand_mentions', []) if isinstance(mentions, list) and 'Atomberg' in mentions)
            avg_eng = kdf.get('engagement_norm', pd.Series([0]*len(kdf))).mean()
            keyword_analysis[kw] = {
                'atomberg_sov': (atomberg_mentions / total * 100) if total > 0 else 0,
                'avg_engagement': avg_eng,
                'total': total
            }
        sorted_kw = sorted(keyword_analysis.items(), key=lambda x: x[1]['atomberg_sov'], reverse=True)
        keywords = [k for k, _ in sorted_kw]
        sov_values = [v['atomberg_sov'] for _, v in sorted_kw]
        engagement_values = [v['avg_engagement'] for _, v in sorted_kw]
        bars = ax.bar(keywords, sov_values, color=self.colors['atomberg'], alpha=0.7, label='Atomberg SoV (%)')
        ax.set_title('Keyword Performance - SoV & Engagement', fontweight='bold')
        ax.set_ylabel('Atomberg Share of Voice (%)', fontweight='bold', color=self.colors['atomberg'])
        ax.set_xlabel('Keywords', fontweight='bold')
        ax2 = ax.twinx()
        ax2.plot(keywords, engagement_values, color=self.colors['competitors'], marker='o', linewidth=2, markersize=6, label='Avg Engagement')
        ax2.set_ylabel('Average Engagement Score', fontweight='bold', color=self.colors['competitors'])
        for bar, value in zip(bars, sov_values):
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1, f'{value:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=9)
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

    def _plot_comments_sentiment(self, ax, df: pd.DataFrame):
        texts = []
        for t in df.get('all_comments', pd.Series([], dtype=str)).fillna(''):
            texts.extend([line for line in str(t).split('\n') if line.strip()])
        if not texts:
            ax.text(0.5, 0.5, 'No comments data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Comments Sentiment', fontweight='bold')
            return
        from nlp_utils import sentiment_scores
        pos = neg = neu = 0
        for line in texts:
            sc = sentiment_scores(line)['brand_adjusted']
            if sc > 0.1:
                pos += 1
            elif sc < -0.1:
                neg += 1
            else:
                neu += 1
        counts = [pos, neg, neu]
        labels = ['positive', 'negative', 'neutral']
        colors = [self.colors['positive'], self.colors['negative'], self.colors['neutral']]
        ax.pie(counts, labels=labels, autopct='%1.1f%%', colors=colors)
        ax.set_title('Comments Sentiment', fontweight='bold')


