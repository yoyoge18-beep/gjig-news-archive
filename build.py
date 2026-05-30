#!/usr/bin/env python3
"""
대학 기사 아카이브 — 정적 사이트 생성기
실행: python3 build.py
결과: dist/ 폴더에 정적 HTML 파일 생성
배포: GitHub Pages / Netlify / Vercel 등에 dist/ 폴더 업로드
"""

import os
import json
import shutil
from datetime import date, timedelta

from database import (
    init_db, get_articles_by_date, get_available_dates,
    get_total_count, get_sources_by_date,
)

DIST = 'dist'

# ── 유틸리티 ─────────────────────────────────────────────
def esc(s):
    """HTML 특수문자 이스케이프"""
    return str(s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def korean_date(date_str):
    try:
        dt = date.fromisoformat(date_str)
        return f"{dt.year}년 {dt.month}월 {dt.day}일"
    except Exception:
        return date_str

# ── 공통 컴포넌트 ─────────────────────────────────────────
HEAD = """\
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;600;700&display=swap" rel="stylesheet">
  <link href="./static/css/style.css" rel="stylesheet">
</head>
<body>"""

def head(title):
    return HEAD.format(title=esc(title))

def g_nav(total_count):
    return f"""\
<nav class="g-nav" role="navigation" aria-label="전역 내비게이션">
  <div class="g-nav__inner">
    <a href="./index.html" class="g-nav__brand">대학 기사 아카이브</a>
    <div class="g-nav__right">
      <span class="g-nav__count">총 <strong>{total_count}</strong>개</span>
      <a href="./search.html" class="g-nav__icon-btn" title="검색" aria-label="검색">
        <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
          <path d="M10 6.5a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0zm-.687 3.02a4.5 4.5 0 1 1 .707-.707l2.834 2.833a.5.5 0 0 1-.708.708L9.313 9.52z" fill="currentColor" fill-rule="evenodd" clip-rule="evenodd"/>
        </svg>
      </a>
    </div>
  </div>
</nav>"""

def site_footer(total_count):
    return f"""\
<footer class="site-footer">
  <div class="site-footer__inner">
    <span class="site-footer__text">© 대학 기사 아카이브</span>
    <span class="site-footer__text">총 <strong>{total_count}</strong>개 기사 보관</span>
  </div>
</footer>"""

def article_card(a):
    desc = f'<p class="article-card__desc">{esc(a.get("description",""))}</p>' if a.get('description') else ''
    return f"""\
<article class="article-card" role="listitem" data-source="{esc(a['source'])}">
  <div class="article-card__inner">
    <div class="article-card__content">
      <a href="{esc(a['link'])}" target="_blank" rel="noopener noreferrer" class="article-card__title">{esc(a['title'])}</a>
      {desc}
      <div class="article-card__meta">
        <span class="badge-source">{esc(a['source'])}</span>
        <span class="article-date">{esc(a['published_date'])}</span>
      </div>
    </div>
    <a href="{esc(a['link'])}" target="_blank" rel="noopener noreferrer"
       class="article-card__ext-btn" aria-label="{esc(a['title'])} 읽기">&#8599;</a>
  </div>
</article>"""

# ── 날짜별 페이지 렌더러 ──────────────────────────────────
def render_date_page(current_date, articles, sources, prev_date, next_date,
                     available_dates, total_count):
    kor_date = korean_date(current_date)
    article_count = len(articles)

    # 이전 / 다음 버튼
    prev_btn = (f'<a href="./{prev_date}.html" class="s-nav__arrow" aria-label="이전 날">&#8592;</a>'
                if prev_date else
                '<span class="s-nav__arrow s-nav__arrow--off" aria-hidden="true">&#8592;</span>')
    next_btn = (f'<a href="./{next_date}.html" class="s-nav__arrow" aria-label="다음 날">&#8594;</a>'
                if next_date else
                '<span class="s-nav__arrow s-nav__arrow--off" aria-hidden="true">&#8594;</span>')

    # 최근 날짜 칩
    date_chips = ''.join(
        f'<a href="./{d}.html" class="date-chip{" date-chip--active" if d == current_date else ""}">{d}</a>'
        for d in available_dates[:8]
    )

    # 언론사 필터 칩
    filter_row = ''
    if sources:
        chip_style = 'font-family:inherit;cursor:pointer;'
        chips = [
            f'<button type="button" class="filter-chip filter-chip--active" '
            f'data-src="" onclick="filterBy(this)" style="{chip_style}">'
            f'전체 <span class="filter-chip__count">{article_count}</span></button>'
        ]
        for src in sources:
            chips.append(
                f'<button type="button" class="filter-chip" '
                f'data-src="{esc(src)}" onclick="filterBy(this)" style="{chip_style}">'
                f'{esc(src)}</button>'
            )
        filter_row = (
            '<div class="filter-row" role="group" aria-label="언론사 필터">'
            + ''.join(chips) + '</div>'
        )

    # 기사 카드 목록
    if articles:
        cards = '\n'.join(article_card(a) for a in articles)
        article_list = (
            '<div class="article-grid" role="list" aria-label="기사 목록" id="article-grid">'
            + cards + '</div>'
        )
    else:
        article_list = """\
<div class="empty-state">
  <div class="empty-state__icon" aria-hidden="true">○</div>
  <h3 class="empty-state__title">기사가 없습니다</h3>
  <p class="empty-state__desc">이 날짜에 수집된 기사가 없습니다.</p>
</div>"""

    # 페이지 전체 조립
    return f"""{head(f"{kor_date} — 대학 기사 아카이브")}

{g_nav(total_count)}

<div class="s-nav" role="navigation" aria-label="날짜 내비게이션">
  <div class="s-nav__inner">
    <div class="s-nav__date-group">
      {prev_btn}
      <label class="date-pick-wrap" aria-label="날짜 선택">
        <span class="s-nav__label">{kor_date}</span>
        <input type="date" value="{current_date}" onchange="goToDate(this.value)" aria-label="날짜 선택">
      </label>
      {next_btn}
      <label class="date-pick-wrap" aria-label="달력으로 날짜 선택">
        <span class="date-pick-badge">&#128197; 날짜 선택</span>
        <input type="date" value="{current_date}" onchange="goToDate(this.value)" aria-label="달력 날짜 선택">
      </label>
    </div>
  </div>
</div>

<main>
  <section class="hero-tile" aria-label="키워드">
    <div class="hero-tile__inner">
      <p class="hero-tile__eyebrow">키워드</p>
      <h1 class="hero-tile__headline">대학</h1>
      <p class="hero-tile__tagline" id="hero-count">{article_count}건의 기사</p>
      <p class="hero-tile__sub">{kor_date} 기준</p>
    </div>
  </section>

  <section class="content-tile">
    <div class="content-tile__inner">
      <div class="section-header">
        <div>
          <h2 class="section-header__title">{kor_date}</h2>
          <p class="section-header__subtitle" id="sub-count">{article_count}건</p>
        </div>
        <div class="date-chips" role="navigation" aria-label="최근 수집일">
          {date_chips}
        </div>
      </div>
      {filter_row}
      {article_list}
    </div>
  </section>
</main>

{site_footer(total_count)}

<script>
function goToDate(val) {{
  if (val) window.location.href = './' + val + '.html';
}}
function filterBy(btn) {{
  var src = btn.dataset.src;
  var cards = document.querySelectorAll('.article-card');
  var count = 0;
  cards.forEach(function(c) {{
    var show = !src || c.dataset.source === src;
    c.style.display = show ? '' : 'none';
    if (show) count++;
  }});
  document.querySelectorAll('.filter-chip').forEach(function(c) {{
    c.classList.remove('filter-chip--active');
  }});
  btn.classList.add('filter-chip--active');
  document.getElementById('sub-count').textContent = count + '건';
  document.getElementById('hero-count').textContent = count + '건의 기사';
}}
</script>
</body>
</html>"""

# ── 검색 페이지 렌더러 ────────────────────────────────────
def render_search_page(total_count):
    return f"""{head("검색 — 대학 기사 아카이브")}

{g_nav(total_count)}

<main>
  <section class="search-tile">
    <div class="search-tile__inner">
      <h1 class="search-tile__title">검색</h1>
      <div class="search-form" role="search">
        <input class="search-input" type="search" id="q"
               placeholder="기사 제목 또는 내용 검색…"
               autofocus aria-label="기사 검색">
        <button class="btn-pill" type="button"
                onclick="doSearch()" aria-label="검색 실행">검색</button>
      </div>
    </div>
  </section>

  <section class="content-tile">
    <div class="content-tile__inner" id="results-wrap">
      <div class="empty-state">
        <div class="empty-state__icon" aria-hidden="true">&#8981;</div>
        <h3 class="empty-state__title">검색어를 입력하세요</h3>
        <p class="empty-state__desc">기사 제목이나 내용에 포함된 단어로 검색할 수 있습니다.</p>
      </div>
    </div>
  </section>
</main>

{site_footer(total_count)}

<script>
var DATA = null;
fetch('./articles.json')
  .then(function(r) {{ return r.json(); }})
  .then(function(d) {{
    DATA = d;
    var q = new URLSearchParams(location.search).get('q');
    if (q) {{ document.getElementById('q').value = q; doSearch(); }}
  }});

document.getElementById('q').addEventListener('keydown', function(e) {{
  if (e.key === 'Enter') doSearch();
}});

function esc(s) {{
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}
function korDate(d) {{
  var p = d.split('-');
  return p[0] + '년 ' + parseInt(p[1]) + '월 ' + parseInt(p[2]) + '일';
}}

function doSearch() {{
  var kw = document.getElementById('q').value.trim();
  var wrap = document.getElementById('results-wrap');
  if (!kw || !DATA) {{
    wrap.innerHTML = '<div class="empty-state"><div class="empty-state__icon">&#8981;</div>'
      + '<h3 class="empty-state__title">검색어를 입력하세요</h3>'
      + '<p class="empty-state__desc">기사 제목이나 내용에 포함된 단어로 검색할 수 있습니다.</p></div>';
    return;
  }}
  var lk = kw.toLowerCase();
  var found = DATA.filter(function(a) {{
    return (a.title || '').toLowerCase().includes(lk)
        || (a.description || '').toLowerCase().includes(lk);
  }}).slice(0, 50);

  var html = '<div class="section-header"><div>'
    + '<h2 class="section-header__title">"' + esc(kw) + '"</h2>'
    + '<p class="section-header__subtitle">'
    + (found.length ? found.length + '건의 결과' : '결과 없음')
    + '</p></div></div>';

  if (!found.length) {{
    html += '<div class="empty-state"><div class="empty-state__icon">&#8981;</div>'
      + '<h3 class="empty-state__title">결과가 없습니다</h3>'
      + '<p class="empty-state__desc">"' + esc(kw) + '"에 대한 기사를 찾을 수 없습니다.</p>'
      + '<a href="./index.html" class="btn-pill btn-pill--ghost">날짜별 보기로 돌아가기</a></div>';
    wrap.innerHTML = html;
    return;
  }}

  html += '<div class="article-grid" role="list">';
  found.forEach(function(a) {{
    html += '<article class="article-card" role="listitem"><div class="article-card__inner">'
      + '<div class="article-card__content">'
      + '<a href="' + esc(a.link) + '" target="_blank" rel="noopener noreferrer" class="article-card__title">'
      + esc(a.title) + '</a>';
    if (a.description) {{
      html += '<p class="article-card__desc">' + esc(a.description) + '</p>';
    }}
    html += '<div class="article-card__meta">'
      + '<span class="badge-source">' + esc(a.source) + '</span>'
      + '<a href="./' + esc(a.published_date) + '.html" class="article-date">'
      + korDate(a.published_date) + '</a></div></div>'
      + '<a href="' + esc(a.link) + '" target="_blank" rel="noopener noreferrer"'
      + ' class="article-card__ext-btn">&#8599;</a></div></article>';
  }});
  html += '</div>';
  wrap.innerHTML = html;
}}
</script>
</body>
</html>"""

# ── 메인 빌드 함수 ────────────────────────────────────────
def build():
    init_db()
    print('대학 기사 아카이브 — 정적 사이트 빌드\n')

    # dist/ 초기화 및 static 파일 복사
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)
    shutil.copytree('static', os.path.join(DIST, 'static'))
    print('✓ static/ 복사 완료\n')

    available_dates = get_available_dates()
    total_count = get_total_count()
    all_articles = []
    today = date.today().isoformat()
    dates_set = set(available_dates)

    # 날짜별 HTML 페이지 생성
    for d in available_dates:
        articles = get_articles_by_date(d)
        sources = get_sources_by_date(d)
        all_articles.extend(articles)

        try:
            dt = date.fromisoformat(d)
            prev_d = (dt - timedelta(days=1)).isoformat()
            next_d = (dt + timedelta(days=1)).isoformat()
            prev_date = prev_d if prev_d in dates_set else None
            next_date = next_d if (next_d in dates_set and next_d <= today) else None
        except Exception:
            prev_date = next_date = None

        html = render_date_page(
            current_date=d,
            articles=articles,
            sources=sources,
            prev_date=prev_date,
            next_date=next_date,
            available_dates=available_dates,
            total_count=total_count,
        )
        out_path = os.path.join(DIST, f'{d}.html')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'  {d}.html  ({len(articles)}건)')

    # index.html — 최신 날짜로 리디렉션
    latest = available_dates[0] if available_dates else 'search'
    index_html = (
        '<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">'
        f'<meta http-equiv="refresh" content="0;url=./{latest}.html">'
        '<title>대학 기사 아카이브</title></head>'
        f'<body><p><a href="./{latest}.html">이동 중…</a></p></body></html>'
    )
    with open(os.path.join(DIST, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
    print(f'\n✓ index.html → {latest}.html 리디렉션')

    # articles.json — 검색용 전체 기사 데이터
    search_data = [
        {k: a[k] for k in ('title', 'link', 'description', 'source', 'published_date') if k in a}
        for a in all_articles
    ]
    with open(os.path.join(DIST, 'articles.json'), 'w', encoding='utf-8') as f:
        json.dump(search_data, f, ensure_ascii=False)
    print(f'✓ articles.json  ({len(search_data)}건)')

    # search.html
    with open(os.path.join(DIST, 'search.html'), 'w', encoding='utf-8') as f:
        f.write(render_search_page(total_count=total_count))
    print('✓ search.html\n')

    print(f'완료!  dist/ 에 {len(available_dates)}개 날짜 · {len(all_articles)}건 기사 생성')
    print()
    print('── 배포 방법 ──────────────────────────────')
    print('• GitHub Pages : dist/ 폴더를 gh-pages 브랜치에 push')
    print('• Netlify      : dist/ 폴더를 드래그 앤 드롭')
    print('• Vercel       : vercel --prod (Output Directory: dist)')
    print('────────────────────────────────────────────')


if __name__ == '__main__':
    build()
