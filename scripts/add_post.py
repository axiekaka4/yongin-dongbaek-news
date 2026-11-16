#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
용인 동백 소식 — 새 소식 1건 추가 도우미

인스타그램 게시가 끝난 뒤 이 스크립트를 한 번 실행하면
  1) 카드뉴스 이미지를 assets/posts/ 로 복사(필요하면 1080px JPEG로 변환)
  2) data/posts.json 맨 앞(최신순)에 항목 추가
  3) git add / commit / pull --rebase / push
까지 처리해 웹사이트가 바로 갱신되게 한다.

예시 (행정소식):
  python3 scripts/add_post.py \
    --category admin \
    --title "용인특례시, 겨울철 수도계량기 동파 예방 안내" \
    --summary "기온이 크게 떨어질 때는 수도계량기 보온에 신경 써 주세요." \
    --place "용인특례시 기흥구" \
    --image ../../downloads/insta-admin-2026-11-17.jpg \
    --body-file /tmp/body.txt \
    --info "대상=단독주택·상가 수도계량기" \
    --info "문의=용인시 상수도사업소 031-324-4114" \
    --source "용인특례시 보도자료|http://www.yongin.go.kr/..." \
    --instagram "https://www.instagram.com/p/XXXXXXX/" \
    --tag "동파예방" --tag "겨울철" \
    --push

도움말:  python3 scripts/add_post.py --help
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "posts.json")
IMGDIR = os.path.join(ROOT, "assets", "posts")
SITE_URL = "https://axiekaka4.github.io/yongin-dongbaek-news/"
CATEGORIES = {"admin": "행정소식", "place": "가볼 만한 곳", "shop": "동네 가게"}
KST = dt.timezone(dt.timedelta(hours=9))
# 로컬 git config에 user.name/user.email이 없을 때 쓰는 기본 값
GIT_FALLBACK_NAME = "리드테니스 2호점"
GIT_FALLBACK_EMAIL = "axiekaka4@users.noreply.github.com"


def die(msg, code=1):
    print("[실패] " + msg, file=sys.stderr)
    sys.exit(code)


def warn(msg):
    print("[알림] " + msg)


def now_kst():
    return dt.datetime.now(KST)


def slugify(text):
    """제목에서 URL에 쓸 수 있는 짧은 조각을 만든다. 한글 제목이면 해시로 대체."""
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    s = s[:28].strip("-")
    if s:
        return s
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:6]


def parse_kv(items, what):
    out = []
    for it in items or []:
        if "=" not in it:
            die("--%s 값은 '라벨=내용' 형식이어야 합니다: %r" % (what, it))
        label, value = it.split("=", 1)
        label, value = label.strip(), value.strip()
        if not label or not value:
            die("--%s 값의 라벨/내용이 비어 있습니다: %r" % (what, it))
        out.append({"label": label, "value": value})
    return out


def parse_sources(items):
    out = []
    for it in items or []:
        if "|" in it:
            label, url = it.split("|", 1)
            label, url = label.strip(), url.strip()
            if not url.startswith("http"):
                die("출처 URL이 http(s)로 시작하지 않습니다: %r" % it)
            out.append({"label": label, "url": url})
        elif it.strip().startswith("http"):
            out.append({"label": "출처", "url": it.strip()})
        else:
            die("--source 값은 '라벨|URL' 또는 'URL' 형식이어야 합니다: %r" % it)
    return out


def read_body(args):
    if args.body_file:
        path = os.path.expanduser(args.body_file)
        if not os.path.isfile(path):
            die("본문 파일을 찾을 수 없습니다: %s" % path)
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        paras = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    elif args.body:
        paras = [p.strip() for p in args.body if p.strip()]
    else:
        paras = []
    return [re.sub(r"\s*\n\s*", " ", p) for p in paras]


def prepare_image(src, post_id, quality):
    """이미지를 assets/posts/<id>.jpg 로 저장. PNG 등은 1080x1080 JPEG로 변환."""
    src = os.path.expanduser(src)
    if not os.path.isfile(src):
        die("이미지 파일을 찾을 수 없습니다: %s" % src)
    os.makedirs(IMGDIR, exist_ok=True)
    dest_name = post_id + ".jpg"
    dest = os.path.join(IMGDIR, dest_name)

    ext = os.path.splitext(src)[1].lower()
    if ext in (".jpg", ".jpeg") and os.path.getsize(src) <= 400 * 1024:
        shutil.copyfile(src, dest)
        return "assets/posts/" + dest_name

    try:
        from PIL import Image
    except ImportError:
        die("PNG 등은 Pillow가 필요합니다. JPEG(400KB 이하)로 준비해 다시 실행하거나 Pillow를 설치하세요.")

    im = Image.open(src)
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    if im.width != 1080 or im.height != 1080:
        im = im.resize((1080, 1080), Image.LANCZOS)
    for q in (88, 84, 80, 76):
        im.save(dest, "JPEG", quality=q, optimize=True, progressive=True)
        if os.path.getsize(dest) <= 320 * 1024:
            break
    return "assets/posts/" + dest_name


def load_json():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def save_json(data):
    tmp = DATA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, DATA)


def git(args, check=True, capture=True):
    res = subprocess.run(["git"] + args, cwd=ROOT, text=True,
                         capture_output=capture)
    if check and res.returncode != 0:
        die("git %s 실패: %s" % (" ".join(args), (res.stderr or res.stdout or "").strip()))
    return res


def git_identity_args():
    """로컬 git config에 사용자 정보가 없으면 -c 로 넘길 기본 값을 돌려준다."""
    missing = False
    for key in ("user.name", "user.email"):
        res = subprocess.run(["git", "config", "--get", key], cwd=ROOT,
                             text=True, capture_output=True)
        if not (res.stdout or "").strip():
            missing = True
            break
    if not missing:
        return []
    warn("git user.name/user.email 설정이 없어 기본 값으로 커밋합니다.")
    return ["-c", "user.name=" + GIT_FALLBACK_NAME,
            "-c", "user.email=" + GIT_FALLBACK_EMAIL]


def git_commit(message):
    """커밋. 사용자 정보가 없거나 신원 확인 실패로 막히면 기본 값으로 재시도한다."""
    res = git(git_identity_args() + ["commit", "-m", message], check=False)
    if res.returncode == 0:
        print("[깃] 커밋 완료")
        return res

    out = ((res.stderr or "") + "\n" + (res.stdout or "")).lower()
    if "nothing to commit" in out or "no changes added to commit" in out:
        print("[알림] 커밋할 변경 내용이 없습니다.")
        return res

    identity_hint = ("please tell me who you are", "unable to auto-detect email",
                     "empty ident", "author identity unknown",
                     "user.email", "user.name")
    if any(h in out for h in identity_hint):
        warn("git 사용자 정보가 없어 기본 값으로 다시 커밋합니다.")
        res = git(["-c", "user.name=" + GIT_FALLBACK_NAME,
                   "-c", "user.email=" + GIT_FALLBACK_EMAIL,
                   "commit", "-m", message], check=False)
        if res.returncode == 0:
            print("[깃] 커밋 완료 (기본 사용자 정보 사용)")
            return res
        out = ((res.stderr or "") + "\n" + (res.stdout or "")).lower()
        if "nothing to commit" in out or "no changes added to commit" in out:
            print("[알림] 커밋할 변경 내용이 없습니다.")
            return res

    die("git commit 실패: %s" % (res.stderr or res.stdout or "").strip())
    return res


def main():
    ap = argparse.ArgumentParser(
        description="용인 동백 소식 웹사이트에 새 소식 1건을 추가합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="카테고리: admin(행정소식) / place(가볼 만한 곳) / shop(동네 가게)")
    ap.add_argument("--category", required=True, choices=sorted(CATEGORIES),
                    help="admin | place | shop")
    ap.add_argument("--title", required=True, help="제목")
    ap.add_argument("--summary", default="", help="카드에 보이는 한두 문장 요약")
    ap.add_argument("--place", default="", help="장소 (검색에 쓰임. 예: 경기 용인시 기흥구 동백5로 12)")
    ap.add_argument("--image", required=True, help="카드뉴스 이미지 경로 (.jpg 권장, 1080x1080)")
    ap.add_argument("--body", action="append", default=[],
                    help="본문 문단 (여러 번 사용 가능)")
    ap.add_argument("--body-file", default="", help="본문 파일 (빈 줄로 문단 구분)")
    ap.add_argument("--info", action="append", default=[],
                    help="핵심 정보 '라벨=내용' (여러 번 사용 가능)")
    ap.add_argument("--tag", action="append", default=[], help="태그 (여러 번 사용 가능)")
    ap.add_argument("--source", action="append", default=[],
                    help="출처 '라벨|URL' (여러 번 사용 가능)")
    ap.add_argument("--instagram", default="", help="인스타그램 게시물 URL")
    ap.add_argument("--instagram-label", default="@yongin_dongbaek_news 게시물",
                    help="인스타 링크 아래 설명 문구")
    ap.add_argument("--date", default="", help="게시 날짜 YYYY-MM-DD (기본: 오늘)")
    ap.add_argument("--time", default="", help="게시 시각 HH:MM (기본: 지금)")
    ap.add_argument("--id", default="", help="항목 ID 직접 지정 (기본: 날짜-카테고리-제목조각)")
    ap.add_argument("--quality", type=int, default=88, help="이미지 변환 품질 (기본 88)")
    ap.add_argument("--dry-run", action="store_true", help="파일/깃을 바꾸지 않고 결과만 확인")
    ap.add_argument("--no-git", action="store_true", help="git commit/push 생략")
    ap.add_argument("--push", action="store_true",
                    help="commit 후 원격(main)으로 push. 없으면 commit까지만")
    args = ap.parse_args()

    if not os.path.isfile(DATA):
        die("data/posts.json 이 없습니다. 저장소 루트에서 실행하세요: %s" % DATA)

    data = load_json()
    posts = data.get("posts", [])

    # 중복 방지: 같은 인스타 게시물이 이미 등록돼 있으면 아무 것도 하지 않는다.
    ig = args.instagram.strip()
    if ig:
        for p in posts:
            if (p.get("instagram") or {}).get("url", "").rstrip("/") == ig.rstrip("/"):
                print("[건너뜀] 이미 등록된 게시물입니다: %s" % ig)
                print("  제목: %s" % p.get("title", ""))
                return 0

    today = args.date.strip() or now_kst().strftime("%Y-%m-%d")
    try:
        dt.datetime.strptime(today, "%Y-%m-%d")
    except ValueError:
        die("--date 형식은 YYYY-MM-DD 입니다: %r" % today)

    if args.time.strip():
        try:
            hh, mm = args.time.strip().split(":")
            pub_dt = dt.datetime.strptime(today + " " + hh + ":" + mm, "%Y-%m-%d %H:%M").replace(tzinfo=KST)
        except ValueError:
            die("--time 형식은 HH:MM 입니다: %r" % args.time)
    else:
        n = now_kst()
        if n.strftime("%Y-%m-%d") == today:
            pub_dt = n
        else:
            pub_dt = dt.datetime.strptime(today + " 00:00", "%Y-%m-%d %H:%M").replace(tzinfo=KST)
    pub_dt = pub_dt.replace(microsecond=0)

    post_id = args.id.strip() or "%s-%s-%s" % (today, args.category, slugify(args.title))
    if any(p.get("id") == post_id for p in posts):
        if args.id:
            die("같은 ID의 항목이 이미 있습니다: %s" % post_id)
        post_id += "-" + hashlib.sha1((args.title + str(pub_dt)).encode("utf-8")).hexdigest()[:4]

    body = read_body(args)
    if not body:
        warn("본문이 비어 있습니다. 상세 화면에 요약만 보입니다.")

    info = parse_kv(args.info, "info")
    sources = parse_sources(args.source)

    post = {
        "id": post_id,
        "date": today,
        "published_at": pub_dt.isoformat(),
        "category": args.category,
        "category_label": CATEGORIES[args.category],
        "title": args.title.strip(),
        "summary": args.summary.strip(),
        "place": args.place.strip(),
        "image": "assets/posts/%s.jpg" % post_id,
        "tags": [t.lstrip("#").strip() for t in args.tag if t.strip()],
        "body": body,
        "info": info,
        "sources": sources,
        "instagram": ({"url": ig, "label": args.instagram_label} if ig else {})
    }

    if args.dry_run:
        print("[미리보기] 아래 항목이 추가될 예정입니다 (파일/깃 변경 없음):")
        print(json.dumps(post, ensure_ascii=False, indent=2))
        return 0

    post["image"] = prepare_image(args.image, post_id, args.quality)

    posts.append(post)
    posts.sort(key=lambda p: p.get("published_at") or p.get("date") or "", reverse=True)
    data["posts"] = posts
    data["site"] = data.get("site") or "용인 동백 소식"
    data["updated_at"] = post["published_at"]
    save_json(data)

    print("[등록] %s · %s" % (CATEGORIES[args.category], post["title"]))
    print("  ID:    %s" % post_id)
    print("  날짜:  %s" % post["published_at"])
    print("  이미지: %s (%d KB)" % (post["image"], os.path.getsize(os.path.join(ROOT, post["image"])) // 1024))
    print("  전체:  %d건" % len(posts))
    print("  웹:    %s#/post/%s" % (SITE_URL, post_id))

    if args.no_git:
        print("[알림] --no-git 이므로 커밋하지 않았습니다.")
        return 0

    if subprocess.run(["git", "rev-parse", "--git-dir"], cwd=ROOT,
                      capture_output=True).returncode != 0:
        die("git 저장소가 아닙니다. 먼저 클론하거나 git init 하세요: %s" % ROOT)

    git(["add", "-A", "data/posts.json", post["image"]])
    git_commit("post: %s %s — %s" % (today, CATEGORIES[args.category], post["title"]))

    if not args.push:
        print("[알림] --push 가 없어 원격에는 올리지 않았습니다. 배포하려면 --push 로 다시 실행하거나 git push 하세요.")
        return 0

    pull = git(["pull", "--rebase", "--autostash", "origin", "main"], check=False)
    if pull.returncode != 0:
        warn("pull 실패 — push를 계속 시도합니다: %s" % (pull.stderr or "").strip()[:200])

    push = git(["push", "origin", "HEAD:main"], check=False)
    if push.returncode != 0:
        die("push 실패: %s\n커밋은 로컬에 남아 있습니다. 원격 상태를 확인한 뒤 다시 push 하세요."
            % (push.stderr or push.stdout or "").strip())

    print("[푸시] origin/main 반영 완료")
    print("  사이트: %s" % SITE_URL)
    print("  (GitHub Pages 반영에 보통 30초~1분 걸립니다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
