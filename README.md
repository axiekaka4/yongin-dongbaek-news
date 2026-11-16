# 용인 동백 소식

용인특례시 기흥구 동백 일대의 **행정소식 · 가볼 만한 곳 · 동네 가게** 소식을 모아 보여 주는 정적 웹사이트입니다.
인스타그램 [@yongin_dongbaek_news](https://www.instagram.com/yongin_dongbaek_news/)에 올라간 카드뉴스를 그대로 모아, 카테고리·검색·상세 보기를 제공합니다.

- 공개 주소: **https://axiekaka4.github.io/yongin-dongbaek-news/**
- 호스팅: GitHub Pages (저장소 `main` 브랜치 루트, `/`) — 빌드 과정 없는 순수 HTML/CSS/JS
- 구성: 모바일 퍼스트, 외부 라이브러리·CDN 없음 (오프라인에서도 동작)

## 폴더 구조

```
index.html                 페이지 뼈대 (배너·필터·검색·모달)
assets/css/style.css       스타일
assets/js/app.js           posts.json 을 읽어 카드 피드·상세 모달 렌더링
assets/posts/*.jpg         카드뉴스 이미지 (1080x1080)
data/posts.json            전체 소식 데이터 (이 파일만 늘리면 사이트가 갱신됨)
scripts/add_post.py        새 소식 1건 추가 + 커밋/푸시 도우미
```

## 새 소식 추가 (인스타 게시 직후)

인스타그램 게시가 끝나면 아래 한 줄이면 됩니다. 이미지 복사, `posts.json` 추가, 커밋, 푸시까지 처리합니다.

```bash
cd sites/yongin-dongbaek-news
python3 scripts/add_post.py \
  --category admin \
  --title "용인특례시, …" \
  --summary "카드에 보일 한두 문장" \
  --place "경기 용인시 기흥구 …" \
  --image ../../downloads/insta-admin-2026-11-17.jpg \
  --body-file /tmp/body-2026-11-17.txt \
  --info "접종 기간=2026.11.9.~12.8." \
  --info "문의=기흥구보건소 031-6193-0314" \
  --source "용인특례시 보도자료|http://www.yongin.go.kr/..." \
  --instagram "https://www.instagram.com/p/XXXXXXXX/" \
  --tag "어린이 인플루엔자" --tag "무료 접종" \
  --push
```

- `--category`: `admin`(행정소식) / `place`(가볼 만한 곳) / `shop`(동네 가게) — 필수
- `--image` 경로는 PNG도 됩니다(자동으로 1080x1080 JPEG로 변환). JPEG는 400KB 이하 그대로 복사.
- `--body` 를 여러 번 쓰거나 `--body-file`(빈 줄로 문단 구분)을 씁니다.
- `--info`, `--source`, `--tag` 는 여러 번 사용할 수 있습니다. `--source` 형식은 `라벨|URL`.
- `--dry-run` 으로 미리 결과(JSON)를 확인할 수 있고, `--push` 를 빼면 커밋까지만 합니다.
- 같은 `--instagram` URL이 이미 들어 있으면 **아무 것도 하지 않고 건너뜁니다** (업로드 재시도에 안전).
- 실행하면 웹 주소(`…/#/post/<id>`)를 출력합니다. Pages 반영은 보통 30초~1분.

### 자동 스케줄에 붙일 때 (09:00 / 12:00 / 17:00)

게시 성공 뒤 아래 순서로 실행하면 됩니다(각 인스타 스케줄 작업이 게시 직후 1회 호출).

```bash
cd sites/yongin-dongbaek-news
# 0) 원격 최신 상태로 맞춰 두고 (다른 회차가 먼저 올렸을 수 있음)
git pull --rebase --autostash origin main
# 1) 캡션에 쓴 내용을 body.txt(문단 구분: 빈 줄)로 저장한 뒤
python3 scripts/add_post.py --category <admin|place|shop> \
  --title "…" --summary "…" --place "…" \
  --image <게시에 쓴 1080x1080 JPEG 경로> \
  --body-file body.txt \
  --info "라벨=내용" --source "라벨|URL" \
  --instagram "<게시물 URL>" --tag "태그" --push
```

## 데이터 형식 (`data/posts.json`)

```json
{
  "site": "용인 동백 소식",
  "updated_at": "2026-11-16T17:07:00+09:00",
  "posts": [
    {
      "id": "2026-11-16-shop-dongrak-coffee",
      "date": "2026-11-16",
      "published_at": "2026-11-16T17:07:00+09:00",
      "category": "shop",
      "category_label": "동네 가게",
      "title": "제목",
      "summary": "카드 요약(1~2문장)",
      "place": "주소 또는 지역 (검색 대상)",
      "image": "assets/posts/2026-11-16-shop-dongrak-coffee.jpg",
      "tags": ["태그"],
      "body": ["본문 문단1", "본문 문단2"],
      "info": [{ "label": "주소", "value": "…" }],
      "sources": [{ "label": "출처 이름", "url": "https://…" }],
      "instagram": { "url": "https://www.instagram.com/p/…/", "label": "@yongin_dongbaek_news 게시물" }
    }
  ]
}
```

- `posts` 는 최신순으로 정렬되어 있습니다(스크립트가 자동 정렬).
- `body` 는 문단 배열, `info` 는 상세 화면의 "핵심 정보" 표, `sources` 는 "링크·출처" 목록입니다. 값이 비어 있으면 해당 영역이 그려지지 않습니다.
- 상세 화면은 `#/post/<id>` 로 바로 열 수 있습니다(공유용 링크).
- 직접 손으로 편집해도 되지만, 빠뜨린 쉼표 하나로 사이트 전체가 비어 보일 수 있으니 `python3 -c "import json;json.load(open('data/posts.json'))"` 로 확인하세요.

## 로컬 미리보기

```bash
cd sites/yongin-dongbaek-news
python3 -m http.server 8000
# 브라우저에서 http://localhost:8000
```

(`index.html` 을 파일로 바로 열면 `fetch` 가 막혀 목록이 비어 보입니다. 서버로 열어 주세요.)

## 배포

- `main` 브랜치 루트를 그대로 서빙합니다 (`/.nojekyll` 포함 — Jekyll 처리 생략).
- 푸시 후 1분 안에 https://axiekaka4.github.io/yongin-dongbaek-news/ 에 반영됩니다.
- 이미지·JSON은 캐시되므로, 갱신이 안 보이면 새로고침(캐시 비우기) 하세요. `app.js` 는 `posts.json` 을 `no-store` 로 요청합니다.
