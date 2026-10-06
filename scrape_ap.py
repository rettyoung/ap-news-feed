#!/usr/bin/env python3
"""Build an RSS feed of AP News Top News (apnews.com/hub/apf-topnews).

Standard library only. Run hourly by GitHub Actions; writes docs/feed.xml and
data/seen.json (first-seen times, used as a fallback pubDate so every item is dated).
"""
import email.utils, html, json, os, re, sys, time, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

HUB = os.environ.get("AP_HUB", "https://apnews.com/hub/apf-topnews")
OUT = "docs/feed.xml"
STATE = "data/seen.json"
MAX_ITEMS = 60            # items kept in the feed
KEEP_DAYS = 7             # how long to remember seen links
FETCH_DETAILS = 25        # max new articles to open per run (for date + summary)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
SKIP = re.compile(r"/(sports|entertainment|lifestyle|photography|video)/|"
                  r"-(nfl|nba|mlb|nhl|wnba|ncaa|soccer|golf|tennis)-", re.I)


def get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


class Links(HTMLParser):
    """Collect <a href=".../article/..."> with their visible text."""
    def __init__(self):
        super().__init__()
        self.cur, self.buf, self.found = None, [], {}

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if href.startswith("/"):
                href = "https://apnews.com" + href
            if re.match(r"https://apnews\.com/article/[^?#]+", href):
                self.cur, self.buf = href.split("?")[0].split("#")[0], []

    def handle_data(self, data):
        if self.cur:
            self.buf.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.cur:
            text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
            if self.cur not in self.found or len(text) > len(self.found[self.cur]):
                self.found[self.cur] = text
            self.cur = None


def title_from_slug(url):
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    slug = re.sub(r"-[0-9a-f]{32}$", "", slug)
    return slug.replace("-", " ").capitalize()


def meta(page, *names):
    for n in names:
        m = re.search(r'<meta[^>]+(?:property|name|itemprop)=["\']%s["\'][^>]+content=["\']([^"\']+)' % re.escape(n), page) \
            or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name|itemprop)=["\']%s["\']' % re.escape(n), page)
        if m:
            return html.unescape(m.group(1)).strip()
    m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', page) if "datePublished" in names else None
    return m.group(1) if m else ""


def parse_dt(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def main():
    os.makedirs("docs", exist_ok=True); os.makedirs("data", exist_ok=True)
    seen = json.load(open(STATE)) if os.path.exists(STATE) else {}
    now = datetime.now(timezone.utc)

    try:
        hub = get(HUB)
    except Exception as e:
        sys.exit(f"ERROR fetching {HUB}: {e}")   # fails the run -> GitHub emails you
    p = Links(); p.feed(hub)
    links = {u: t for u, t in p.found.items() if not SKIP.search(u)}
    if not links:
        sys.exit("ERROR: hub page fetched but no article links found (layout change or block page)")

    opened = 0
    for url, text in links.items():
        rec = seen.get(url)
        if rec is None:
            rec = {"title": text or title_from_slug(url), "first_seen": now.isoformat(),
                   "published": "", "summary": ""}
            if opened < FETCH_DETAILS:
                opened += 1
                try:
                    page = get(url)
                    rec["title"] = meta(page, "og:title") or rec["title"]
                    rec["summary"] = meta(page, "og:description", "description")
                    rec["published"] = meta(page, "article:published_time", "datePublished")
                except Exception as e:
                    print(f"warn: detail fetch failed {url}: {e}")
                time.sleep(1)
            seen[url] = rec
        rec["last_seen"] = now.isoformat()

    cutoff = now.timestamp() - KEEP_DAYS * 86400
    seen = {u: r for u, r in seen.items() if parse_dt(r["first_seen"]).timestamp() > cutoff}
    json.dump(seen, open(STATE, "w"), indent=1, sort_keys=True)

    def when(r):
        return parse_dt(r.get("published") or "") or parse_dt(r["first_seen"])
    items = sorted(seen.items(), key=lambda kv: when(kv[1]), reverse=True)[:MAX_ITEMS]

    esc = html.escape
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0"><channel>',
           '<title>AP News: Top News (self-hosted)</title>',
           f'<link>{esc(HUB)}</link>',
           '<description>AP Top News, scraped hourly by GitHub Actions</description>',
           f'<lastBuildDate>{email.utils.format_datetime(now)}</lastBuildDate>',
           '<ttl>60</ttl>']
    for url, r in items:
        out += ['<item>', f'<title>{esc(r["title"])}</title>', f'<link>{esc(url)}</link>',
                f'<guid isPermaLink="true">{esc(url)}</guid>',
                f'<pubDate>{email.utils.format_datetime(when(r))}</pubDate>',
                f'<description>{esc(r.get("summary", ""))}</description>', '</item>']
    out.append('</channel></rss>')
    open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(f"ok: {len(links)} links on hub, {opened} new articles opened, {len(items)} items in feed")


if __name__ == "__main__":
    main()
