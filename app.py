from flask import Flask, render_template, request, jsonify
from datetime import date, timedelta
from urllib.parse import quote
from database import (
    init_db, get_articles_by_date, get_available_dates,
    get_sources_by_date, get_articles_by_date_and_source,
    search_articles, get_total_count
)
from fetcher import fetch_news
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)

def _korean_date(date_str):
    try:
        dt = date.fromisoformat(date_str)
        return f"{dt.year}년 {dt.month}월 {dt.day}일"
    except Exception:
        return date_str

app.jinja_env.filters['korean_date'] = _korean_date
app.jinja_env.filters['urlencode'] = lambda s: quote(str(s), safe='')

# 매일 오전 8시 자동 수집 스케줄러
scheduler = BackgroundScheduler()
scheduler.add_job(func=fetch_news, trigger='cron', hour=8, minute=0)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())


@app.route('/')
def index():
    today = date.today().isoformat()
    target_date = request.args.get('date', today)
    source_filter = request.args.get('source', '')

    # 오늘 데이터 없으면 자동 수집
    articles = get_articles_by_date(target_date)
    if not articles and target_date == today:
        fetch_news()
        articles = get_articles_by_date(target_date)

    sources = get_sources_by_date(target_date)
    available_dates = get_available_dates()
    total_count = get_total_count()

    if source_filter and source_filter in sources:
        articles = get_articles_by_date_and_source(target_date, source_filter)

    # 이전/다음 날짜 계산
    try:
        dt = date.fromisoformat(target_date)
        prev_date = (dt - timedelta(days=1)).isoformat()
        next_date = (dt + timedelta(days=1)).isoformat()
        next_date = next_date if next_date <= today else None
    except ValueError:
        prev_date = next_date = None

    return render_template(
        'index.html',
        articles=articles,
        current_date=target_date,
        today=today,
        prev_date=prev_date,
        next_date=next_date,
        sources=sources,
        selected_source=source_filter,
        available_dates=available_dates,
        total_count=total_count,
        article_count=len(articles),
    )


@app.route('/search')
def search():
    keyword = request.args.get('q', '').strip()
    articles = []
    if keyword:
        articles = search_articles(keyword)
    return render_template(
        'search.html',
        articles=articles,
        keyword=keyword,
        total_count=get_total_count(),
    )


@app.route('/api/fetch', methods=['POST'])
def api_fetch():
    try:
        saved = fetch_news()
        return jsonify({'success': True, 'message': f'{saved}개의 새 기사를 수집했습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/articles')
def api_articles():
    target_date = request.args.get('date', date.today().isoformat())
    articles = get_articles_by_date(target_date)
    return jsonify(articles)


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001, use_reloader=False)
