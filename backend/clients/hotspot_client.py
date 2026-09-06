"""
热点客户端（RSSHub / RSS）—— 拉取热点供朋友圈文案与对话引用。

【方法】
- fetch_hotspots() -> list[Hotspot]
  拉取 RSS_FEED_URLS（逗号分隔）多个订阅源 → 解析标题/摘要/链接 → 合并去重
  返回结构化热点列表；单个源失败不影响其它源。

【说明】
- 用标准库 xml.etree 解析，同时兼容 RSS 2.0（<item>）与 Atom（<entry>），
  不额外引入 feedparser 依赖。
- 超时与错误都做容错：源挂掉只降级返回空，不抛异常拖垮定时任务。
"""
import html
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional

import httpx

from config.settings import get_settings

settings = get_settings()


@dataclass
class Hotspot:
    title: str
    link: str
    summary: str = ""
    source: str = ""
    tags: List[str] = field(default_factory=list)


def _strip_html(raw: Optional[str]) -> str:
    """去掉摘要里可能的 HTML 标签，保留纯文本。"""
    if not raw:
        return ""
    import re
    return html.unescape(re.sub(r"<[^>]+>", "", raw)).strip()


def _parse_feed(text: str, source: str) -> List[Hotspot]:
    """解析 RSS 2.0 / Atom 两种格式，返回 Hotspot 列表。"""
    root = ET.fromstring(text)
    items = []
    # RSS 2.0：<channel><item>
    for item in root.iter("item"):
        title = _strip_html(item.findtext("title"))
        link = (item.findtext("link") or "").strip()
        summary = _strip_html(item.findtext("description") or item.findtext("summary"))
        if title and link:
            items.append(Hotspot(title=title, link=link, summary=summary, source=source))
    # Atom：<entry>
    for entry in root.iter("entry"):
        title = _strip_html(entry.findtext("title"))
        link = ""
        for ln in entry.findall("{http://www.w3.org/2005/Atom}link"):
            link = ln.get("href") or link
        if not link:
            link = (entry.findtext("link") or "").strip()
        summary = _strip_html(entry.findtext("summary") or entry.findtext("content"))
        if title and link:
            items.append(Hotspot(title=title, link=link, summary=summary, source=source))
    return items


class HotspotClient:
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def fetch_hotspots(self, limit: int = 20) -> List[Hotspot]:
        """拉取所有订阅源的热点，合并去重（按标题），返回前 limit 条。"""
        urls = settings.rss_feed_url_list
        if not urls:
            return []

        seen: set = set()
        result: List[Hotspot] = []
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for url in urls:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    for h in _parse_feed(resp.text, source=url):
                        key = h.title
                        if key in seen:
                            continue
                        seen.add(key)
                        result.append(h)
                        if len(result) >= limit:
                            return result
                except Exception as e:
                    print(f"⚠️ 热点源拉取失败 {url}: {e}")
                    continue
        return result


# 全局单例
_hotspot_client: Optional[HotspotClient] = None


def get_hotspot_client() -> HotspotClient:
    global _hotspot_client
    if _hotspot_client is None:
        _hotspot_client = HotspotClient()
    return _hotspot_client
