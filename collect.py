"""Archive BJX's public policy index; never publish a challenge page as news."""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from lxml import html
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
PAGE = "https://news.bjx.com.cn/zc/1/"
FEED = "https://raw.githubusercontent.com/zhengboyuan/bjx-policy-rss/main/public/feed.xml"
CST = timezone(timedelta(hours=8))
ET.register_namespace("atom", "http://www.w3.org/2005/Atom")


def parse_page(raw: str) -> tuple[list[dict], int]:
    tree = html.fromstring(raw)
    rows = tree.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," cc-list-content ")]/ul/li')
    if not rows:
        raise ValueError("Public policy list missing; possible access verification. Archive unchanged.")
    items = []
    for row in rows:
        links = row.xpath('./a[@href]')
        dates = row.xpath('./span/text()')
        if len(links) != 1 or len(dates) != 1:
            raise ValueError("Unexpected policy row structure")
        title = " ".join(links[0].text_content().split())
        url = urljoin(PAGE, links[0].get('href'))
        target = urlparse(url)
        if not title or target.scheme not in {'https', 'http'} or not (target.hostname or '').endswith('.bjx.com.cn'):
            raise ValueError("Unexpected article link")
        published = datetime.strptime(dates[0].strip(), '%Y-%m-%d').replace(tzinfo=CST)
        items.append({'title': title, 'url': url, 'published_at': published.isoformat()})
    maximum = tree.xpath('//input[@name="pageNumber"]/@max')
    if len(maximum) != 1 or not maximum[0].isdigit() or not 1 <= int(maximum[0]) <= 1000:
        raise ValueError("Cannot determine archive pagination")
    return items, int(maximum[0])


class Fetcher:
    def __enter__(self):
        self.driver = self.browser = self.page = None
        return self

    def __exit__(self, *args):
        if self.browser:
            self.browser.close()
        if self.driver:
            self.driver.stop()

    def read(self, number):
        url = urljoin(PAGE, f'/zc/{number}/')
        if self.page is None:
            try:
                with urllib.request.urlopen(url, timeout=40) as response:
                    raw = response.read().decode('utf-8')
                return parse_page(raw)
            except Exception as error:
                print(f'HTTP access unavailable ({type(error).__name__}); trying standard browser', flush=True)
                self.driver = sync_playwright().start()
                options = {'headless': True}
                if os.environ.get('BROWSER_EXECUTABLE'):
                    options['executable_path'] = os.environ['BROWSER_EXECUTABLE']
                self.browser = self.driver.chromium.launch(**options)
                self.page = self.browser.new_page()
        self.page.goto(url, wait_until='domcontentloaded', timeout=45000)
        try:
            self.page.locator('.cc-list-content > ul > li').first.wait_for(timeout=30000)
        except Exception as error:
            raise RuntimeError(f'Cannot access page {number}; page title: {self.page.title()}. No archive changes.') from error
        return parse_page(self.page.content())


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_bytes(content)
    temp.replace(path)


def publish(items, status):
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    for tag, value in {
        'title': '北极星电力网｜政策（历史归档与更新）',
        'link': PAGE,
        'description': '非官方 RSS。归档北极星电力网政策栏目公开列表，保留标题、日期和原文链接。版权归原作者。',
        'language': 'zh-cn', 'ttl': '360',
        'lastBuildDate': format_datetime(datetime.fromisoformat(status['updated_at'])),
    }.items():
        ET.SubElement(channel, tag).text = value
    ET.SubElement(channel, '{http://www.w3.org/2005/Atom}link', href=FEED, rel='self', type='application/rss+xml')
    for item in items:
        node = ET.SubElement(channel, 'item')
        ET.SubElement(node, 'title').text = item['title']
        ET.SubElement(node, 'link').text = item['url']
        ET.SubElement(node, 'guid', isPermaLink='true').text = item['url']
        date = datetime.fromisoformat(item['published_at'])
        ET.SubElement(node, 'pubDate').text = format_datetime(date)
        ET.SubElement(node, 'description').text = f"{item['title']}\n发布日期：{date:%Y-%m-%d}\n来源：北极星电力网政策栏目。点击原文查看全文。"
    ET.indent(rss)
    xml = ET.tostring(rss, encoding='utf-8', xml_declaration=True)
    if len(ET.fromstring(xml).findall('./channel/item')) != len(items):
        raise ValueError('RSS item count mismatch')
    for path, value in [(ROOT / 'data/notices.json', items), (ROOT / 'public/status.json', status)]:
        atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())
    atomic_write(ROOT / 'public/feed.xml', xml)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help='Revisit every currently listed page')
    args = parser.parse_args()
    archive = ROOT / 'data/notices.json'
    previous = json.loads(archive.read_text()) if archive.exists() else []
    records = {item['url']: item for item in previous}
    known = set(records)
    fetched = set()
    signatures = set()
    consecutive_known = 0
    with Fetcher() as fetcher:
        number, maximum = 1, 1
        while number <= maximum:
            current, maximum = fetcher.read(number)
            urls = {row['url'] for row in current}
            signature = tuple(sorted(urls))
            if signature in signatures:
                raise ValueError(f'Duplicate page at {number}; archive unchanged')
            signatures.add(signature)
            consecutive_known = consecutive_known + 1 if urls <= known else 0
            fetched.update(urls)
            records.update({row['url']: row for row in current})
            print(f'Page {number}/{maximum}: {len(current)} records, {len(fetched)} unique fetched', flush=True)
            if previous and not args.full and consecutive_known >= 2:
                break
            if number == maximum:
                break
            time.sleep(2)
            number += 1
    items = sorted(records.values(), key=lambda row: (row['published_at'], row['url']), reverse=True)
    status = {
        'updated_at': datetime.now(CST).isoformat(), 'source_page': PAGE,
        'source_pages': maximum, 'pages_fetched_this_run': number,
        'full_scan_this_run': number == maximum, 'fetched_unique_count': len(fetched),
        'archive_count': len(items), 'oldest_date': items[-1]['published_at'][:10],
        'newest_date': items[0]['published_at'][:10],
        'coverage': '首次遍历栏目当前公开分页，此后累积保存；不包含官网已下架或不再列出的更早文章。',
    }
    publish(items, status)
    print(json.dumps(status, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
