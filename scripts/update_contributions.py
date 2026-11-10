#!/usr/bin/env python3
"""把 README 头部徽章里的「已合并 PR 数」刷新成实时值。

只替换 <!-- prs:badge:start --> 与 <!-- prs:badge:end --> 之间的那一行，
标记之外一个字符都不动。标记不在时安静退出，不当作失败。
依赖：Python 3.9+，仅标准库；凭据从环境变量 GITHUB_TOKEN / GH_TOKEN 读取。
"""

import json
import os
import urllib.parse
import urllib.request

OWNER = "shunxinyi-ljs"
README = "README.md"
API = "https://api.github.com"
BADGE_START, BADGE_END = "<!-- prs:badge:start -->", "<!-- prs:badge:end -->"


def api_get(url, token):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "User-Agent": OWNER + "-profile-readme",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def merged_pr_count(token):
    query = urllib.parse.quote("author:%s type:pr is:merged" % OWNER)
    return api_get("%s/search/issues?q=%s&per_page=1" % (API, query), token)["total_count"]


def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("缺少 GITHUB_TOKEN / GH_TOKEN，跳过")
        return 0

    with open(README, encoding="utf-8") as f:
        original = f.read()

    start, end = original.find(BADGE_START), original.find(BADGE_END)
    if start < 0 or end < start:
        print("README 里没有徽章标记，跳过（改版正常，不算失败）")
        return 0

    count = merged_pr_count(token)
    badge = ('<img src="https://img.shields.io/badge/MERGED%%20PRs-%d-4f46e5?style=for-the-badge" '
             'alt="Merged PRs %d" />' % (count, count))
    updated = original[:start + len(BADGE_START)] + "\n" + badge + "\n" + original[end:]

    if updated == original:
        print("已合并 PR 共 %d 条，README 无变化" % count)
        return 0

    with open(README, "w", encoding="utf-8", newline="\n") as f:
        f.write(updated)
    print("已合并 PR 共 %d 条，README 已更新" % count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
