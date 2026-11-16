/* 용인 동백 소식 — data/posts.json 을 읽어 카드 피드와 상세 모달을 그린다. */
(function () {
  'use strict';

  var CATS = {
    admin: { label: '행정소식', emoji: '🏛️' },
    place: { label: '가볼 만한 곳', emoji: '🌿' },
    shop: { label: '동네 가게', emoji: '🏪' }
  };

  var state = {
    posts: [],
    updatedAt: null,
    cat: 'all',
    q: '',
    currentId: null,
    lastFocus: null
  };

  var $ = function (sel) { return document.querySelector(sel); };
  var el = {
    feed: $('#feed'),
    tabs: Array.prototype.slice.call(document.querySelectorAll('.tab')),
    q: $('#q'),
    qClear: $('#q-clear'),
    resultLine: $('#result-line'),
    empty: $('#empty'),
    emptyReset: $('#empty-reset'),
    loading: $('#loading'),
    loadError: $('#load-error'),
    modal: $('#modal'),
    modalScroll: $('#modal-scroll'),
    modalPanel: document.querySelector('.modal-panel'),
    modalClose: $('#modal-close')
  };

  /* ── helpers ───────────────────────────── */
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function norm(s) {
    return String(s == null ? '' : s).toLowerCase().replace(/[\s\u00b7,.\-·()\[\]'"“”‘’]/g, '');
  }

  function catOf(post) {
    var key = post.category;
    var meta = CATS[key] || null;
    return {
      key: key,
      label: (meta && meta.label) || post.category_label || '소식',
      emoji: (meta && meta.emoji) || ''
    };
  }

  function fmtDate(iso, withWeekday) {
    var d = new Date(iso);
    if (isNaN(d)) return iso || '';
    var days = ['일', '월', '화', '수', '목', '금', '토'];
    var s = d.getFullYear() + '.' + String(d.getMonth() + 1).padStart(2, '0') + '.' + String(d.getDate()).padStart(2, '0');
    if (withWeekday) s += ' (' + days[d.getDay()] + ')';
    return s;
  }

  function fmtDateTime(iso) {
    var d = new Date(iso);
    if (isNaN(d)) return fmtDate(iso, false);
    var hh = String(d.getHours()).padStart(2, '0');
    var mm = String(d.getMinutes()).padStart(2, '0');
    return fmtDate(iso, false) + ' ' + hh + ':' + mm;
  }

  function timeOf(post) {
    var t = Date.parse(post.published_at || post.date);
    return isNaN(t) ? 0 : t;
  }

  function postText(post) {
    var parts = [post.title, post.summary, post.place, post.category_label];
    if (Array.isArray(post.body)) parts = parts.concat(post.body);
    if (Array.isArray(post.tags)) parts = parts.concat(post.tags);
    if (Array.isArray(post.info)) {
      post.info.forEach(function (row) { parts.push(row.label, row.value); });
    }
    return norm(parts.join(' '));
  }

  /* ── data ──────────────────────────────── */
  function load() {
    var url = 'data/posts.json?t=' + Date.now();
    return fetch(url, { cache: 'no-store' })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        var list = Array.isArray(data) ? data : (data.posts || []);
        state.posts = list.slice().sort(function (a, b) { return timeOf(b) - timeOf(a); });
        state.updatedAt = (data && data.updated_at) || (state.posts[0] && state.posts[0].published_at) || null;
      });
  }

  /* ── feed ──────────────────────────────── */
  function visiblePosts() {
    var q = norm(state.q);
    return state.posts.filter(function (p) {
      if (state.cat !== 'all' && p.category !== state.cat) return false;
      if (!q) return true;
      return postText(p).indexOf(q) !== -1;
    });
  }

  function cardHTML(post) {
    var c = catOf(post);
    var img = post.image
      ? '<img src="' + esc(post.image) + '" alt="' + esc(post.title) + ' 카드뉴스 이미지" loading="lazy" decoding="async">'
      : '<div class="ph">이미지 준비 중</div>';

    var summary = post.summary ? '<p class="card-summary">' + esc(post.summary) + '</p>' : '';
    var place = post.place
      ? '<span class="card-place"><svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a7 7 0 0 1 7 7c0 5-7 13-7 13S5 14 5 9a7 7 0 0 1 7-7Zm0 4.5A2.5 2.5 0 1 0 12 11.5 2.5 2.5 0 0 0 12 6.5Z"/></svg>' + esc(post.place) + '</span>'
      : '';

    return '' +
      '<button class="card" type="button" data-id="' + esc(post.id) + '" aria-label="' + esc(post.title) + ' 상세 보기">' +
        '<div class="card-figure">' +
          '<span class="badge ' + esc(c.key) + '">' + esc(c.emoji + ' ' + c.label) + '</span>' +
          img +
        '</div>' +
        '<div class="card-body">' +
          '<span class="card-date">' + esc(fmtDateTime(post.published_at || post.date)) + '</span>' +
          '<h2 class="card-title">' + esc(post.title) + '</h2>' +
          summary +
          place +
        '</div>' +
      '</button>';
  }

  function render() {
    var list = visiblePosts();

    el.loading.hidden = true;

    if (!state.posts.length) {
      el.feed.innerHTML = '';
      el.empty.hidden = true;
      el.resultLine.textContent = '';
      return;
    }

    el.feed.innerHTML = list.map(cardHTML).join('');
    el.empty.hidden = list.length > 0;

    var catLabel = state.cat === 'all' ? '전체' : (CATS[state.cat] ? CATS[state.cat].label : state.cat);
    var bits = [catLabel + ' ' + list.length + '건'];
    if (state.q.trim()) bits.push('"' + state.q.trim() + '" 검색 결과');
    if (state.updatedAt) bits.push('최근 업데이트 ' + fmtDateTime(state.updatedAt));
    el.resultLine.textContent = bits.join(' · ');

    // 이미지가 없거나 깨져도 카드가 무너지지 않게
    Array.prototype.forEach.call(el.feed.querySelectorAll('.card-figure img'), function (img) {
      img.addEventListener('error', function () {
        var fig = img.parentElement;
        img.remove();
        var ph = document.createElement('div');
        ph.className = 'ph';
        ph.textContent = '이미지 준비 중';
        fig.appendChild(ph);
      }, { once: true });
    });
  }

  function setCat(cat) {
    state.cat = cat;
    el.tabs.forEach(function (t) {
      var on = t.getAttribute('data-cat') === cat;
      t.classList.toggle('is-active', on);
      t.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    render();
  }

  function setQuery(q) {
    state.q = q;
    el.qClear.hidden = !q;
    render();
  }

  /* ── modal ─────────────────────────────── */
  function infoHTML(post) {
    if (!Array.isArray(post.info) || !post.info.length) return '';
    var rows = post.info.map(function (row) {
      return '<div class="info-row"><dt>' + esc(row.label) + '</dt><dd>' + esc(row.value) + '</dd></div>';
    }).join('');
    return '<h3 class="section-label">핵심 정보</h3><dl class="info-card">' + rows + '</dl>';
  }

  function bodyHTML(post) {
    if (!Array.isArray(post.body) || !post.body.length) return '';
    return '<div class="article-body">' + post.body.map(function (p) {
      return '<p>' + esc(p) + '</p>';
    }).join('') + '</div>';
  }

  function linksHTML(post) {
    var links = [];
    var sources = Array.isArray(post.sources) ? post.sources : (post.source ? [post.source] : []);
    sources.forEach(function (s) {
      if (!s || !s.url) return;
      links.push(
        '<a class="link-btn" href="' + esc(s.url) + '" target="_blank" rel="noopener">' +
          '<span>' + esc(s.label || '출처') + '<span class="sub">원문·공식 안내 보기</span></span>' +
          '<span class="arrow">↗</span>' +
        '</a>'
      );
    });
    if (post.instagram && post.instagram.url) {
      links.push(
        '<a class="link-btn ig" href="' + esc(post.instagram.url) + '" target="_blank" rel="noopener">' +
          '<span>인스타그램 원글' + (post.instagram.label ? '<span class="sub">' + esc(post.instagram.label) + '</span>' : '') + '</span>' +
          '<span class="arrow">↗</span>' +
        '</a>'
      );
    }
    if (!links.length) return '';
    return '<h3 class="section-label">링크·출처</h3><div class="link-list">' + links.join('') + '</div>';
  }

  function tagsHTML(post) {
    if (!Array.isArray(post.tags) || !post.tags.length) return '';
    return '<h3 class="section-label">태그</h3><div class="tags">' +
      post.tags.map(function (t) { return '<span class="tag">#' + esc(t) + '</span>'; }).join('') +
      '</div>';
  }

  function findPost(id) {
    for (var i = 0; i < state.posts.length; i++) if (state.posts[i].id === id) return state.posts[i];
    return null;
  }

  function openPost(id, opts) {
    opts = opts || {};
    var post = findPost(id);
    if (!post) return false;

    var c = catOf(post);
    var hero = post.image
      ? '<div class="article-hero"><img src="' + esc(post.image) + '" alt="' + esc(post.title) + ' 카드뉴스 이미지"></div>'
      : '';

    el.modalScroll.innerHTML = '' +
      hero +
      '<div class="article-inner">' +
        '<div class="article-meta">' +
          '<span class="pill ' + esc(c.key) + '">' + esc(c.emoji + ' ' + c.label) + '</span>' +
          '<span>' + esc(fmtDate(post.published_at || post.date, true)) + '</span>' +
          (post.place ? '<span>· ' + esc(post.place) + '</span>' : '') +
        '</div>' +
        '<h2 class="article-title" id="modal-title">' + esc(post.title) + '</h2>' +
        (post.summary ? '<p class="article-lead">' + esc(post.summary) + '</p>' : '') +
        bodyHTML(post) +
        infoHTML(post) +
        linksHTML(post) +
        tagsHTML(post) +
        '<p class="article-note">안내된 정보는 게시 시점의 공개 자료를 정리한 것입니다. 방문·이용 전에 기관이나 가게의 최신 안내를 함께 확인해 주세요.</p>' +
      '</div>';

    if (!state.currentId) state.lastFocus = document.activeElement;
    state.currentId = id;
    el.modal.hidden = false;
    document.body.classList.add('modal-open');
    el.modalScroll.scrollTop = 0;
    el.modalPanel.focus({ preventScroll: true });

    if (opts.push) {
      try { history.pushState({ post: id }, '', '#/post/' + encodeURIComponent(id)); } catch (e) {}
    }
    return true;
  }

  function closeModal(opts) {
    opts = opts || {};
    if (el.modal.hidden) return;
    el.modal.hidden = true;
    document.body.classList.remove('modal-open');
    el.modalScroll.innerHTML = '';
    state.currentId = null;

    if (!opts.fromHistory) {
      if (history.state && history.state.post) {
        history.back();
      } else if (location.hash.indexOf('#/post/') === 0) {
        try { history.replaceState(null, '', location.pathname + location.search); } catch (e) {}
      }
    }
    if (state.lastFocus && typeof state.lastFocus.focus === 'function') {
      try { state.lastFocus.focus({ preventScroll: true }); } catch (e) {}
    }
    state.lastFocus = null;
  }

  function syncFromHash() {
    var h = decodeURIComponent(location.hash || '');
    if (h.indexOf('#/post/') === 0) {
      var id = h.slice('#/post/'.length);
      if (!state.posts.length) return;
      if (state.currentId === id) return;
      openPost(id, { push: false });
    } else {
      closeModal({ fromHistory: true });
    }
  }

  /* ── events ────────────────────────────── */
  function bind() {
    el.tabs.forEach(function (t) {
      t.addEventListener('click', function () { setCat(t.getAttribute('data-cat')); });
    });

    var t;
    el.q.addEventListener('input', function (e) {
      var v = e.target.value;
      clearTimeout(t);
      t = setTimeout(function () { setQuery(v); }, 120);
    });

    el.qClear.addEventListener('click', function () {
      el.q.value = '';
      setQuery('');
      el.q.focus();
    });

    el.emptyReset.addEventListener('click', function () {
      el.q.value = '';
      state.q = '';
      el.qClear.hidden = true;
      setCat('all');
    });

    el.feed.addEventListener('click', function (e) {
      var card = e.target.closest('.card');
      if (card) openPost(card.getAttribute('data-id'), { push: true });
    });

    el.modalClose.addEventListener('click', function () { closeModal(); });
    el.modal.addEventListener('click', function (e) {
      if (e.target.getAttribute('data-close') === '1') closeModal();
    });

    document.addEventListener('keydown', function (e) {
      if (el.modal.hidden) return;
      if (e.key === 'Escape') { e.preventDefault(); closeModal(); return; }
      if (e.key === 'Tab') {
        var f = el.modalPanel.querySelectorAll('a[href],button:not([disabled])');
        if (!f.length) return;
        var first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });

    window.addEventListener('popstate', syncFromHash);
    window.addEventListener('hashchange', syncFromHash);
  }

  /* ── start ─────────────────────────────── */
  function start() {
    bind();
    load().then(function () {
      render();
      if (location.hash.indexOf('#/post/') === 0) syncFromHash();
    }).catch(function (err) {
      el.loading.hidden = true;
      el.loadError.hidden = false;
      el.resultLine.textContent = '';
      if (window.console) console.error('[dongbaek-news] posts load failed:', err);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
