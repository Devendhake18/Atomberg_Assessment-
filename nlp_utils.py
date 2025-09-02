from typing import Dict, List
import re
import pandas as pd
import numpy as np
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer

from config import BRAND_NAME, COMPETITOR_BRANDS

_vader = SentimentIntensityAnalyzer()
_lemm = WordNetLemmatizer()
_stop = set(stopwords.words('english'))

def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        return ''
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    tokens = word_tokenize(text)
    tokens = [_lemm.lemmatize(t) for t in tokens if t not in _stop and len(t) > 2]
    return ' '.join(tokens)

def sentiment_scores(text: str) -> Dict:
    if not text:
        return {'vader': 0.0, 'textblob': 0.0, 'brand_adjusted': 0.0}
    v = _vader.polarity_scores(text)['compound']
    tb = TextBlob(text).sentiment.polarity
    return {'vader': v, 'textblob': tb, 'brand_adjusted': v}

def extract_brand_mentions(text: str) -> List[str]:
    # include common variants and spacing issues
    variants = [BRAND_NAME, BRAND_NAME.replace(' ', ''), BRAND_NAME.replace(' ', '-'), BRAND_NAME.replace(' ', '_'), 'atom berg']
    brands = list(dict.fromkeys(variants + COMPETITOR_BRANDS))
    found = []
    tl = (text or '').lower()
    for b in brands:
        bl = b.lower()
        if bl in tl:
            found.append(b)
    # de-duplicate while preserving original case
    seen = set()
    dedup = []
    for b in found:
        bl = b.lower()
        if bl not in seen:
            seen.add(bl)
            dedup.append(b)
    return dedup


