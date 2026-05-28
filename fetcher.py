import feedparser
import requests
from datetime import datetime, date
import re

# 뉴스 소스 설정 - Google News RSS (API 키 불필요)
NEWS_SOURCES = [
    {
        'name': 'Google뉴스',
        'url': 'https://news.google.com/rss/search?q=%EB%8C%80%ED%95%99&hl=ko&gl=KR&ceid=KR:ko',
        'keyword': '대학'
    },
]

# 국내 주요 신문 RSS (대학 관련 섹션)
NEWSPAPER_RSS = [
    {'name': '연합뉴스(사회)', 'url': 'https://www.yna.co.kr/rss/society.xml'},
]

KEYWORD = '대학'

def parse_date(entry):
    """feedparser entry에서 날짜 추출"""
    for attr in ('published_parsed', 'updated_parsed'):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:3]).strftime('%Y-%m-%d')
            except Exception:
                pass
    return date.today().isoformat()

def clean_html(text):
    """HTML 태그 제거"""
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&[a-z]+;', ' ', text)
    return text.strip()[:500]

def extract_source(entry, default_source):
    """기사 출처 추출"""
    # Google News의 경우 source 필드 존재
    source = getattr(entry, 'source', None)
    if source:
        if isinstance(source, dict):
            return source.get('title', default_source)
        return str(source)
    return default_source

def fetch_from_rss(source_info):
    """RSS 피드에서 대학 관련 기사 수집"""
    articles = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; NewsArchiver/1.0)'}
        resp = requests.get(source_info['url'], headers=headers, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        for entry in feed.entries:
            title = clean_html(getattr(entry, 'title', ''))
            desc = clean_html(getattr(entry, 'summary', '') or getattr(entry, 'description', ''))
            link = getattr(entry, 'link', '')

            if not title or not link:
                continue

            # '대학' 키워드 필터링
            keyword = source_info.get('keyword', KEYWORD)
            if keyword and keyword not in title and keyword not in desc:
                continue

            pub_date = parse_date(entry)
            source_name = extract_source(entry, source_info['name'])

            articles.append({
                'title': title,
                'link': link,
                'description': desc,
                'source': source_name,
                'published_date': pub_date,
            })
    except Exception as e:
        print(f"[오류] {source_info['name']} 수집 실패: {e}")

    return articles

def fetch_news():
    """모든 소스에서 뉴스 수집 후 저장"""
    from database import save_articles

    all_articles = []

    # Google News RSS
    for src in NEWS_SOURCES:
        arts = fetch_from_rss(src)
        print(f"[{src['name']}] {len(arts)}개 수집")
        all_articles.extend(arts)

    # 국내 신문 RSS (대학 키워드 필터링)
    for src in NEWSPAPER_RSS:
        src_with_kw = {**src, 'keyword': KEYWORD}
        arts = fetch_from_rss(src_with_kw)
        print(f"[{src['name']}] {len(arts)}개 수집")
        all_articles.extend(arts)

    saved = save_articles(all_articles)
    print(f"총 {len(all_articles)}개 수집 → {saved}개 신규 저장")
    return saved

if __name__ == '__main__':
    from database import init_db
    init_db()
    fetch_news()
