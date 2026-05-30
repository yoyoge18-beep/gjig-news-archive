import smtplib, os, sys
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
now = datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')

user     = os.environ['GMAIL_USERNAME']
password = os.environ['GMAIL_APP_PASSWORD']
fetch    = os.environ.get('FETCH_RESULT', '')
build    = os.environ.get('BUILD_RESULT', '')
run_id   = os.environ.get('RUN_ID', '')

body = "\n".join([
    "대학 기사 아카이브 - 오늘의 수집 결과",
    "",
    f"실행 일시: {now}",
    "사이트: https://yoyoge18-beep.github.io/gjig-news-archive/",
    "",
    "--- 뉴스 수집 ---",
    fetch,
    "",
    "--- 빌드 ---",
    build,
    "",
    f"Actions 로그: https://github.com/yoyoge18-beep/gjig-news-archive/actions/runs/{run_id}",
])

msg = MIMEText(body, 'plain', 'utf-8')
msg['Subject'] = f'[기사아카이브] {now} 수집 완료'
msg['From']    = user
msg['To']      = user

try:
    with smtplib.SMTP('smtp.gmail.com', 587) as s:
        s.ehlo()
        s.starttls()
        s.login(user, password)
        s.sendmail(user, [user], msg.as_string())
    print('이메일 발송 완료')
except Exception as e:
    print(f'이메일 발송 실패: {e}', file=sys.stderr)
    sys.exit(1)
