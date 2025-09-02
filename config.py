import os
from dotenv import load_dotenv

load_dotenv('config.env')

BRAND_NAME = os.getenv('BRAND_NAME', 'Atomberg')
COMPETITOR_BRANDS = [b.strip() for b in os.getenv('COMPETITOR_BRANDS', 'Havells,Crompton,Orient,USHA,Bajaj').split(',') if b.strip()]

# API keys
# Google disabled (YouTube-only pipeline)
GOOGLE_API_KEY = None
GOOGLE_CX = None
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# Limits and pagination
RESULTS_PER_KEYWORD = int(os.getenv('SEARCH_RESULTS_PER_PLATFORM', '10'))
GOOGLE_MAX_RESULTS_TOTAL = 0
GOOGLE_TIMEOUT_SECONDS = 0

YOUTUBE_RESULTS_PER_KEYWORD = min(50, int(os.getenv('YOUTUBE_RESULTS_PER_KEYWORD', '15')))
COMMENTS_PER_VIDEO = min(100, int(os.getenv('COMMENTS_PER_VIDEO', '50')))

# Composite SoV weights
SOV_WEIGHT_BASIC = float(os.getenv('SOV_WEIGHT_BASIC', '0.40'))
SOV_WEIGHT_ENGAGEMENT = float(os.getenv('SOV_WEIGHT_ENGAGEMENT', '0.30'))
SOV_WEIGHT_SENTIMENT = float(os.getenv('SOV_WEIGHT_SENTIMENT', '0.20'))
SOV_WEIGHT_VISIBILITY = float(os.getenv('SOV_WEIGHT_VISIBILITY', '0.10'))

# Paths
PLOTS_DIR = 'plots'
REPORTS_DIR = 'reports'
EMBEDDINGS_DIR = 'embeddings'


