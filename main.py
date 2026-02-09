#!/usr/bin/env python3
"""
Prototype: monitor UDN + TVBS, detect high-impact events, generate drafts,
and hand off to an ETtoday publishing adapter.

Notes:
- OpenClaw crawler backend is intentionally left as a stub for now.
- Mobile push monitoring is intentionally left as a stub for now.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import logging
import os
import sqlite3
import subprocess
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Optional, Set
from urllib.parse import urljoin, urlparse
from collections import Counter
import math

import requests
import yaml

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None

try:
    import jieba
    JIEBA_AVAILABLE = True
except Exception:
    JIEBA_AVAILABLE = False

from html.parser import HTMLParser


LOGGER = logging.getLogger("newsfollow")


DEFAULT_CONFIG = {
    "interval_seconds": 180,
    "event_threshold": 11,
    "cluster_similarity": 0.74,
    "crawler_backend": "requests",  # requests | openclaw
    "database_path": "./newsfollow.db",
    "llm": {
        "enabled": True,
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.4,
        "max_tokens": 1200,
        "style_prompt": (
            "Write in concise breaking-news style for Taiwan digital media. "
            "Lead with the key development, include source attributions, and avoid speculation."
        ),
    },
    "publisher": {
        "mode": "stub",  # stub | command
        "publish_command": "",
    },
    "mobile_push": {
        "enabled": False,
    },
    "sources": [
        {
            "source_id": "udn",
            "source_name": "UDN",
            "domain_contains": "udn.com",
            "sections": [
                {
                    "section_id": "homepage",
                    "url": "https://udn.com/news/index",
                    "weight": 5,
                    "selectors": [
                        "a.story-list__title-link",
                        ".story-list a",
                        "main a[href*='/news/story/']",
                    ],
                    "max_items": 20,
                },
                {
                    "section_id": "marquee",
                    "url": "https://udn.com/news/index",
                    "weight": 6,
                    "selectors": [
                        ".breaking-news a",
                        ".news-bar a",
                        ".newsList a[href*='/news/story/']",
                    ],
                    "max_items": 12,
                },
                {
                    "section_id": "hot",
                    "url": "https://udn.com/rank/pv",
                    "weight": 4,
                    "selectors": [
                        ".ranking-list a",
                        "table a[href*='/news/story/']",
                        "main a[href*='/news/story/']",
                    ],
                    "max_items": 20,
                },
            ],
        },
        {
            "source_id": "tvbs",
            "source_name": "TVBS",
            "domain_contains": "news.tvbs.com.tw",
            "sections": [
                {
                    "section_id": "homepage",
                    "url": "https://news.tvbs.com.tw/",
                    "weight": 5,
                    "selectors": [
                        "a.news__title",
                        "a[href*='news.tvbs.com.tw/'][title]",
                        "main a[href*='news.tvbs.com.tw/']",
                    ],
                    "max_items": 20,
                },
                {
                    "section_id": "marquee",
                    "url": "https://news.tvbs.com.tw/",
                    "weight": 6,
                    "selectors": [
                        ".breakingNews a",
                        ".marquee a",
                        ".rolling a",
                    ],
                    "max_items": 12,
                },
                {
                    "section_id": "hot",
                    "url": "https://news.tvbs.com.tw/hot",
                    "weight": 4,
                    "selectors": [
                        ".hot a",
                        ".popular a",
                        "main a[href*='news.tvbs.com.tw/']",
                    ],
                    "max_items": 20,
                },
            ],
        },
    ],
}


@dataclass
class Signal:
    source_id: str
    source_name: str
    section_id: str
    title: str
    url: str
    weight: int
    crawled_at: str

    @property
    def normalized_title(self) -> str:
        return normalize_title(self.title)


@dataclass
class Event:
    event_key: str
    canonical_title: str
    score: float
    source_count: int
    signal_count: int
    reasons: List[str]
    signals: List[Signal]


class Repository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                note TEXT
            );

            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                source_name TEXT NOT NULL,
                section_id TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                normalized_title TEXT NOT NULL,
                weight INTEGER NOT NULL,
                crawled_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_signals_run ON signals(run_id);
            CREATE INDEX IF NOT EXISTS idx_signals_norm ON signals(normalized_title);

            CREATE TABLE IF NOT EXISTS events (
                event_key TEXT PRIMARY KEY,
                canonical_title TEXT NOT NULL,
                score REAL NOT NULL,
                source_count INTEGER NOT NULL,
                signal_count INTEGER NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new'
            );

            CREATE TABLE IF NOT EXISTS event_signals (
                event_key TEXT NOT NULL,
                signal_id INTEGER NOT NULL,
                PRIMARY KEY (event_key, signal_id)
            );

            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_key TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                image_prompt TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                raw_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS publish_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_key TEXT NOT NULL,
                published_at TEXT NOT NULL,
                status TEXT NOT NULL,
                external_id TEXT,
                message TEXT
            );
            """
        )
        self.conn.commit()

    def start_run(self) -> str:
        run_id = dt.datetime.now(dt.timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
        started_at = now_iso()
        self.conn.execute(
            "INSERT INTO runs (run_id, started_at, status) VALUES (?, ?, ?)",
            (run_id, started_at, "running"),
        )
        self.conn.commit()
        return run_id

    def finish_run(self, run_id: str, status: str, note: str = "") -> None:
        self.conn.execute(
            "UPDATE runs SET finished_at = ?, status = ?, note = ? WHERE run_id = ?",
            (now_iso(), status, note, run_id),
        )
        self.conn.commit()

    def save_signals(self, run_id: str, signals: List[Signal]) -> List[int]:
        ids: List[int] = []
        for s in signals:
            cur = self.conn.execute(
                """
                INSERT INTO signals
                (run_id, source_id, source_name, section_id, title, url, normalized_title, weight, crawled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    s.source_id,
                    s.source_name,
                    s.section_id,
                    s.title,
                    s.url,
                    s.normalized_title,
                    s.weight,
                    s.crawled_at,
                ),
            )
            ids.append(cur.lastrowid)
        self.conn.commit()
        return ids

    def upsert_event(self, event: Event) -> None:
        existing = self.conn.execute(
            "SELECT event_key, first_seen FROM events WHERE event_key = ?", (event.event_key,)
        ).fetchone()
        now = now_iso()
        if existing:
            self.conn.execute(
                """
                UPDATE events
                SET canonical_title = ?, score = ?, source_count = ?, signal_count = ?, last_seen = ?
                WHERE event_key = ?
                """,
                (
                    event.canonical_title,
                    event.score,
                    event.source_count,
                    event.signal_count,
                    now,
                    event.event_key,
                ),
            )
        else:
            self.conn.execute(
                """
                INSERT INTO events
                (event_key, canonical_title, score, source_count, signal_count, first_seen, last_seen, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'new')
                """,
                (
                    event.event_key,
                    event.canonical_title,
                    event.score,
                    event.source_count,
                    event.signal_count,
                    now,
                    now,
                ),
            )
        self.conn.commit()

    def bind_event_signals(self, event_key: str, signal_ids: List[int]) -> None:
        for signal_id in signal_ids:
            self.conn.execute(
                "INSERT OR IGNORE INTO event_signals (event_key, signal_id) VALUES (?, ?)",
                (event_key, signal_id),
            )
        self.conn.commit()

    def save_draft(self, event_key: str, draft: Dict) -> None:
        self.conn.execute(
            """
            INSERT INTO drafts
            (event_key, generated_at, title, body, image_prompt, sources_json, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_key,
                now_iso(),
                draft.get("title", ""),
                draft.get("body", ""),
                draft.get("image_prompt", ""),
                json.dumps(draft.get("sources", []), ensure_ascii=False),
                json.dumps(draft, ensure_ascii=False),
            ),
        )
        self.conn.commit()

    def save_publish_log(self, event_key: str, result: Dict) -> None:
        self.conn.execute(
            """
            INSERT INTO publish_logs
            (event_key, published_at, status, external_id, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event_key,
                now_iso(),
                result.get("status", "unknown"),
                result.get("external_id", ""),
                result.get("message", ""),
            ),
        )
        self.conn.commit()

    def list_recent_events(self, limit: int = 20) -> List[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT event_key, canonical_title, score, source_count, signal_count, first_seen, last_seen, status
            FROM events
            ORDER BY last_seen DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


class RequestsCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0 Safari/537.36"
                )
            }
        )

    def fetch_html(self, url: str, timeout: int = 15) -> str:
        # ETtoday SSL certificate has issues (Missing Subject Key Identifier)
        # Disable verification for ETtoday domains to enable crawling
        verify_ssl = not ("ettoday.net" in url)

        try:
            resp = self.session.get(url, timeout=timeout, verify=verify_ssl)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.SSLError as e:
            # Fallback: retry without SSL verification if SSL error occurs
            LOGGER.warning("SSL error for %s, retrying without verification: %s", url, e)
            resp = self.session.get(url, timeout=timeout, verify=False)
            resp.raise_for_status()
            return resp.text


class OpenClawCrawlerStub:
    """
    Reserved for future OpenClaw-powered crawling. Intentionally left blank for now.
    """

    def fetch_html(self, url: str, timeout: int = 15) -> str:
        raise NotImplementedError(
            "OpenClaw crawler backend is reserved for future implementation. "
            "Use crawler_backend=requests for now."
        )


class MobilePushMonitorStub:
    """
    Reserved for future mobile push notification ingestion.
    """

    def collect(self) -> List[Signal]:
        return []


class DraftGenerator:
    def __init__(self, llm_cfg: Dict):
        self.cfg = llm_cfg
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")

    def generate(self, event: Event) -> Dict:
        if not self.cfg.get("enabled", True):
            return self._fallback(event, "llm disabled")

        if self.cfg.get("provider") != "openai":
            return self._fallback(event, "provider not implemented")

        if not self.api_key:
            return self._fallback(event, "OPENAI_API_KEY missing")

        payload = self._build_payload(event)

        try:
            resp = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=45,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed = parse_json_block(content)
            if not isinstance(parsed, dict):
                return self._fallback(event, "llm returned non-json")

            return {
                "title": parsed.get("headline", event.canonical_title),
                "body": parsed.get("article", ""),
                "image_prompt": parsed.get("image_prompt", ""),
                "sources": [{"source": s.source_name, "url": s.url} for s in event.signals],
                "meta": {
                    "event_key": event.event_key,
                    "model": self.cfg.get("model", "gpt-4o-mini"),
                    "reason": "llm-success",
                },
            }
        except Exception as exc:
            LOGGER.warning("LLM generation failed for %s: %s", event.event_key, exc)
            return self._fallback(event, f"llm-error: {exc}")

    def _build_payload(self, event: Event) -> Dict:
        style = self.cfg.get("style_prompt", "")
        event_brief = {
            "event_key": event.event_key,
            "canonical_title": event.canonical_title,
            "score": event.score,
            "reasons": event.reasons,
            "signals": [
                {
                    "source": s.source_name,
                    "section": s.section_id,
                    "title": s.title,
                    "url": s.url,
                }
                for s in event.signals
            ],
        }

        system_prompt = (
            "You are a newsroom assistant. Return strict JSON with keys: "
            "headline, article, image_prompt. No markdown, no extra keys."
        )
        user_prompt = (
            f"Style requirement: {style}\n"
            "Task: synthesize cross-source event draft for ETtoday workflow.\n"
            "Input event JSON:\n"
            f"{json.dumps(event_brief, ensure_ascii=False)}"
        )
        return {
            "model": self.cfg.get("model", "gpt-4o-mini"),
            "temperature": self.cfg.get("temperature", 0.4),
            "max_tokens": self.cfg.get("max_tokens", 1200),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

    def _fallback(self, event: Event, reason: str) -> Dict:
        source_lines = "\n".join(f"- {s.source_name} ({s.section_id}): {s.title}" for s in event.signals[:6])
        body = (
            f"[PROTOTYPE DRAFT | {reason}]\n"
            f"Event: {event.canonical_title}\n\n"
            "Cross-source highlights:\n"
            f"{source_lines}\n\n"
            "This is a placeholder draft. Connect your production LLM prompt for final tone/style."
        )
        return {
            "title": f"[Prototype] {event.canonical_title}",
            "body": body,
            "image_prompt": (
                "news photo style, realistic, no logos, depict the core event context inferred from title"
            ),
            "sources": [{"source": s.source_name, "url": s.url} for s in event.signals],
            "meta": {
                "event_key": event.event_key,
                "reason": reason,
            },
        }


class PublisherStub:
    def publish(self, draft: Dict) -> Dict:
        external_id = hashlib.md5(draft["title"].encode("utf-8")).hexdigest()[:12]
        return {
            "status": "stubbed",
            "external_id": external_id,
            "message": "ETtoday publisher not connected yet. Dry-run only.",
        }


class PublisherCommandAdapter:
    def __init__(self, command: str):
        self.command = command

    def publish(self, draft: Dict) -> Dict:
        if not self.command.strip():
            return {
                "status": "failed",
                "external_id": "",
                "message": "publish_command is empty",
            }

        try:
            proc = subprocess.run(
                self.command,
                input=json.dumps(draft, ensure_ascii=False),
                text=True,
                shell=True,
                capture_output=True,
                timeout=60,
            )
            if proc.returncode != 0:
                return {
                    "status": "failed",
                    "external_id": "",
                    "message": f"command failed: {proc.stderr.strip()}",
                }

            out = proc.stdout.strip()
            if out:
                try:
                    data = json.loads(out)
                    return {
                        "status": data.get("status", "ok"),
                        "external_id": data.get("external_id", ""),
                        "message": data.get("message", ""),
                    }
                except Exception:
                    pass

            return {
                "status": "ok",
                "external_id": "",
                "message": "publish command executed",
            }
        except Exception as exc:
            return {
                "status": "failed",
                "external_id": "",
                "message": str(exc),
            }


class MonitorApp:
    def __init__(self, cfg: Dict):
        self.cfg = cfg
        self.repo = Repository(cfg["database_path"])
        self.crawler = self._build_crawler(cfg.get("crawler_backend", "requests"))
        self.push_monitor = MobilePushMonitorStub()
        self.generator = DraftGenerator(cfg["llm"])
        self.publisher = self._build_publisher(cfg["publisher"])

    def _build_crawler(self, backend: str):
        if backend == "openclaw":
            LOGGER.warning("crawler_backend=openclaw is stubbed. Falling back to requests backend.")
            return RequestsCrawler()
        return RequestsCrawler()

    def _build_publisher(self, pub_cfg: Dict):
        mode = pub_cfg.get("mode", "stub")
        if mode == "command":
            return PublisherCommandAdapter(pub_cfg.get("publish_command", ""))
        return PublisherStub()

    def run_once(self, publish: bool = False) -> Dict:
        run_id = self.repo.start_run()
        LOGGER.info("run started: %s", run_id)

        try:
            signals = self.collect_signals()
            signal_ids = self.repo.save_signals(run_id, signals)

            id_by_signature = {}
            for sid, signal in zip(signal_ids, signals):
                signature = f"{signal.source_id}|{signal.section_id}|{signal.normalized_title}|{signal.url}"
                id_by_signature[signature] = sid

            events = detect_events(
                signals=signals,
                score_threshold=self.cfg["event_threshold"],
                similarity_threshold=self.cfg["cluster_similarity"],
            )

            for event in events:
                self.repo.upsert_event(event)
                related_signal_ids = []
                for sig in event.signals:
                    signature = f"{sig.source_id}|{sig.section_id}|{sig.normalized_title}|{sig.url}"
                    if signature in id_by_signature:
                        related_signal_ids.append(id_by_signature[signature])
                self.repo.bind_event_signals(event.event_key, related_signal_ids)

                draft = self.generator.generate(event)
                self.repo.save_draft(event.event_key, draft)

                if publish:
                    result = self.publisher.publish(draft)
                    self.repo.save_publish_log(event.event_key, result)

                LOGGER.info(
                    "event=%s score=%.1f sources=%d signals=%d title=%s",
                    event.event_key,
                    event.score,
                    event.source_count,
                    event.signal_count,
                    event.canonical_title,
                )

            self.repo.finish_run(run_id, "ok", f"signals={len(signals)}, events={len(events)}")
            return {"run_id": run_id, "signals": len(signals), "events": len(events)}
        except Exception as exc:
            self.repo.finish_run(run_id, "failed", str(exc))
            raise

    def collect_signals(self) -> List[Signal]:
        all_signals: List[Signal] = []
        ts = now_iso()

        for source in self.cfg["sources"]:
            for section in source["sections"]:
                url = section["url"]
                try:
                    html = self.crawler.fetch_html(url)
                except Exception as exc:
                    LOGGER.warning("crawl failed source=%s section=%s url=%s err=%s", source["source_id"], section["section_id"], url, exc)
                    continue

                extracted = extract_signals(
                    html=html,
                    base_url=url,
                    source_id=source["source_id"],
                    source_name=source["source_name"],
                    section_id=section["section_id"],
                    domain_contains=source.get("domain_contains", ""),
                    selectors=section.get("selectors", []),
                    weight=section.get("weight", 1),
                    crawled_at=ts,
                    max_items=section.get("max_items", 20),
                )
                all_signals.extend(extracted)

        if self.cfg.get("mobile_push", {}).get("enabled", False):
            all_signals.extend(self.push_monitor.collect())

        deduped = dedupe_signals(all_signals)
        return deduped


class _FallbackAnchorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = []
        self._stack = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        attr_map = dict(attrs)
        href = (attr_map.get("href") or "").strip()
        title = (attr_map.get("title") or "").strip()
        self._stack.append({"href": href, "title": title, "text": []})

    def handle_data(self, data):
        if self._stack and data and data.strip():
            self._stack[-1]["text"].append(data.strip())

    def handle_endtag(self, tag):
        if tag != "a" or not self._stack:
            return
        item = self._stack.pop()
        text = " ".join(item["text"]).strip()
        self.anchors.append(
            {
                "href": item["href"],
                "title": item["title"],
                "text": text,
            }
        )


def _extract_signals_fallback(
    html: str,
    base_url: str,
    source_id: str,
    source_name: str,
    section_id: str,
    domain_contains: str,
    weight: int,
    crawled_at: str,
    max_items: int,
) -> List[Signal]:
    parser = _FallbackAnchorParser()
    parser.feed(html)

    links: List[Signal] = []
    seen = set()

    for a in parser.anchors:
        candidate = signal_from_anchor(
            a,
            base_url=base_url,
            source_id=source_id,
            source_name=source_name,
            section_id=section_id,
            domain_contains=domain_contains,
            weight=weight,
            crawled_at=crawled_at,
        )
        if not candidate:
            continue
        key = f"{candidate.url}|{candidate.normalized_title}"
        if key in seen:
            continue
        seen.add(key)
        links.append(candidate)
        if len(links) >= max_items:
            break

    return links


def extract_signals(
    html: str,
    base_url: str,
    source_id: str,
    source_name: str,
    section_id: str,
    domain_contains: str,
    selectors: List[str],
    weight: int,
    crawled_at: str,
    max_items: int,
) -> List[Signal]:
    if BeautifulSoup is None:
        return _extract_signals_fallback(
            html=html,
            base_url=base_url,
            source_id=source_id,
            source_name=source_name,
            section_id=section_id,
            domain_contains=domain_contains,
            weight=weight,
            crawled_at=crawled_at,
            max_items=max_items,
        )

    soup = BeautifulSoup(html, "html.parser")
    links: List[Signal] = []
    seen = set()

    # Try configured selectors first.
    for selector in selectors:
        for el in soup.select(selector):
            anchors = [el] if getattr(el, "name", "") == "a" else el.select("a[href]")
            for a in anchors:
                candidate = signal_from_anchor(
                    a,
                    base_url=base_url,
                    source_id=source_id,
                    source_name=source_name,
                    section_id=section_id,
                    domain_contains=domain_contains,
                    weight=weight,
                    crawled_at=crawled_at,
                )
                if not candidate:
                    continue
                key = f"{candidate.url}|{candidate.normalized_title}"
                if key in seen:
                    continue
                seen.add(key)
                links.append(candidate)
                if len(links) >= max_items:
                    return links

    # Fallback: generic anchor scan.
    for a in soup.select("a[href]"):
        candidate = signal_from_anchor(
            a,
            base_url=base_url,
            source_id=source_id,
            source_name=source_name,
            section_id=section_id,
            domain_contains=domain_contains,
            weight=weight,
            crawled_at=crawled_at,
        )
        if not candidate:
            continue
        key = f"{candidate.url}|{candidate.normalized_title}"
        if key in seen:
            continue
        seen.add(key)
        links.append(candidate)
        if len(links) >= max_items:
            break

    return links


def signal_from_anchor(
    a,
    base_url: str,
    source_id: str,
    source_name: str,
    section_id: str,
    domain_contains: str,
    weight: int,
    crawled_at: str,
) -> Optional[Signal]:
    if isinstance(a, dict):
        href = (a.get("href") or "").strip()
        extracted_text = (a.get("text") or "").strip()
        extracted_title = (a.get("title") or "").strip()
    else:
        href = (a.get("href") or "").strip()
        extracted_text = " ".join(a.stripped_strings)
        extracted_title = (a.get("title") or "").strip()

    if not href or href.startswith("javascript:"):
        return None

    url = urljoin(base_url, href)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None

    if domain_contains and domain_contains not in parsed.netloc:
        return None

    text = extracted_text or extracted_title
    text = compact_space(text)
    if not is_reasonable_title(text):
        return None

    return Signal(
        source_id=source_id,
        source_name=source_name,
        section_id=section_id,
        title=text,
        url=url,
        weight=weight,
        crawled_at=crawled_at,
    )


def dedupe_signals(signals: Iterable[Signal]) -> List[Signal]:
    deduped: List[Signal] = []
    seen = set()
    for s in signals:
        key = f"{s.source_id}|{s.section_id}|{s.normalized_title}|{s.url}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(s)
    return deduped


def detect_events(signals: List[Signal], score_threshold: float, similarity_threshold: float) -> List[Event]:
    if not signals:
        return []

    clusters: List[List[Signal]] = []
    representatives: List[str] = []

    for signal in signals:
        # 使用原始標題進行比對（改進的演算法）
        title = signal.title
        if not title:
            continue

        placed = False
        for i, rep in enumerate(representatives):
            # 使用改進的 title_similarity 函數比對原始標題
            if title_similarity(title, rep) >= similarity_threshold:
                clusters[i].append(signal)
                # 更新代表標題為較長的標題
                if len(title) > len(rep):
                    representatives[i] = title
                placed = True
                break

        if not placed:
            clusters.append([signal])
            representatives.append(title)

    events: List[Event] = []

    for cluster in clusters:
        score, reasons = score_cluster(cluster)
        if score < score_threshold:
            continue

        canonical = select_canonical_title(cluster)
        key = "evt_" + hashlib.md5(normalize_title(canonical).encode("utf-8")).hexdigest()[:16]
        source_count = len({s.source_id for s in cluster})

        events.append(
            Event(
                event_key=key,
                canonical_title=canonical,
                score=score,
                source_count=source_count,
                signal_count=len(cluster),
                reasons=reasons,
                signals=sorted(cluster, key=lambda s: s.weight, reverse=True),
            )
        )

    events.sort(key=lambda e: e.score, reverse=True)
    return events


def score_cluster(cluster: List[Signal]) -> (float, List[str]):
    reasons = []
    per_source_max: Dict[str, int] = {}
    per_section_count: Dict[str, int] = {}

    for sig in cluster:
        per_source_max[sig.source_id] = max(per_source_max.get(sig.source_id, 0), sig.weight)
        per_section_count[sig.section_id] = per_section_count.get(sig.section_id, 0) + 1

    base = sum(per_source_max.values())
    source_bonus = max(0, len(per_source_max) - 1) * 3
    volume_bonus = min(max(len(cluster) - 1, 0), 4)

    score = base + source_bonus + volume_bonus

    reasons.append(f"base_weight={base}")
    reasons.append(f"source_bonus={source_bonus}")
    reasons.append(f"volume_bonus={volume_bonus}")
    reasons.append(f"sections={dict(per_section_count)}")
    return float(score), reasons


def select_canonical_title(cluster: List[Signal]) -> str:
    sorted_titles = sorted((s.title for s in cluster), key=len, reverse=True)
    return sorted_titles[0]


def title_similarity(a: str, b: str) -> float:
    """
    改進的標題相似度演算法
    使用多種指標的加權組合，能識別「同一新聞但不同切角」的標題
    """
    if not a or not b:
        return 0.0

    # 正規化
    t1 = ' '.join(a.lower().split())
    t2 = ' '.join(b.lower().split())

    # 完全相同
    if t1 == t2:
        return 1.0

    # 子字串包含
    if t1 in t2 or t2 in t1:
        return 0.85

    # 如果 jieba 可用，使用改進算法
    if JIEBA_AVAILABLE:
        return _improved_similarity(a, b)

    # 否則使用原始算法
    return SequenceMatcher(None, a, b).ratio()


from functools import lru_cache

@lru_cache(maxsize=10000)
def get_jieba_tokens(text: str) -> tuple:
    """取得 jieba 分詞結果（含快取）"""
    return tuple(jieba.cut(text.lower()))


def _improved_similarity(title1: str, title2: str) -> float:
    """使用 jieba 分詞的改進相似度算法"""

    # 停用詞
    stopwords = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一個',
        '上', '也', '很', '到', '說', '要', '去', '你', '會', '著', '沒有', '看', '好',
        '自己', '這', '那', '與', '及', '或', '等', '被', '將', '於', '為', '以',
        '！', '？', '，', '。', '：', '；', '、', '「', '」', '『', '』', '（', '）',
        '【', '】', '《', '》', '〈', '〉', '．', '・', '…', '—', '～', '｜', '/', '|',
    }

    # 分詞
    import re
    tokens1 = list(get_jieba_tokens(title1))
    tokens2 = list(get_jieba_tokens(title2))

    # 過濾停用詞和標點
    tokens1 = [t.strip() for t in tokens1 if t.strip() and t not in stopwords and not re.match(r'^[^\w]+$', t)]
    tokens2 = [t.strip() for t in tokens2 if t.strip() and t not in stopwords and not re.match(r'^[^\w]+$', t)]

    if not tokens1 or not tokens2:
        return 0.0

    # 計算 Jaccard 相似度
    set1 = set(tokens1)
    set2 = set(tokens2)
    jaccard = len(set1 & set2) / len(set1 | set2) if set1 | set2 else 0.0

    # 計算餘弦相似度
    counter1 = Counter(tokens1)
    counter2 = Counter(tokens2)
    all_tokens = set(counter1.keys()) | set(counter2.keys())
    vec1 = [counter1.get(token, 0) for token in all_tokens]
    vec2 = [counter2.get(token, 0) for token in all_tokens]
    dot_product = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(v ** 2 for v in vec1))
    magnitude2 = math.sqrt(sum(v ** 2 for v in vec2))
    cosine = dot_product / (magnitude1 * magnitude2) if magnitude1 and magnitude2 else 0.0

    # 計算最長公共子字串比例 (使用 SequenceMatcher 優化效能)
    s1_clean = re.sub(r'\s+', '', title1)
    s2_clean = re.sub(r'\s+', '', title2)
    # SequenceMatcher.ratio() returns 2*M / T
    # It is C-optimized and much faster than manual DP loop
    lcs_ratio = SequenceMatcher(None, s1_clean, s2_clean).ratio()

    # 提取數字
    numbers1 = set(re.findall(r'\d+', title1))
    numbers2 = set(re.findall(r'\d+', title2))
    if numbers1 and numbers2:
        number_match = len(numbers1 & numbers2) / len(numbers1 | numbers2)
    else:
        number_match = 0.0

    # 加權組合
    combined_similarity = (
        jaccard * 0.35 +
        cosine * 0.30 +
        lcs_ratio * 0.25 +
        number_match * 0.10
    )

    # 檢查共同實體（長度 >= 2 的詞）
    long_tokens1 = {t for t in set1 if len(t) >= 2}
    long_tokens2 = {t for t in set2 if len(t) >= 2}
    common_tokens = long_tokens1 & long_tokens2
    has_entity = len(common_tokens) >= 2

    # 如果有共同實體，提升相似度
    if has_entity and 0.15 <= combined_similarity < 0.7:
        common_keywords_count = len(set1 & set2)
        if common_keywords_count >= 3:
            boost = 0.30
        elif common_keywords_count >= 2:
            boost = 0.25
        else:
            boost = 0.20
        combined_similarity = min(combined_similarity + boost, 0.85)

    # 如果數字匹配且有共同詞，額外加分
    if numbers1 and numbers2 and number_match >= 0.5 and len(set1 & set2) >= 1:
        combined_similarity = min(combined_similarity + 0.15, 0.9)

    return combined_similarity


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def compact_space(text: str) -> str:
    return " ".join(text.split())


def normalize_title(text: str) -> str:
    keep = []
    for ch in compact_space(text).lower():
        if ch.isalnum():
            keep.append(ch)
        elif "\u4e00" <= ch <= "\u9fff":  # CJK unified ideographs
            keep.append(ch)
    return "".join(keep)


def is_reasonable_title(text: str) -> bool:
    if len(text) < 8:
        return False
    if len(text) > 80:
        return False
    if text.count("/") > 2:
        return False
    return True


def parse_json_block(text: str):
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except Exception:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except Exception:
                return None
    return None


def load_config(path: str) -> Dict:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
        cfg = deep_merge(cfg, user_cfg)
    return cfg


def deep_merge(base: Dict, overlay: Dict) -> Dict:
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="newsfollow prototype")
    parser.add_argument("--config", default="./config.yaml", help="config file path")
    parser.add_argument("--log-level", default="INFO", help="DEBUG/INFO/WARNING/ERROR")

    sub = parser.add_subparsers(dest="command", required=True)

    run_once = sub.add_parser("run-once", help="run one monitoring cycle")
    run_once.add_argument("--publish", action="store_true", help="publish draft via adapter")

    loop = sub.add_parser("loop", help="run forever with interval")
    loop.add_argument("--publish", action="store_true", help="publish draft via adapter")

    list_events = sub.add_parser("list-events", help="list recent events")
    list_events.add_argument("--limit", type=int, default=20)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    cfg = load_config(args.config)
    app = MonitorApp(cfg)

    if args.command == "run-once":
        result = app.run_once(publish=args.publish)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "loop":
        interval = int(cfg.get("interval_seconds", 180))
        LOGGER.info("loop mode started, interval=%ss", interval)
        try:
            while True:
                result = app.run_once(publish=args.publish)
                LOGGER.info("cycle done: %s", result)
                time.sleep(interval)
        except KeyboardInterrupt:
            LOGGER.info("stopped by user")
            return 0

    if args.command == "list-events":
        rows = app.repo.list_recent_events(limit=args.limit)
        for r in rows:
            print(
                f"{r['last_seen']} | score={r['score']:.1f} | sources={r['source_count']} | "
                f"signals={r['signal_count']} | {r['canonical_title']}"
            )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
