# -*- coding: utf-8 -*-
"""Збирає статичну копію rvn.com.ua з source/rvn-dump.json у теку dist/.

Запуск:  python build.py
Перегляд: python serve.py  →  http://localhost:8137
"""
import json, re, html, shutil, datetime, unicodedata, os
from pathlib import Path
from PIL import Image, ImageOps
import content as C

ROOT = Path(__file__).parent
# Для попереднього перегляду на GitHub Pages: RVN_BASE=/rvn-site RVN_NOINDEX=1 python build.py
BASE = os.environ.get('RVN_BASE', '').rstrip('/')
NOINDEX = os.environ.get('RVN_NOINDEX') == '1'
SRC = ROOT / 'source'
DIST = ROOT / 'dist'
IMG_OUT = DIST / 'img'

SITE = 'https://rvn.com.ua'
BRAND = 'Робимо вам нерви'
BRAND_SHORT = 'РВН'
EMAIL = 'robymo.vam.nervy@gmail.com'
MAP_SRC = 'https://www.google.com/maps/d/embed?mid=19TCSNDhSDeH43Wbb1G0Sk49XPg_Up5E'
DONATE = 'https://base.monobank.ua/8Cx7oUbAxXqMWb'
JAR = 'https://send.monobank.ua/jar/5jRYkGfcEx'
SOCIALS = [
    ('instagram', 'РВН в Instagram', 'https://www.instagram.com/rvn.com.ua'),
    ('facebook', 'РВН у Facebook', 'https://www.facebook.com/rvn.com.ua/'),
    ('youtube', 'РВН на YouTube', 'https://www.youtube.com/@robymovamnervy'),
    ('tiktok', 'РВН у TikTok', 'https://www.tiktok.com/@rvn.com.ua'),
]
NAV = [('/pro-nas', 'Про нас'), ('/blog', 'Блоґ'), ('/movniinspektsii', 'Мовні інспекції'),
       ('/podii', 'Події'), ('/doluchytysia', 'Долучитися'), ('/contacts', 'Контакти')]

# Старі адреси статей → нові (301 у .htaccess та _redirects)
RENAMES = {
    '/-': '/yak-deputaty-zalyshaiut-odesu-bez-rishen',
    '/----': '/oun-na-odeshchyni',
    '/blog-post': '/100-richchia-niny-strokatoi',
}

# Дані, яких немає в джерелі або які треба підтвердити — див. README.md
STATS = C.STATS   # цифри з документа «РВН 4 роки», див. content.py
HOME_GALLERY_ALT = [
    'Учасники зустрічі РВН у вишиванках',
    'Виступ на зустрічі РВН',
    'Учасники просвітницького заходу РВН',
    'Команда й учасники заходу РВН',
]
SIGNS_ALT = [
    ('Вивіска «Таврия В» до зміни напису', 'Вивіска «Таврія В» після зміни напису'),
    ('Російськомовна вивіска «Самая вкусная шаурма» до зміни', 'Україномовна вивіска «Найсмачніша шаурма» після зміни'),
    ('Вивіска «Ривьера — офис у моря» до зміни напису', 'Вивіска «Рів’єра — офіс біля моря» після зміни напису'),
]
HERO_ALT = 'Учасники акції з українськими прапорами біля Одеського оперного театру'
DUPLICATE_IMAGES = ('-1-w0CtOYN8aPwgaASF',)   # повтор фото у статті про Майдан
MONTHS = ['січня', 'лютого', 'березня', 'квітня', 'травня', 'червня', 'липня',
          'серпня', 'вересня', 'жовтня', 'листопада', 'грудня']

dump = json.loads((SRC / 'rvn-dump.json').read_text(encoding='utf-8'))
e = html.escape


# ---------------------------------------------------------------- зображення
def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


_img_cache = {}


def _open(name):
    path = str((SRC / name if '/' in name else SRC / 'img' / name).resolve())
    im = Image.open('\\\\?\\' + path if os.name == 'nt' else path)   # довгі назви файлів у Windows
    im = ImageOps.exif_transpose(im)
    if im.mode not in ('RGB', 'RGBA'):
        im = im.convert('RGBA' if 'A' in im.getbands() or im.mode == 'P' else 'RGB')
    return im


def variants(name, widths=(480, 768, 1200, 1600), ratio=None, tag=''):
    """Готує WebP-варіанти. ratio=(w,h) → обрізання по центру. Повертає [(w,h,url)]."""
    key = (name, widths, ratio)
    if key in _img_cache:
        return _img_cache[key]
    im = _open(name)
    if ratio:
        target = ratio[0] / ratio[1]
        w, h = im.size
        if w / h > target:
            nw = int(h * target); x = (w - nw) // 2; im = im.crop((x, 0, x + nw, h))
        else:
            nh = int(w / target); y = (h - nh) // 2; im = im.crop((0, y, w, y + nh))
    base = slug(Path(name).stem)[-48:].strip('-') + (('-' + tag) if tag else '')
    ws = sorted({min(w, im.size[0]) for w in widths})
    out = []
    for w in ws:
        h = round(im.size[1] * w / im.size[0])
        fn = f'{base}-{w}.webp'
        dst = IMG_OUT / fn
        if not dst.exists():
            r = im.resize((w, h), Image.LANCZOS) if w != im.size[0] else im
            lossless = name.lower().endswith('.png') and tag == 'doc'
            r.save(dst, 'WEBP', quality=78, method=6, lossless=lossless)
        out.append((w, h, f'/img/{fn}'))
    _img_cache[key] = out
    return out


def img_tag(name, alt, sizes, widths=(480, 768, 1200, 1600), ratio=None, tag='',
            eager=False, cls=''):
    v = variants(name, tuple(widths), ratio, tag)
    w, h, src = v[-1] if len(v) == 1 else v[min(1, len(v) - 1)]
    srcset = ', '.join(f'{u} {vw}w' for vw, vh, u in v)
    load = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
    c = f' class="{cls}"' if cls else ''
    return (f'<img{c} src="{src}" srcset="{srcset}" sizes="{sizes}" width="{w}" height="{h}" '
            f'alt="{e(alt)}" {load} decoding="async">')


# ---------------------------------------------------------------- дані з дампа
def fname(src):
    return src.split('/')[-1].split('?')[0]


def run_text(it):
    return ''.join(' ' if 'br' in r else r['t'] for r in it['runs']).replace('\xa0', ' ').strip()


def find_text(page, prefix):
    for s in dump[page]['secs']:
        for it in s['items']:
            if it['k'] == 't' and run_text(it).startswith(prefix):
                return run_text(it)
    raise KeyError(prefix)


def find_btn(page, text):
    for s in dump[page]['secs']:
        for it in s['items']:
            if it['k'] == 'btn' and it['text'].strip() == text:
                return it['href']
    raise KeyError(text)


def url(path):
    """Внутрішня адреса з урахуванням перейменувань."""
    if not path:
        return path
    if path.startswith(SITE):
        path = path[len(SITE):] or '/'
    if path.startswith('/'):
        p = path.split('?')[0].split('#')[0].rstrip('/') or '/'
        return RENAMES.get(p, p)
    return path


def uk_date(d):
    return f'{d.day} {MONTHS[d.month - 1]} {d.year} р.'


def runs_html(runs, all_bold_is_plain=True):
    """Перетворює фрагменти тексту на список HTML-абзаців (розрив рядка = новий абзац)."""
    paras, cur = [], []
    for r in runs:
        if 'br' in r:
            paras.append(cur); cur = []
        else:
            cur.append(r)
    paras.append(cur)
    out = []
    for p in paras:
        if not ''.join(r['t'] for r in p).strip():
            continue
        plain_bold = all_bold_is_plain and all(r.get('b') or not r['t'].strip() for r in p)
        buf = ''
        for r in p:
            t = e(r['t'], quote=False)
            if r.get('i'):
                t = f'<em>{t}</em>'
            if r.get('b') and not plain_bold and r['t'].strip():
                t = f'<strong>{t}</strong>'
            if r.get('href'):
                h = url(r['href'])
                ext = ' rel="noopener" target="_blank"' if h.startswith('http') else ''
                t = f'<a href="{e(h)}"{ext}>{t}</a>'
            buf += t
        buf = re.sub(r'</strong>(\s*)<strong>', r'\1', buf)
        buf = re.sub(r'</em>(\s*)<em>', r'\1', buf)
        out.append(buf.strip())
    return out


class Post:
    pass


def parse_post(old_path):
    pg = dump[old_path]
    secs = pg['secs']
    head = [it for it in secs[1]['items'] if it['k'] == 't']
    p = Post()
    p.old = old_path
    p.path = url(old_path)
    p.title = run_text(head[0])
    rest = [run_text(it) for it in head[1:]]
    p.desc = rest[0]
    di = next(i for i, t in enumerate(rest) if re.fullmatch(r'\d{1,2}/\d{1,2}/\d{4}', t))
    m, d, y = map(int, rest[di].split('/'))
    p.date = datetime.date(y, m, d)
    p.author = re.sub(r'^Автори?:\s*', '', rest[di - 1]).strip()
    p.category = rest[1] if di - 1 > 1 else ''
    p.meta_desc = pg['desc']
    # вміст
    items = []
    for s in secs[2:-1]:
        for it in s['items']:
            if it['rect'][0] >= 1190 and it['rect'][2] < 320:
                continue                      # бічний блок «Останні статті»
            if it['k'] == 'img' and (it['rect'][2] < 120 or any(d in it['src'] for d in DUPLICATE_IMAGES)):
                continue
            if it['k'] in ('t', 'img', 'btn'):
                items.append(it)
    items.sort(key=lambda it: (round(it['rect'][1] / 12), it['rect'][0]))
    p.items = items
    p.images = [fname(it['src']) for it in items if it['k'] == 'img']
    return p


POST_PATHS = [k for k in dump if k not in ('/', '/blog', '/blog-page2', '/movniinspektsii', '/podii', '/contacts')]
posts = sorted((parse_post(k) for k in POST_PATHS), key=lambda p: p.date, reverse=True)
covers = {}
for pk in ('/blog', '/blog-page2', '/'):
    for s in dump[pk]['secs']:
        for it in s['items']:
            if it['k'] == 'img' and it.get('href') in dump and it['rect'][2] > 200:
                covers.setdefault(it['href'], fname(it['src']))
for p in posts:
    p.cover = covers.get(p.old) or (p.images[0] if p.images else None)
    p.html = None


def para(t):
    return t if t.startswith('<') else f'<p>{e(t, quote=False)}</p>'


def news_post(n):
    p = Post()
    p.old, p.path, p.date, p.title, p.desc, p.category = None, n['path'], n['date'], n['title'], n['desc'], n['cat']
    p.meta_desc = n['desc']
    p.author = n['author']
    p.cover = n['slides'][0][0]
    p.images = [f for f, _, _ in n['slides']]
    p.news = n
    p.html = True
    return p


posts = sorted(posts + [news_post(n) for n in C.NEWS], key=lambda p: p.date, reverse=True)
for p in posts:
    p.category = C.CATEGORY_OVERRIDES.get(p.path) or (p.category or '').capitalize()
CATEGORIES = [c for c in C.CATEGORY_ORDER if any(p.category == c for p in posts)]


def cat_slug(c):
    return C.CATEGORY_SLUGS.get(c, slug(c))


def ig_url(n):
    return f"https://www.instagram.com/{'reel' if n.get('reel') else 'p'}/{n['ig']}/"


def carousel(n):
    slides = n['slides']
    if n.get('reel'):
        f, alt, _ = slides[0]
        poster = variants(f, (720,), None, 'poster')[0][2]
        return (f'<figure class="reel"><video controls preload="none" playsinline poster="{poster}" width="720" height="1280">'
                f'<source src="/media/{n["ig"]}.mp4" type="video/mp4"></video>'
                f'<figcaption>{e(alt)}. <a href="{ig_url(n)}" rel="noopener" target="_blank">Відео в Instagram</a></figcaption></figure>')
    if len(slides) == 1:
        f, alt, _ = slides[0]
        return f'<div class="figs figs-1"><figure>{img_tag(f, alt, "(min-width: 900px) 600px, calc(100vw - 48px)", (480, 860, 1200), None, "sl", True)}</figure></div>'
    items = ''
    for i, (f, alt, video) in enumerate(slides, 1):
        im = img_tag(f, alt, '(min-width: 900px) 380px, 78vw', (380, 760), (4, 5), 'sl', i == 1)
        badge = f'<a class="car-video" href="{ig_url(n)}" rel="noopener" target="_blank" aria-label="Відео в Instagram">▶</a>' if video else ''
        items += f'<li class="car-slide" aria-roledescription="слайд" aria-label="{i} з {len(slides)}">{im}{badge}</li>'
    return (f'<section class="carousel" aria-roledescription="карусель" aria-label="Світлини з допису">'
            f'<ul class="car-track" tabindex="0">{items}</ul>'
            f'<div class="car-ctrl"><button type="button" class="car-prev" aria-label="Попередній слайд">{icon("arrow-l", 18)}</button>'
            f'<span class="car-count" aria-live="polite">1 / {len(slides)}</span>'
            f'<button type="button" class="car-next" aria-label="Наступний слайд">{icon("arrow", 18)}</button></div></section>')


def credits_html(n):
    rows = ''
    for role, name, handle in n['credits']:
        link = f'<a href="https://www.instagram.com/{e(handle)}/" rel="noopener" target="_blank">@{e(handle)}</a>' if handle else ''
        who = f'{e(name)} ({link})' if name and link else (e(name) if name else link)
        rows += f'<li><span>{e(role)}</span>{who}</li>'
    if not rows:
        rows = '<li><span>Автор</span>Команда РВН</li>'
    return (f'<aside class="credits" aria-label="Над матеріялом працювали"><p class="credits-h">Над матеріялом працювали</p><ul>{rows}</ul>'
            f'<p class="credits-src">Першоджерело: <a href="{ig_url(n)}" rel="noopener" target="_blank">допис РВН в Instagram</a></p></aside>')


def news_html(p):
    n = p.news
    out = []
    for blk in n['body']:
        k = blk[0]
        if k == 'p':
            out.append(f'<p>{e(blk[1], quote=False)}</p>')
        elif k == 'h2':
            out.append(f'<h2>{e(blk[1], quote=False)}</h2>')
        elif k == 'ul':
            out.append('<ul>' + ''.join(f'<li>{x}</li>' for x in blk[1]) + '</ul>')
        elif k == 'quote':
            out.append(f'<figure class="pull"><blockquote><p>«{e(blk[1], quote=False)}»</p></blockquote><figcaption>{e(blk[2])}</figcaption></figure>')
        elif k == 'carousel':
            out.append(carousel(n))
        elif k == 'cta':
            out.append(f'<p class="btn-row">{btn("Долучитися", "/doluchytysia", "red")}{btn("Підтримати", "/pidtrymaty", "outline")}</p>')
        elif k == 'complaint':
            out.append(f'<p class="btn-row">{btn("Лишити скаргу", find_btn("/movniinspektsii", "Лишити скаргу"), "red")}</p>')
    out.append(credits_html(n))
    words = sum(len(re.sub('<[^>]+>', ' ', t).split()) for t in out if 'carousel' not in t)
    return out, words


# ---------------------------------------------------------------- компоненти
ICONS = {
    'instagram': '<rect x="3" y="3" width="18" height="18" rx="5" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="17.3" cy="6.7" r="1.3"/>',
    'facebook': '<path d="M22 12c0-5.52-4.48-10-10-10S2 6.48 2 12c0 4.84 3.44 8.87 8 9.8V15H8v-3h2V9.5C10 7.57 11.57 6 13.5 6H16v3h-2c-.55 0-1 .45-1 1v2h3v3h-3v6.95c5.05-.5 9-4.76 9-9.95z"/>',
    'youtube': '<path d="M21.6 7.2a2.5 2.5 0 0 0-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4A2.5 2.5 0 0 0 2.4 7.2C2 8.8 2 12 2 12s0 3.2.4 4.8a2.5 2.5 0 0 0 1.8 1.8C5.8 19 12 19 12 19s6.2 0 7.8-.4a2.5 2.5 0 0 0 1.8-1.8c.4-1.6.4-4.8.4-4.8s0-3.2-.4-4.8zM10 15V9l5.2 3z"/>',
    'tiktok': '<path d="M16.5 3c.3 2.1 1.5 3.6 3.5 3.9v3c-1.3 0-2.5-.4-3.5-1v6.3a5.7 5.7 0 1 1-5.7-5.7c.3 0 .6 0 .9.1v3.1a2.7 2.7 0 1 0 1.8 2.5V3z"/>',
    'users': '<path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" d="M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zm-6.5 9c0-3.3 2.9-5.5 6.5-5.5s6.5 2.2 6.5 5.5M16 4.3a3.5 3.5 0 0 1 0 6.4M18 14.8c2.1.7 3.5 2.4 3.5 5.2"/>',
    'calendar': '<path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" d="M4 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2zM4 10h16M8 3v4M16 3v4M8 14h2M14 14h2"/>',
    'doc': '<path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M6 3h9l4 4v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM9 9h6M9 13l2 2 4-4"/>',
    'heart': '<path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" d="M12 20s-7.5-4.6-7.5-10.2A4.3 4.3 0 0 1 12 7.2a4.3 4.3 0 0 1 7.5 2.6C19.500 15.400 12 20 12 20z"/>',
}


def icon(name, size=24):
    return f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="currentColor" aria-hidden="true" focusable="false">{ICONS[name]}</svg>'


def socials(cls='socials', size=22):
    lis = ''.join(f'<li><a href="{u}" aria-label="{e(label)}" rel="noopener" target="_blank">{icon(k, size)}</a></li>'
                  for k, label, u in SOCIALS)
    return f'<ul class="{cls}">{lis}</ul>'


def btn(text, href, kind='red', big=False):
    ext = ' rel="noopener" target="_blank"' if href.startswith('http') else ''
    return f'<a class="btn btn-{kind}{" btn-big" if big else ""}" href="{e(href)}"{ext}>{e(text)}</a>'


ICONS.update({
    'mail': '<path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" d="M3 6.5A1.5 1.5 0 0 1 4.5 5h15A1.5 1.5 0 0 1 21 6.5v11a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5zM3.5 6l8.5 7 8.5-7"/>',
    'arrow': '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M13 6l6 6-6 6"/>',
    'arrow-l': '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M19 12H5M11 6l-6 6 6 6"/>',
    'flag': '<path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
})
ICONS.update({
    'telegram': '<path d="M21.4 4.2 2.9 11.3c-1.3.5-1.2 1.3-.2 1.6l4.7 1.5 1.8 5.6c.2.6.4.8.9.8.4 0 .6-.2.9-.5l2.3-2.2 4.8 3.5c.9.5 1.5.2 1.7-.8l3.1-14.7c.3-1.3-.5-1.9-1.5-1.4zM8.4 14.1l9.7-6.1c.5-.3.9-.1.5.2l-8.1 7.3-.3 3.3z"/>',
    'link': '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    'share': '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M12 3v12M7 8l5-5 5 5M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6"/>',
})
YEAR = datetime.date.today().year


def arrow_link(text, name='arrow'):
    return f'<span class="more">{e(text)}{icon(name, 18)}</span>'


def sec_head(title, sub='', level='h2'):
    s = f'<p>{e(sub)}</p>' if sub else ''
    return f'<div class="sec-head"><{level}>{e(title)}</{level}>{s}</div>'


def header(current):
    logo = variants('logo-1-SvkvHc1uyi0uawRf.png', (160, 320), tag='logo')
    nav = ''.join(f'<li><a href="{h}"{" aria-current=\"page\"" if h == current else ""}>{t}</a></li>' for h, t in NAV)
    return f'''<a class="skip" href="#main">Перейти до вмісту</a>
<header class="site-header">
  <div class="wrap bar">
    <a class="logo" href="/" aria-label="На головну — {BRAND}"><img src="{logo[0][2]}" srcset="{logo[0][2]} 1x, {logo[-1][2]} 2x" width="77" height="79" alt=""><span class="brand-name" aria-hidden="true">Робимо<br>вам нерви</span></a>
    <button class="menu-toggle" aria-expanded="false" aria-controls="nav" aria-label="Меню"><span></span><span></span><span></span></button>
    <nav id="nav" aria-label="Головне меню"><ul class="menu">{nav}</ul>{socials()}<a class="btn btn-dark btn-sm" href="/pidtrymaty">{icon('heart', 18)}<span>Підтримати</span></a></nav>
  </div>
</header>'''


def footer():
    logo = variants('logo-1-SvkvHc1uyi0uawRf.png', (160, 320), tag='logo')
    about = find_text('/', 'ГО «Робимо вам нерви»').split('. ')[0] + '.'
    links = ''.join(f'<li><a href="{h}">{t}</a></li>' for h, t in NAV)
    return f'''<footer class="site-footer">
  <div class="wrap foot">
    <div class="foot-brand">
      <a class="foot-logo" href="/" aria-label="На головну — {BRAND}"><img src="{logo[0][2]}" srcset="{logo[0][2]} 1x, {logo[-1][2]} 2x" width="77" height="79" alt="{BRAND}" loading="lazy"></a>
      <p class="foot-about">{e(about)}</p>
      {socials('socials', 20)}
    </div>
    <nav class="foot-nav" aria-label="Розділи сайту">
      <p class="foot-h">Розділи</p>
      <ul>{links}<li><a href="/pidtrymaty">Підтримати</a></li><li><a href="/pytannia">Часті питання</a></li><li><a href="/dlia-media">Для медія</a></li><li><a href="/rss.xml">RSS блоґу</a></li></ul>
    </nav>
    <div class="foot-contact">
      <p class="foot-h">Зв'язатися з нами</p>
      <p><a class="foot-mail" href="mailto:{EMAIL}">{EMAIL}</a></p>
      <p>{btn('Підтримати', '/pidtrymaty', 'red')}</p>
    </div>
  </div>
  <p class="foot-word" aria-hidden="true">Робимо вам нерви</p>
  <div class="foot-bottom"><div class="wrap foot-bottom-in"><p>© {YEAR} ГО «{BRAND}» · ЄДРПОУ {C.EDRPOU}</p><p><a href="/privacy">Політика конфіденційности</a></p></div></div>
</footer>'''




def page(path, title, desc, body, current=None, og=None, ld=None, noindex=False, full_title=None):
    canon = SITE + ('/' if path == '/' else path)
    t = full_title or f'{title} | {BRAND_SHORT}'
    ogimg = SITE + (og or variants('img_5686-2-vRdG3ZdFPOWcBUEe.JPG', (1200,), (1200, 630), 'og')[0][2])
    robots = '<meta name="robots" content="noindex">' if noindex or NOINDEX else ''
    ldj = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' if ld else ''
    return f'''<!doctype html>
<html lang="uk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(t)}</title>
<meta name="description" content="{e(desc)}">
{robots}<link rel="canonical" href="{canon}">
<meta property="og:type" content="{'article' if ld and ld.get('@type') == 'Article' else 'website'}">
<meta property="og:locale" content="uk_UA">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{ogimg}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#fcf0e0">
<link rel="icon" href="/img/favicon.png" type="image/png">
<link rel="apple-touch-icon" href="/img/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&display=swap">
<link rel="stylesheet" href="/style.css">
<link rel="alternate" type="application/rss+xml" title="Блоґ {BRAND_SHORT}" href="/rss.xml">
{ldj}
</head>
<body>
{header(current)}
<main id="main">
{body}
</main>
{footer()}
<button type="button" class="to-top" aria-label="Повернутися нагору">{icon('arrow', 20)}</button>
<script src="/site.js" defer></script>
</body>
</html>
'''


def card(p, level='h3', eager=False, featured=False):
    if featured:
        cover = img_tag(p.cover, '', '(min-width: 1100px) 660px, (min-width: 900px) 55vw, calc(100vw - 48px)', (480, 800, 1200), (16, 10), 'fc', eager) if p.cover else ''
    else:
        cover = img_tag(p.cover, '', '(min-width: 1100px) 380px, (min-width: 640px) 45vw, calc(100vw - 48px)', (400, 800), (5, 3), 'cover', eager) if p.cover else ''
    cat = f'<span class="pill">{e(p.category)}</span>' if p.category else ''
    return f'''<article class="card{' card-featured' if featured else ''}" data-cat="{cat_slug(p.category) if p.category else ''}">
  <div class="card-img">{cover}</div>
  <div class="card-body">
    {cat}
    <{level} class="card-title"><a href="{p.path}">{e(p.title)}</a></{level}>
    <p class="card-desc">{e(p.desc)}</p>
    <p class="card-meta"><span>{e(p.author)}</span><time datetime="{p.date.isoformat()}">{uk_date(p.date)}</time></p>
  </div>
</article>'''


# ---------------------------------------------------------------- сторінки
def build_home():
    d = dump['/']
    def imgs(sec):
        return [it for it in d['secs'][sec]['items'] if it['k'] == 'img']
    gallery = ''.join(f'<li>{img_tag(fname(it["src"]), alt, "(min-width: 900px) 280px, 45vw", (320, 640), (1, 1), "sq")}</li>'
                      for it, alt in zip(imgs(2), HOME_GALLERY_ALT))
    stats = ''.join(f'<li class="stat">{icon(k, 30)}<p class="stat-num">{e(n)}</p><p class="stat-label">{e(l)}</p></li>' for k, n, l in STATS)
    media_sec = d['secs'][6]['items']
    m_imgs = sorted([it for it in media_sec if it['k'] == 'img'], key=lambda it: it['rect'][0])
    m_titles = sorted([it for it in media_sec if it['k'] == 't' and it['tag'] == 'h3'], key=lambda it: it['rect'][0])
    m_btns = sorted([it for it in media_sec if it['k'] == 'btn'], key=lambda it: it['rect'][0])
    media = ''.join(f'''<li class="media-card">{img_tag(fname(i["src"]), i["alt"], "(min-width: 1100px) 380px, (min-width: 640px) 45vw, calc(100vw - 48px)", (480, 800), (4, 3), "m")}
<div class="media-body"><h3><a href="{e(b["href"])}" rel="noopener" target="_blank">{e(run_text(t))}</a></h3>{arrow_link("Детальніше")}</div></li>''' for i, t, b in zip(m_imgs, m_titles, m_btns))
    events = [
        ('photo_2026-03-26_01-43-53-1-zZ7cdm3Fv6S84Gem.jpg', 'Мурал Одеси', "На честь громадського активіста Дем'яна Ганула"),
        ('photo_2026-09-29_16-42-05-jKBJSSrHsXPD7mHw.jpg', 'Наліпки про полон', 'Адже полон — це пекло. Не дамо забути.'),
        ('img_6070-5xdrFsxNvwGGpNJ2.JPG', 'Мовні ігри', 'Створення спільноти зі схожими цінностями та поглядами'),
        ('img_3555-vwGUuBCzv8xqZd2h.jpg', 'Підтримка одеських діячів', 'Допомога з виданням збірки Олекси Різникова «Під пресом репресій»'),
    ]
    alts = {fname(it['src']): it['alt'] for s in d['secs'] for it in s['items'] if it['k'] == 'img'}
    ev = ''.join(f'''<li class="event-card">{img_tag(f, alts[f], "(min-width: 900px) 580px, calc(100vw - 48px)", (580, 1160), (16, 9), "ev")}
<div class="event-body"><h3>{e(t)}</h3><p>{e(s)}</p></div></li>''' for f, t, s in events)
    tm = team_html()
    hero = variants('img_5686-2-vRdG3ZdFPOWcBUEe.JPG', (480, 768, 1280, 1920), tag='hero')
    hero_img = (f'<img class="hero-bg" src="{hero[2][2]}" srcset="{", ".join(f"{u} {w}w" for w, h, u in hero)}" sizes="100vw" '
                f'width="{hero[2][0]}" height="{hero[2][1]}" alt="{e(HERO_ALT)}" loading="eager" fetchpriority="high" decoding="async">')
    join = find_btn('/', 'Вступити в ГО')
    lead = find_text('/', 'Долучайтеся до підтримки')
    ticker = ''.join(f'<span>{e(t)}</span>' for t in C.SLOGANS * 2)
    body = f'''<section class="hero">{hero_img}
  <div class="wrap hero-in">
    <p class="eyebrow">ГО «{BRAND}» · Одеса</p>
    <h1>Відновлюємо українську самобутність <span class="hl">Одеси</span></h1>
    <p class="hero-lead">{e(lead)}</p>
    <p class="btn-row">{btn('Підтримати', '/pidtrymaty', 'red', True)}{btn('Долучитися', '/doluchytysia', 'ghost', True)}</p>
  </div>
</section>
<div class="ticker" aria-hidden="true"><div class="ticker-track">{ticker}{ticker}</div></div>
<section class="quick" aria-label="Швидкі дії">
  <div class="wrap"><ul class="quick-list">{quick_actions()}</ul></div>
</section>
<section class="sec cream">
  <div class="wrap two about">
    <div><h2 class="h-red">Ми повертаємо Одесі правду про себе</h2><p class="lead">{e(find_text('/', 'ГО «Робимо вам нерви»'))}</p>
      <p class="btn-row">{btn('Більше про нас', '/pro-nas', 'outline')}{btn('Мовні інспекції', '/movniinspektsii', 'outline')}</p></div>
    <ul class="mosaic">{gallery}</ul>
  </div>
</section>
<section class="sec red">
  <div class="wrap two">
    <div><h2>Наші результати</h2><p class="lead">{e(find_text('/', 'За кожною нашою подією'))}</p>
      <p class="stats-note">Чотири роки діяльности, дані на {C.AS_OF}.</p>
      <p class="btn-row">{btn('Усі цифри', '/rvn-4-roky', 'cream')}</p></div>
    <ul class="stats">{stats}</ul>
  </div>
</section>
<section class="sec blue">
  <div class="wrap">
    <div class="sec-row"><h2>Блоґ</h2>{btn('Читати всі статті', '/blog', 'cream')}</div>
    <div class="cards">{''.join(card(p) for p in posts[:3])}</div>
  </div>
</section>
<section class="sec cream">
  <div class="wrap">{sec_head('Згадки про нас у медія')}<ul class="media">{media}</ul>
  {quote_block()}</div>
</section>
<section class="sec red">
  <div class="wrap">{sec_head('Наші події', 'Реальні кроки для відродження Одеси')}<ul class="events">{ev}</ul>
  <p class="center more-row">{btn('Анонси та звіти', '/podii', 'cream')}</p></div>
</section>
<section class="sec cream">
  <div class="wrap">{sec_head('Наша команда', 'Керівний склад організації')}<ul class="team">{tm}</ul></div>
</section>
<section class="sec join">
  <div class="wrap join-in">
    <div><h2>Стати частиною команди</h2><p>{e(lead)}</p></div>
    <p class="btn-row">{btn('Долучитися', '/doluchytysia', 'cream', True)}{btn('Підтримати', '/pidtrymaty', 'ghost', True)}</p>
  </div>
</section>'''
    ld = {'@context': 'https://schema.org', '@type': 'Organization', 'name': f'ГО «{BRAND}»', 'alternateName': BRAND_SHORT,
          'url': SITE + '/', 'logo': SITE + variants('logo-1-SvkvHc1uyi0uawRf.png', (160, 320), tag='logo')[-1][2],
          'email': EMAIL, 'sameAs': [u for _, _, u in SOCIALS]}
    return page('/', dump['/']['title'].split(' | ')[0], dump['/']['desc'], body, '/', ld=ld)


def build_blog():
    chips = '<button type="button" class="chip" data-cat="" aria-pressed="true">Усі <span>' + str(len(posts)) + '</span></button>' + ''.join(
        f'<button type="button" class="chip" data-cat="{cat_slug(c)}" aria-pressed="false">{e(c)} <span>{sum(p.category == c for p in posts)}</span></button>'
        for c in CATEGORIES)
    body = f'''<section class="page-head blue">
  <div class="wrap"><h1>Блоґ</h1><p class="lead">{e(dump['/blog']['desc'])}</p></div>
</section>
<section class="sec cream">
  <div class="wrap">
    <form class="blog-filters" role="search" aria-label="Пошук і рубрики блоґу" hidden>
      <div class="chips" role="group" aria-label="Рубрики">{chips}</div>
      <div class="search"><label class="sr-only" for="q">Пошук у блоґу</label>
        <input id="q" type="search" placeholder="Пошук: назва, автор, тема" autocomplete="off">
        <span class="blog-found" aria-live="polite"></span></div>
    </form>
    <div class="blog-list">
      {card(posts[0], 'h2', True, True)}
      <div class="cards">{''.join(card(p, 'h2', i < 2) for i, p in enumerate(posts[1:]))}</div>
    </div>
    <div class="blog-empty" hidden><p>Нічого не знайдено.</p><button type="button" class="btn btn-outline blog-reset">Показати всі статті</button></div>
  </div>
</section>'''
    ld = {'@context': 'https://schema.org', '@type': 'Blog', 'name': f'Блоґ {BRAND_SHORT}', 'url': SITE + '/blog',
          'blogPost': [{'@type': 'BlogPosting', 'headline': p.title, 'url': SITE + p.path, 'datePublished': p.date.isoformat()} for p in posts]}
    return page('/blog', dump['/blog']['title'].split(' | ')[0], dump['/blog']['desc'], body, '/blog', ld=ld)


def build_inspections():
    P = '/movniinspektsii'
    d = dump[P]
    complaint = find_btn(P, 'Лишити скаргу')
    signs = [fname(it['src']) for it in d['secs'][1]['items'] if it['k'] == 'img' and it['rect'][2] < 400]
    pairs = ''
    for i, (a, b) in enumerate(SIGNS_ALT):
        f1, f2 = signs[2 * i], signs[2 * i + 1]
        pairs += f'''<li class="pair">
<figure>{img_tag(f1, a, "(min-width: 1100px) 190px, (min-width: 900px) 15vw, 45vw", (320, 640), (1, 1), "sq")}<figcaption>До</figcaption></figure>
<figure>{img_tag(f2, b, "(min-width: 1100px) 190px, (min-width: 900px) 15vw, 45vw", (320, 640), (1, 1), "sq")}<figcaption>Після</figcaption></figure></li>'''
    body = f'''<section class="sec cream">
  <div class="wrap two">
    <div><h1>Що таке мовні інспекції?</h1><p class="lead">{e(find_text(P, 'Це практичний інструмент'))}</p>
    <p class="btn-row">{btn('Лишити скаргу', complaint, 'red', True)}</p></div>
    <div>{img_tag('img_1277-yhkHU7G2y0zBqokl.jpg', 'Учасники мовних інспекцій РВН', '(min-width: 900px) 560px, calc(100vw - 48px)', (560, 1120), (9, 8), 'in', True, 'round')}</div>
  </div>
</section>
<section class="sec paper">
  <div class="wrap">
    {sec_head('Наші результати: до і після', find_text(P, 'За кожною зміненою вивіскою'))}
    <ul class="pairs">{pairs}</ul>
    <p class="center lead lead-c">{e(find_text(P, 'Ми не чекаємо'))}</p>
  </div>
</section>
<section class="sec red">
  <div class="wrap">{sec_head('Інспекції в цифрах', 'Дані на ' + C.AS_OF)}{numbers([('170', 'закритих порушень мовного законодавства'), ('130', 'скарг в опрацюванні')], 'numbers numbers-2')}
  <p class="center more-row"><a class="btn btn-cream" href="{C.INSPECTIONS_IG}" rel="noopener" target="_blank">{icon('instagram', 18)}<span>Інспекції в Instagram</span></a></p></div>
</section>
<section class="sec cream" id="povidomyty">
  <div class="wrap">{sec_head('Бачите порушення? Ось що робити')}
  <div class="two report">
    <div><h3>Що є порушенням</h3><p>Закон № 2704-VIII «Про забезпечення функціонування української мови як державної» порушують, зокрема:</p>{checks(C.REPORT_WHAT)}</div>
    <div><h3>Алгоритм дій</h3>{steps(C.REPORT_STEPS)}<p class="more-link"><a href="/yak-zakhystyty-movni-prava">Детальна інструкція: як захистити свої мовні права</a></p></div>
  </div>
  <p class="center more-row">{btn('Лишити скаргу', complaint, 'red', True)}</p></div>
</section>
<section class="sec paper">
  <div class="wrap">{sec_head('Мапа змін', 'Тут мапа, де показані змінені порушники.')}
  <div class="map"><iframe src="{MAP_SRC}" title="Мапа змін: заклади, що виправили мовні порушення" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe></div></div>
</section>'''
    return page(P, d['title'].split(' | ')[0], d['desc'], body, P)


def build_events():
    P = '/podii'
    d = dump[P]
    btns = [it['href'] for it in d['secs'][1]['items'] if it['k'] == 'btn']
    strokata = next(p for p in posts if p.old == '/blog-post')
    body = f'''<section class="page-head red">
  <div class="wrap"><h1>Анонси та звіти наших подій</h1><p class="lead">Доєднуйтеся до збереження культурної спадщини міста.</p></div>
</section>
<section class="sec cream">
  <div class="wrap">
    <article class="feature">
      <div class="feature-media">{img_tag('img_8484-pTXwCwYnHnGxQZ6J.jpg', 'Учасники заходу до 125-річчя Юрія Липи', '(min-width: 900px) 620px, calc(100vw - 48px)', (620, 1240), (3, 2), 'e', True, 'round')}</div>
      <div><h2>125-річчя Юрія Липи</h2><p>{e(find_text(P, 'Зануртеся у святкування'))}</p><p class="btn-row">{btn('Переглянути світлини', btns[0], 'dark')}</p></div>
    </article>
    <article class="feature feature-rev">
      <div class="feature-media">{img_tag('dsc00311-kTYzpHSNwKUNJQh4.JPG', 'Учасники майстер-клясу на Коцюбіїв-фесті', '(min-width: 900px) 620px, calc(100vw - 48px)', (620, 1240), (3, 2), 'e', False, 'round')}</div>
      <div><h2>Коцюбіїв-фест</h2><p>{e(find_text(P, 'Разом із вами відзначили'))}</p><p class="btn-row">{btn('Переглянути світлини', btns[1], 'dark')}</p></div>
    </article>
  </div>
</section>
<section class="sec paper">
  <div class="wrap">{sec_head('Архів подій', 'Що ми встигли зробити останнім часом')}{archive()}</div>
</section>
<section class="sec cream" id="kalendar">
  <div class="wrap">{sec_head('Календар пам’яти', 'Дати, які ми відзначаємо щороку. Найближча — першою.')}{memory_calendar()}</div>
</section>
<section class="sec cream">
  <div class="wrap">{sec_head('Звіти в блоґу')}{card(strokata, 'h3', False, True)}</div>
</section>'''
    return page(P, d['title'].split(' | ')[0], d['desc'], body, P)


def build_contacts():
    P = '/contacts'
    d = dump[P]
    gal = [it for it in d['secs'][2]['items'] if it['k'] == 'img']
    g = ''.join(f'<li>{img_tag(fname(it["src"]), it["alt"], ("(min-width: 900px) 800px, calc(100vw - 48px)" if n == 0 else "(min-width: 900px) 400px, calc(100vw - 48px)"), (480, 800, 1200) if n == 0 else (480, 800), (4, 3), "g")}</li>' for n, it in enumerate(gal))
    actions = [
        ('users', 'Вступити до ГО', 'Анкета для волонтерів і членів організації.', 'Заповнити анкету', find_btn('/', 'Вступити в ГО')),
        ('flag', 'Повідомити про мовне порушення', 'Форма скарги для мовних інспекцій.', 'Лишити скаргу', find_btn('/movniinspektsii', 'Лишити скаргу')),
        ('mail', 'Написати нам', 'Партнерство, медія та инші питання.', 'Написати листа', f'mailto:{EMAIL}'),
        ('heart', 'Підтримати фінансово', 'Збір на банку monobank.', 'Підтримати', JAR),
    ]
    act = ''.join(f'''<li class="action"><span class="action-ico">{icon(k, 26)}</span>
<h3><a href="{e(h)}"{' rel="noopener" target="_blank"' if h.startswith('http') else ''}>{e(t)}</a></h3><p>{e(s)}</p>{arrow_link(c)}</li>''' for k, t, s, c, h in actions)
    body = f'''<section class="page-head blue">
  <div class="wrap two">
    <div><h1>Зв'язатися з нами можна через соцмережі або пошту</h1>
      <p class="contact-mail"><a href="mailto:{EMAIL}">{icon('mail', 22)}<span>{EMAIL}</span></a><button type="button" class="btn btn-sm btn-ghost" data-copy="{EMAIL}" data-copied="Адресу скопійовано" hidden>Копіювати</button></p>
      {socials('socials socials-big', 24)}</div>
    <div>{img_tag('img_7422-piJbir4VzWCvmra6.jpg', 'Учасники зустрічі РВН під час обговорення', '(min-width: 900px) 560px, calc(100vw - 48px)', (560, 1120), (3, 2), 'c', True, 'round')}</div>
  </div>
</section>
<section class="sec cream">
  <div class="wrap">{sec_head('Як долучитися')}<ul class="actions">{act}</ul>
  <p class="center note">Маєте питання? Можливо, відповідь уже є в <a href="/pytannia">частих питаннях</a>. Журналістам — <a href="/dlia-media">сторінка для медія</a>.</p></div>
</section>
<section class="sec paper">
  <div class="wrap">{sec_head('Збірка світлин', 'Моменти, що відображають дух нашої Одеси')}<ul class="photo-grid">{g}</ul></div>
</section>'''
    ld = {'@context': 'https://schema.org', '@type': 'ContactPage', 'url': SITE + P,
          'mainEntity': {'@type': 'Organization', 'name': f'ГО «{BRAND}»', 'email': EMAIL, 'sameAs': [u for _, _, u in SOCIALS]}}
    return page(P, d['title'].split(' | ')[0], d['desc'], body, P, ld=ld)


def build_post(p):
    if p.html:
        out, words = news_html(p)
        return render_post(p, out, '', words)
    out = []
    first_img = True
    i = 0
    items = p.items
    cta = ''
    words = 0
    while i < len(items):
        it = items[i]
        if it['k'] == 't':
            text = run_text(it)
            words += len(text.split())
            is_heading = it['tag'].startswith('h') and len(text) <= 110 and it['fs'] >= 20
            if is_heading:
                out.append(f'<h2>{e(text.rstrip("."))}</h2>')
            else:
                out += [f'<p>{h}</p>' for h in runs_html(it['runs'])]
            i += 1
        elif it['k'] == 'img':
            row = [it]
            while i + 1 < len(items) and items[i + 1]['k'] == 'img' and abs(items[i + 1]['rect'][1] - it['rect'][1]) < 90:
                i += 1; row.append(items[i])
            figs = ''
            for r in row:
                f = fname(r['src'])
                is_doc = bool(re.search(r'звернення|відповід|перелік|допис|документ', r['alt'].lower()))
                sizes = '(min-width: 900px) 860px, calc(100vw - 48px)' if len(row) == 1 else '(min-width: 900px) 420px, calc(100vw - 48px)'
                figs += f'<figure>{img_tag(f, r["alt"], sizes, (480, 860, 1280) if not is_doc else (768, 1600), None, "doc" if is_doc else "", first_img)}</figure>'
                first_img = False
            out.append(f'<div class="figs figs-{min(len(row), 2)}">{figs}</div>')
            i += 1
        else:
            if url(it['href']) != '/blog':      # на список статей уже ведуть «Усі статті» нижче
                cta = btn(it['text'], url(it['href']), 'blue', True)
            i += 1
    return render_post(p, out, cta, words)


def add_toc(out):
    """Дає розділам (h2) якорі; для статей із трьома й більше розділами додає зміст."""
    heads, res = [], []
    for block in out:
        m = re.match(r'<h2>(.*?)</h2>$', block)
        if m:
            text = re.sub('<[^>]+>', '', m.group(1))
            hid = f'rozdil-{len(heads) + 1}'
            heads.append((hid, text))
            block = f'<h2 id="{hid}">{m.group(1)}</h2>'
        res.append(block)
    if len(heads) < 3:
        return res, ''
    items = ''.join(f'<li><a href="#{h}">{t}</a></li>' for h, t in heads)
    return res, f'<nav class="toc" aria-label="Зміст статті"><details open><summary>Зміст</summary><ol>{items}</ol></details></nav>'


def share_html(p):
    from urllib.parse import quote
    u = SITE + p.path
    tg = f'https://t.me/share/url?url={quote(u, safe="")}&text={quote(p.title, safe="")}'
    fb = f'https://www.facebook.com/sharer/sharer.php?u={quote(u, safe="")}'
    return (f'<div class="share"><p class="share-h">Поділитися</p><div class="share-row">'
            f'<a class="share-btn" href="{e(tg)}" rel="noopener" target="_blank">{icon("telegram", 18)}<span>Telegram</span></a>'
            f'<a class="share-btn" href="{e(fb)}" rel="noopener" target="_blank">{icon("facebook", 18)}<span>Facebook</span></a>'
            f'<button type="button" class="share-btn" data-copy="{u}" data-copied="Посилання скопійовано" hidden>{icon("link", 18)}<span>Копіювати посилання</span></button>'
            f'<button type="button" class="share-btn" data-share="{u}" hidden>{icon("share", 18)}<span>Инші застосунки</span></button>'
            '</div></div>')


def quick_actions():
    items = [
        ('flag', 'Бачите мовне порушення?', 'Що робити й куди скаржитися', '/movniinspektsii#povidomyty'),
        ('users', 'Хочете в команду?', 'Інспекції, медія, архіви, події', '/doluchytysia'),
        ('heart', 'Підтримати РВН', 'Підписка на Монобазі або банка', '/pidtrymaty'),
    ]
    return ''.join(f'<li class="quick-item"><span class="quick-ico">{icon(k, 24)}</span><span class="quick-text">'
                   f'<a href="{h}">{e(t)}</a><span>{e(d)}</span></span>{icon("arrow", 20)}</li>' for k, t, d, h in items)


def render_post(p, out, cta, words):
    mins = max(1, round(words / 200))
    idx = posts.index(p)
    older = posts[idx + 1] if idx + 1 < len(posts) else None
    newer = posts[idx - 1] if idx > 0 else None
    nav = ''
    if older:
        nav += f'<a class="prev" href="{older.path}" rel="prev"><span>{icon("arrow-l", 16)}Попередня стаття</span><strong>{e(older.title)}</strong></a>'
    if newer:
        nav += f'<a class="next" href="{newer.path}" rel="next"><span>Наступна стаття{icon("arrow", 16)}</span><strong>{e(newer.title)}</strong></a>'
    same = [o for o in posts if o is not p and p.category and o.category == p.category]
    others = (same + [o for o in posts if o is not p and o not in same])[:3]
    out, toc = add_toc(out)
    share = share_html(p)
    cover = SITE + variants(p.cover, (1200,), (1200, 630), 'og')[0][2] if p.cover else None
    cat = (f'<a class="pill" href="/blog?rubryka={cat_slug(p.category)}">{e(p.category)}</a>') if p.category else ''
    initials = ''.join(w[0] for w in p.author.split(',')[0].split()[:2]).upper()
    if p.author == 'Команда РВН':
        lg = variants('logo-1-SvkvHc1uyi0uawRf.png', (160, 320), tag='logo')
        avatar = f'<span class="avatar avatar-logo" aria-hidden="true"><img src="{lg[0][2]}" width="44" height="45" alt=""></span>'
    else:
        avatar = f'<span class="avatar" aria-hidden="true">{e(initials)}</span>'
    crumbs_ld = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Головна', 'item': SITE + '/'},
        {'@type': 'ListItem', 'position': 2, 'name': 'Блоґ', 'item': SITE + '/blog'},
        {'@type': 'ListItem', 'position': 3, 'name': p.title, 'item': SITE + p.path}]}
    body = f'''<div class="read-progress" aria-hidden="true"></div>
<article class="post">
  <header class="post-head">
    <div class="post-wrap">
      <nav class="crumbs" aria-label="Навігаційний ланцюжок"><ol><li><a href="/">Головна</a></li><li><a href="/blog">Блоґ</a></li><li aria-current="page"><span>{e(p.title)}</span></li></ol></nav>
      {cat}
      <h1>{e(p.title)}</h1>
      <p class="post-desc">{e(p.desc)}</p>
      <p class="post-meta">{avatar}<span><strong>{e(p.author)}</strong><br><time datetime="{p.date.isoformat()}">{uk_date(p.date)}</time> · {mins} хв читання</span></p>
    </div>
  </header>
  <div class="post-body">
{toc}
{chr(10).join(out)}
  {f'<p class="center post-cta">{cta}</p>' if cta else ''}
  {share}
  </div>
</article>
<nav class="post-nav" aria-label="Сусідні статті">{nav}</nav>
<section class="sec paper">
  <div class="wrap"><div class="sec-row"><h2>Читайте також</h2>{btn('Усі статті', '/blog', 'outline')}</div><div class="cards">{''.join(card(o) for o in others)}</div></div>
</section>
<script type="application/ld+json">{json.dumps(crumbs_ld, ensure_ascii=False)}</script>'''
    ld = {'@context': 'https://schema.org', '@type': 'Article', 'headline': p.title, 'description': p.desc,
          'datePublished': p.date.isoformat(), 'inLanguage': 'uk',
          'author': [{'@type': 'Person', 'name': a.strip()} for a in p.author.split(',')],
          'publisher': {'@type': 'Organization', 'name': f'ГО «{BRAND}»', 'url': SITE + '/'},
          'mainEntityOfPage': SITE + p.path}
    if cover:
        ld['image'] = cover
    return page(p.path, p.title, p.meta_desc or p.desc, body, '/blog', og=cover[len(SITE):] if cover else None, ld=ld)


TEAM = [
    ('img_8986-IHzOMfyrKGO0fRLg.jpg', 'Микола Тарасенко', 'Голова організації'),
    ('img_8928-8IXl5odSyTRFSkba.jpg', 'Катерина Мусієнко', 'Голова відділу Опори'),
    ('img_8866-XwwnDAjaeyPdY9Ls.jpg', 'Карина Серт', 'Голова відділу Спільноти'),
    ('img_8961-ivWdDINjWKw2Zwm2.jpg', 'Василина Гушевська', 'Голова відділу Ідеї'),
    ('photo_2026-10-23_14-29-36-Tb5Qqycg9hPAsMBj.jpg', 'Ніка Умарова', 'Голова відділу Дії'),
]


def team_html():
    alts = {fname(it['src']): it['alt'] for s in dump['/']['secs'] for it in s['items'] if it['k'] == 'img'}
    return ''.join(f'''<li class="member">{img_tag(f, alts[f], "(min-width: 1100px) 220px, (min-width: 640px) 30vw, 45vw", (240, 480), (3, 4), "p4")}
<p class="member-name">{e(n)}</p><p class="member-role">{e(r)}</p></li>''' for f, n, r in TEAM)


def quote_block():
    return f'''<figure class="quote">
  <blockquote><p>«{e(C.QUOTE)}»</p></blockquote>
  <figcaption><strong>{e(C.QUOTE_AUTHOR)}</strong>, {e(C.QUOTE_ROLE)}<br><a href="/podiaka-upovnovazhenoi">Подяка від Уповноваженої із захисту державної мови</a></figcaption>
</figure>'''


def numbers(items, cls='numbers'):
    return f'<ul class="{cls}">' + ''.join(f'<li><p class="num">{e(n)}</p><p class="num-label">{e(l)}</p></li>' for n, l in items) + '</ul>'


def action_cards(items, cls='actions'):
    """items: (icon, title, text[, link_text, href]) — без href картка без посилання."""
    out = ''
    for k, t, s_, *rest in items:
        c, h = (list(rest) + [None, None])[:2]
        if h:
            ext = ' rel="noopener" target="_blank"' if h.startswith('http') else ''
            title = f'<h3><a href="{e(h)}"{ext}>{e(t)}</a></h3>'
            more = arrow_link(c)
        else:
            title, more = f'<h3>{e(t)}</h3>', ''
        out += f'<li class="action"><span class="action-ico">{icon(k, 26)}</span>{title}<p>{e(s_)}</p>{more}</li>'
    return f'<ul class="{cls}">{out}</ul>'


def steps(items):
    return '<ol class="steps">' + ''.join(f'<li><h3>{e(t)}</h3><p>{e(d)}</p></li>' for t, d in items) + '</ol>'


def checks(items):
    return '<ul class="checks">' + ''.join(f'<li>{e(x)}</li>' for x in items) + '</ul>'


def join_band(title='Стати частиною команди', text=None):
    text = text or find_text('/', 'Долучайтеся до підтримки')
    return f'''<section class="sec join">
  <div class="wrap join-in">
    <div><h2>{e(title)}</h2><p>{e(text)}</p></div>
    <p class="btn-row">{btn('Долучитися', '/doluchytysia', 'cream', True)}{btn('Підтримати', '/pidtrymaty', 'ghost', True)}</p>
  </div>
</section>'''


def build_about():
    P = '/pro-nas'
    dirs = [(k, t, s_, 'Детальніше', h) for k, t, s_, h in C.DIRECTIONS]
    tl = ''.join(f'<li><p class="tl-date">{e(d)}</p><p>{e(t)}</p></li>' for d, t in C.MILESTONES)
    about = ''.join(f'<p class="lead">{e(t)}</p>' if i == 0 else f'<p>{e(t)}</p>' for i, t in enumerate(C.ABOUT_TEXT))
    body = f'''<section class="page-head red">
  <div class="wrap"><h1>Про нас</h1><p class="lead">{e(C.ABOUT_LEAD)}</p></div>
</section>
<section class="sec cream">
  <div class="wrap two">
    <div class="prose"><h2 class="h-red">У чому унікальність РВН</h2>{about}</div>
    <div>{img_tag('drive/2025-11-09-richnytsia-1.jpg', 'Команда РВН на святкуванні третьої річниці організації', '(min-width: 900px) 560px, calc(100vw - 48px)', (560, 1120), (4, 3), 'ab', True, 'round')}</div>
  </div>
</section>
<section class="sec paper">
  <div class="wrap">{sec_head('Що ми робимо')}{action_cards(dirs)}</div>
</section>
<section class="sec red">
  <div class="wrap">{sec_head('Чотири роки в цифрах', 'Дані на ' + C.AS_OF)}{numbers(C.NUMBERS)}
  <p class="center more-row">{btn('Докладніше про чотири роки', '/rvn-4-roky', 'cream')}</p></div>
</section>
<section class="sec cream">
  <div class="wrap two">
    <div><h2 class="h-red">Важливі дати</h2><ol class="timeline">{tl}</ol></div>
    <div>{quote_block()}</div>
  </div>
</section>
<section class="sec paper">
  <div class="wrap">{sec_head('Наша команда', 'Керівний склад організації')}<ul class="team">{team_html()}</ul></div>
</section>
{join_band()}'''
    ld = {'@context': 'https://schema.org', '@type': 'AboutPage', 'url': SITE + P,
          'mainEntity': {'@type': 'Organization', 'name': f'ГО «{BRAND}»', 'foundingDate': C.FOUNDED.isoformat(),
                         'url': SITE + '/', 'email': EMAIL, 'sameAs': [u for _, _, u in SOCIALS]}}
    return page(P, 'Про нас', 'ГО «Робимо вам нерви» з листопада 2022 року українізує й демосковізує Одесу: мовні інспекції, акції, події, історія міста. Хто ми, що робимо й чого досягли.', body, P, ld=ld)


def build_join():
    P = '/doluchytysia'
    form = find_btn('/', 'Вступити в ГО')
    body = f'''<section class="page-head blue">
  <div class="wrap two">
    <div><h1>Долучитися до РВН</h1><p class="lead">{e(C.JOIN_LEAD)}</p>
      <p class="btn-row">{btn('Заповнити анкету', form, 'cream', True)}</p></div>
    <div>{img_tag('drive/2026-01-25-movni-ihry-2.jpg', 'Учасники мовних ігор РВН за столом', '(min-width: 900px) 560px, calc(100vw - 48px)', (560, 1120), (3, 2), 'jn', True, 'round')}</div>
  </div>
</section>
<section class="sec cream">
  <div class="wrap">{sec_head('Чим можна займатися', 'Обирай напрям, що тобі ближчий')}{action_cards(C.JOIN_ROLES)}</div>
</section>
<section class="sec paper">
  <div class="wrap two">
    <div><h2 class="h-red">Що ти отримаєш</h2>{checks(C.JOIN_GAINS)}</div>
    <div>{img_tag('drive/2025-10-01-khoda-1.jpg', 'Учасники вечірньої ходи РВН з прапорами', '(min-width: 900px) 560px, calc(100vw - 48px)', (560, 1120), (3, 2), 'jn', False, 'round')}</div>
  </div>
</section>
<section class="sec cream">
  <div class="wrap">{sec_head('Як вступити')}{steps(C.JOIN_STEPS)}
  <p class="center note">{e(C.JOIN_MINORS)}</p>
  <p class="center more-row">{btn('Заповнити анкету', form, 'red', True)}</p>
  <p class="center note">Ще не готові вступати? <a href="/movniinspektsii#povidomyty">Повідомте про мовне порушення</a> або <a href="/pidtrymaty">підтримайте нас</a>.</p></div>
</section>'''
    return page(P, 'Долучитися до команди', 'Як стати волонтером ГО «Робимо вам нерви»: мовні інспекції, медія, архіви, події. Анкета на вступ і кроки для новачків.', body, P)


def build_support():
    P = '/pidtrymaty'
    links = {'DONATE': DONATE, 'JAR': JAR}
    opts = [(k, t, s_, c, links.get(h, h)) for k, t, s_, c, h in C.SUPPORT_OPTIONS]
    body = f'''<section class="page-head red">
  <div class="wrap"><h1>Підтримати РВН</h1><p class="lead">{e(C.SUPPORT_LEAD)}</p>
  <p class="btn-row">{btn('Оформити підписку', DONATE, 'cream', True)}{btn('Поповнити банку', JAR, 'ghost', True)}</p></div>
</section>
<section class="sec cream">
  <div class="wrap">{sec_head('Як можна допомогти')}{action_cards(opts, 'actions actions-3')}</div>
</section>
<section class="sec paper">
  <div class="wrap">{sec_head('Прозорість', 'Чотири роки діяльности, дані на ' + C.AS_OF)}{numbers(C.SUPPORT_FACTS, 'numbers numbers-' + str(len(C.SUPPORT_FACTS)))}
  <p class="center lead lead-c">Звіти про нашу діяльність ми публікуємо в <a href="{C.INSTAGRAM}" rel="noopener" target="_blank">Instagram</a>, у розділі «Звіти».</p></div>
</section>'''
    return page(P, 'Підтримати', 'Як підтримати ГО «Робимо вам нерви»: щомісячна підписка на Монобазі, разовий внесок на банку monobank або участь у команді.', body, P)


def archive():
    out = ''
    years = sorted({ev[0][:4] for ev in C.EVENTS}, reverse=True)
    for y in years:
        lis = ''
        for ev in sorted((ev for ev in C.EVENTS if ev[0][:4] == y), reverse=True):
            key, shown, title, text, photo, alt, *link = ev
            h = f'<a href="{link[0]}">{e(title)}</a>' if link else e(title)
            lis += f'''<li class="arch{' arch-link' if link else ''}">{img_tag(photo, alt, "(min-width: 1100px) 280px, (min-width: 640px) 45vw, calc(100vw - 48px)", (320, 640), (4, 3), "ar")}
<div class="arch-body"><p class="arch-date">{e(shown)}</p><h4>{h}</h4><p>{e(text)}</p></div></li>'''
        out += f'<h3 class="year">{y}</h3><ul class="archive">{lis}</ul>'
    return out



def build_faq():
    P = '/pytannia'
    items = ''.join(f'<details class="faq-item"{" open" if i == 0 else ""}><summary><h2>{e(q)}</h2></summary><div class="faq-a"><p>{a}</p></div></details>'
                    for i, (q, a) in enumerate(C.FAQ))
    body = f"""<section class="page-head blue">
  <div class="wrap"><h1>Часті питання</h1><p class="lead">Коротко про РВН, мовні інспекції, вступ до команди й підтримку.</p></div>
</section>
<section class="sec cream">
  <div class="wrap faq">{items}
  <div class="faq-more"><p><strong>Не знайшли відповіді?</strong> Напишіть нам — відповімо.</p>
  <p class="btn-row">{btn('Написати листа', 'mailto:' + EMAIL, 'red')}{btn('Контакти', '/contacts', 'outline')}</p></div></div>
</section>"""
    ld = {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
        {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': re.sub('<[^>]+>', '', a)}} for q, a in C.FAQ]}
    return page(P, 'Часті питання', 'Відповіді на часті питання про ГО «Робимо вам нерви»: мовні інспекції, скарги, вступ до команди, підтримка й звіти.', body, P, ld=ld)


def build_press():
    P = '/dlia-media'
    logo_png = '/media/rvn-logo.png'
    facts = ''.join(f'<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in C.PRESS_FACTS)
    d = dump['/']['secs'][6]['items']
    titles = sorted([it for it in d if it['k'] == 't' and it['tag'] == 'h3'], key=lambda it: it['rect'][0])
    links = sorted([it for it in d if it['k'] == 'btn'], key=lambda it: it['rect'][0])
    def host(u):
        return re.sub(r'^https?://(www\.)?', '', u).split('/')[0]
    mentions = ''.join(f'<li><a href="{e(b["href"])}" rel="noopener" target="_blank">{e(run_text(t))}</a><span>{e(host(b["href"]))}</span></li>'
                       for t, b in zip(titles, links))
    mentions += '<li><a href="/podiaka-upovnovazhenoi">Подяка від Уповноваженої із захисту державної мови</a><span>жовтень 2026</span></li>'
    def copyblock(title, text):
        return (f'<div class="press-text"><div class="press-text-head"><h3>{e(title)}</h3>'
                f'<button type="button" class="btn btn-sm btn-outline" data-copy="{e(text)}" data-copied="Текст скопійовано" hidden>Копіювати</button></div>'
                f'<p>{e(text)}</p></div>')
    body = f"""<section class="page-head red">
  <div class="wrap"><h1>Для медія</h1><p class="lead">Довідка про організацію, логотип, ключові цифри й контакти для журналістів.</p>
  <p class="btn-row">{btn('Написати нам', 'mailto:' + EMAIL, 'cream', True)}</p></div>
</section>
<section class="sec cream">
  <div class="wrap two press-top">
    <div><h2 class="h-red">Про організацію</h2>{copyblock('Одним реченням', C.PRESS_SHORT)}{copyblock('Розгорнуто', C.PRESS_LONG)}</div>
    <div><h2 class="h-red">Ключові факти</h2><dl class="facts">{facts}</dl>
      <div class="logo-card"><img src="{logo_png}" width="160" height="163" alt="Логотип ГО «Робимо вам нерви»" loading="lazy">
      <div><h3>Логотип</h3><p>PNG з прозорим тлом.</p><a class="btn btn-sm btn-dark" href="{logo_png}" download="rvn-logo.png">Завантажити</a></div></div>
    </div>
  </div>
</section>
<section class="sec red">
  <div class="wrap">{sec_head('Цифри', 'Чотири роки діяльности, дані на ' + C.AS_OF)}{numbers(C.NUMBERS)}</div>
</section>
<section class="sec paper">
  <div class="wrap two">
    <div><h2 class="h-red">Про нас у медія</h2><ul class="mentions">{mentions}</ul></div>
    <div><h2 class="h-red">Контакти для медія</h2>
      <p class="contact-mail light"><a href="mailto:{EMAIL}">{icon('mail', 22)}<span>{EMAIL}</span></a></p>
      <p>Коментарі, інтерв’ю, світлини з подій — пишіть на пошту або в соцмережі.</p>{socials('socials socials-dark', 22)}</div>
  </div>
</section>"""
    return page(P, 'Для медія', 'Медіякит ГО «Робимо вам нерви»: коротка довідка про організацію, ключові факти й цифри, логотип і контакти для журналістів.', body, P)


def memory_calendar():
    today = datetime.date.today()
    def nxt(m, d):
        y = today.year if (m, d) >= (today.month, today.day) else today.year + 1
        return datetime.date(y, m, d)
    items = sorted(C.MEMORY_DATES, key=lambda x: nxt(x[0], x[1]))
    lis = ''
    for i, (m, d, t, desc, link) in enumerate(items):
        title = f'<a href="{link}">{e(t)}</a>' if link else e(t)
        soon = ' mem-next' if i == 0 else ''
        badge = '<span class="mem-badge">Найближча</span>' if i == 0 else ''
        lis += (f'<li class="mem{soon}" data-md="{m:02d}-{d:02d}"><p class="mem-date"><span class="mem-d">{d}</span><span class="mem-m">{MONTHS[m - 1]}</span></p>'
                f'<div class="mem-body">{badge}<h3>{title}</h3>{f"<p>{e(desc)}</p>" if desc else ""}</div></li>')
    return f'<ol class="memory">{lis}</ol>'


def build_privacy():
    lines = (SRC / 'policy.txt').read_text(encoding='utf-8').splitlines()
    out, table, lst = [], [], []

    def flush():
        nonlocal table, lst
        if table:
            head, *rows = table
            out.append('<div class="table-wrap"><table><thead><tr>' + ''.join(f'<th scope="col">{e(c)}</th>' for c in head) + '</tr></thead><tbody>' +
                       ''.join('<tr>' + ''.join(f'<td>{e(c)}</td>' for c in r) + '</tr>' for r in rows) + '</tbody></table></div>')
            table = []
        if lst:
            out.append('<ul>' + ''.join(f'<li>{e(x)}</li>' for x in lst) + '</ul>'); lst = []

    for ln in lines:
        ln = ln.replace('сайт «Відлуння»', 'сайт rvn.com.ua')
        if ln.startswith('===='):
            continue
        if ln.startswith('| '):
            if lst: flush()
            table.append([c.strip() for c in ln.strip('|').split('|')]); continue
        if ln.startswith('- '):
            if table: flush()
            lst.append(ln[2:].strip()); continue
        flush()
        if ln.startswith('## '):
            out.append(f'<h2>{e(ln[3:])}</h2>')
        elif ln.startswith('# '):
            out.append(f'<h1>{e(ln[2:].replace("конфіденційності", "конфіденційности"))}</h1>')
        elif re.match(r'^[A-Z][a-z]{2} \d', ln):
            continue
        elif ln.strip():
            t = e(ln)
            t = t.replace(EMAIL, f'<a href="mailto:{EMAIL}">{EMAIL}</a>')
            out.append(f'<p>{t}</p>')
    flush()
    body = f'<article class="post"><div class="post-body doc">{chr(10).join(out)}</div></article>'
    return page('/privacy', 'Політика конфіденційности',
                'Як ГО «Робимо вам нерви» збирає, використовує та захищає персональні дані відвідувачів сайту, волонтерів і донаторів.',
                body)


def build_404():
    body = f'''<section class="sec cream nf"><div class="wrap center">
<p class="nf-code">404</p><h1>Такої сторінки немає</h1>
<p class="lead">Можливо, адресу змінено або в ній одруківка. Спробуйте почати з одного з розділів:</p>
<p class="btn-row center">{btn('На головну', '/', 'red')}{btn('Блоґ', '/blog', 'blue')}{btn('Контакти', '/contacts', 'dark')}</p>
</div></section>'''
    return page('/404', 'Сторінку не знайдено', 'Сторінку не знайдено. Перейдіть на головну, у блоґ або на сторінку контактів.', body, noindex=True)


# ---------------------------------------------------------------- збирання
def with_base(html_text):
    """Додає префікс підтеки до внутрішніх адрес (href, src, poster, srcset)."""
    if not BASE:
        return html_text
    html_text = re.sub(r'((?:href|src|poster)=")/(?!/)', rf'\1{BASE}/', html_text)
    return re.sub(r'srcset="([^"]+)"', lambda m: 'srcset="' + re.sub(r'(^|,\s*)/(?!/)', rf'\1{BASE}/', m.group(1)) + '"', html_text)


def write(path, content):
    content = with_base(content)
    f = DIST / ('index.html' if path == '/' else path.lstrip('/') + '.html')
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding='utf-8', newline='\n')


def main():
    DIST.mkdir(exist_ok=True)
    IMG_OUT.mkdir(exist_ok=True)
    for f in DIST.glob('*.html'):
        f.unlink()
    shutil.copy(ROOT / 'style.css', DIST / 'style.css')
    shutil.copy(ROOT / 'site.js', DIST / 'site.js')
    (DIST / 'media').mkdir(exist_ok=True)
    for v in (SRC / 'instagram' / 'video').glob('*.mp4'):
        if not (DIST / 'media' / v.name).exists():
            shutil.copy(v, DIST / 'media' / v.name)
    fav = _open('logo-1-SvkvHc1uyi0uawRf.png'); fav.thumbnail((96, 96)); fav.save(IMG_OUT / 'favicon.png')
    logo = _open('logo-1-SvkvHc1uyi0uawRf.png').convert('RGBA')
    (DIST / 'media').mkdir(exist_ok=True)
    logo.save(DIST / 'media' / 'rvn-logo.png')
    for size, name in ((180, 'apple-touch-icon.png'), (192, 'icon-192.png'), (512, 'icon-512.png')):
        bg = Image.new('RGBA', (size, size), (252, 240, 224, 255))
        lg = logo.copy(); lg.thumbnail((int(size * .78), int(size * .78)), Image.LANCZOS)
        bg.alpha_composite(lg, ((size - lg.width) // 2, (size - lg.height) // 2))
        bg.convert('RGB').save(IMG_OUT / name)
    start = (BASE or '') + '/'
    (DIST / 'site.webmanifest').write_text(json.dumps({
        'name': f'ГО «{BRAND}»', 'short_name': BRAND_SHORT, 'lang': 'uk', 'start_url': start, 'scope': start,
        'display': 'standalone', 'background_color': '#fcf0e0', 'theme_color': '#dd2923',
        'icons': [{'src': f'{BASE}/img/icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
                  {'src': f'{BASE}/img/icon-512.png', 'sizes': '512x512', 'type': 'image/png'}]}, ensure_ascii=False), encoding='utf-8')
    pages = {'/': build_home(), '/blog': build_blog(), '/movniinspektsii': build_inspections(),
             '/podii': build_events(), '/contacts': build_contacts(), '/pro-nas': build_about(),
             '/doluchytysia': build_join(), '/pidtrymaty': build_support(), '/pytannia': build_faq(),
             '/dlia-media': build_press(), '/privacy': build_privacy()}
    for p in posts:
        pages[p.path] = build_post(p)
    for path, content in pages.items():
        write(path, content)
    write('/404', build_404())
    today = datetime.date.today().isoformat()
    lastmod = {p.path: p.date.isoformat() for p in posts}
    sm = ''.join(f'<url><loc>{SITE}{"/" if k == "/" else k}</loc><lastmod>{lastmod.get(k, today)}</lastmod></url>\n' for k in pages)
    (DIST / 'sitemap.xml').write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{sm}</urlset>\n', encoding='utf-8')
    items = ''.join(
        f"<item><title>{e(p.title)}</title><link>{SITE}{p.path}</link><guid>{SITE}{p.path}</guid>"
        f"<pubDate>{datetime.datetime(p.date.year, p.date.month, p.date.day, 12).strftime('%a, %d %b %Y %H:%M:%S +0200')}</pubDate>"
        f"<description>{e(p.desc)}</description></item>\n" for p in posts)
    (DIST / 'rss.xml').write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Блоґ {BRAND_SHORT}</title><link>{SITE}/blog</link>
<description>Статті й новини ГО «{BRAND}» про українську Одесу</description><language>uk</language>
{items}</channel></rss>
''', encoding='utf-8')
    if BASE:      # GitHub Pages не знає 301 — старі адреси статей перенаправляє HTML-сторінка
        for o, n in RENAMES.items():
            (DIST / (o.lstrip('/') + '.html')).write_text(
                f'<!doctype html><meta charset="utf-8"><title>Сторінку перенесено</title><meta name="robots" content="noindex">'
                f'<link rel="canonical" href="{SITE}{n}"><meta http-equiv="refresh" content="0; url={BASE}{n}">'
                f'<p>Сторінку перенесено: <a href="{BASE}{n}">{BASE}{n}</a></p>', encoding='utf-8')
    (DIST / 'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n', encoding='utf-8')
    red = ''.join(f'RewriteRule ^{re.escape(o.lstrip("/"))}/?$ {n} [R=301,L]\n' for o, n in RENAMES.items())
    (DIST / '.htaccess').write_text(f'''# Apache (наприклад, хостинг NIC.UA)
RewriteEngine On

# старі адреси статей
{red}
# без слеша в кінці
RewriteCond %{{REQUEST_FILENAME}} !-d
RewriteRule ^(.+)/$ /$1 [R=301,L]

# /page.html → /page
RewriteCond %{{THE_REQUEST}} \\s/([^.?\\s]+)\\.html[\\s?] [NC]
RewriteRule ^ /%1 [R=301,L]
RewriteRule ^index$ / [R=301,L]

# /page → page.html
RewriteCond %{{REQUEST_FILENAME}}.html -f
RewriteRule ^([^.]+)$ $1.html [L]

ErrorDocument 404 /404.html

<IfModule mod_expires.c>
ExpiresActive On
ExpiresByType image/webp "access plus 1 year"
ExpiresByType image/png "access plus 1 year"
ExpiresByType text/css "access plus 1 month"
ExpiresByType video/mp4 "access plus 1 year"
</IfModule>
''', encoding='utf-8', newline='\n')
    (DIST / '_redirects').write_text('# Netlify / Cloudflare Pages\n' + ''.join(f'{o} {n} 301\n' for o, n in RENAMES.items()), encoding='utf-8', newline='\n')
    size = sum(f.stat().st_size for f in IMG_OUT.iterdir())
    print(f'pages: {len(pages) + 1}, posts: {len(posts)}, images: {len(list(IMG_OUT.iterdir()))} files, {size / 1e6:.1f} MB')
    for p in posts:
        print(' ', p.date, p.path, '|', p.category or '-', '|', p.author, '| imgs', len(p.images))


if __name__ == '__main__':
    main()
