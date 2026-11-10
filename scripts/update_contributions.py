#!/usr/bin/env python3
"""用 GitHub API 重写 README.md 里被标记圈定的两块内容。

只改标记之间的文本，标记之外一个字符都不动。没有变化时不写文件。
依赖：Python 3.9+，仅标准库；凭据从环境变量 GITHUB_TOKEN / GH_TOKEN 读取。
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

OWNER = "shunxinyi-ljs"
README = "README.md"
API = "https://api.github.com"

BADGE_START, BADGE_END = "<!-- prs:badge:start -->", "<!-- prs:badge:end -->"
TABLE_START, TABLE_END = "<!-- prs:start -->", "<!-- prs:end -->"

# 仓库 → 一句人话描述。顺序即表格行顺序；新仓库先落到 PR 标题拼接，
# 日志会提示补一行，避免措辞每天漂移。
REPO_DESCRIPTIONS = {
    "bytedance/deer-flow": "未安装中文分词器时，中文子词召回失败（`memory_search` 返回空结果）",
    "Tencent-Hunyuan/Hy-Memory": "记忆写盘与迁移可重放、检索时间戳归一、错误分类与截断上报、日志 stdout 清理",
}


def api_get(url, token):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "User-Agent": OWNER + "-profile-readme",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_merged_prs(token):
    """按 author 检索所有已合并 PR，跨仓库，自动翻页。"""
    items, page = [], 1
    query = urllib.parse.quote("author:%s type:pr is:merged" % OWNER)
    while True:
        data = api_get("%s/search/issues?q=%s&per_page=100&page=%d" % (API, query, page), token)
        batch = data.get("items", [])
        items.extend(batch)
        if len(batch) < 100:
            return items
        page += 1


def build_blocks(prs):
    grouped = {}
    for item in prs:
        repo = item["repository_url"].split("/repos/", 1)[-1]
        grouped.setdefault(repo, []).append((item["number"], item["title"]))

    ordered = [r for r in REPO_DESCRIPTIONS if r in grouped]
    ordered += sorted(r for r in grouped if r not in REPO_DESCRIPTIONS)

    rows, missing = [], []
    for repo in ordered:
        entries = sorted(grouped[repo], key=lambda x: x[0])
        links = " ".join("[#%d](https://github.com/%s/pull/%d)" % (n, repo, n) for n, _ in entries)
        desc = REPO_DESCRIPTIONS.get(repo)
        if desc is None:
            missing.append(repo)
            desc = "、".join(t.strip().rstrip(".") for _, t in entries)
        rows.append("| **[%s](https://github.com/%s)** | %s | %s |" % (repo, repo, links, desc))

    total = sum(len(v) for v in grouped.values())
    table = "\n".join([
        "只列已合并的 PR（共 %d 条）：" % total,
        "",
        "| 仓库 | 已合并 PR | 做了什么 |",
        "| :--- | :--- | :--- |",
    ] + rows)
    badge = ('<img src="https://img.shields.io/badge/MERGED%%20PRs-%d-4f46e5?style=for-the-badge" '
             'alt="Merged PRs %d" />' % (total, total))
    return badge, table, missing, total


def replace_block(text, start, end, body):
    i, j = text.find(start), text.find(end)
    if i < 0 or j < 0 or j < i:
        sys.exit("标记缺失或顺序不对：%s / %s" % (start, end))
    head, tail = text[:i + len(start)], text[j:]
    return head + "\n" + body + "\n" + tail


def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("缺少 GITHUB_TOKEN / GH_TOKEN 环境变量")

    with open(README, encoding="utf-8") as f:
        original = f.read()

    prs = fetch_merged_prs(token)
    badge, table, missing, total = build_blocks(prs)

    updated = replace_block(original, BADGE_START, BADGE_END, badge)
    updated = replace_block(updated, TABLE_START, TABLE_END, table)

    if missing:
        print("警告：以下仓库还没有固定描述，当前用 PR 标题拼接，请到 REPO_DESCRIPTIONS 补一行：%s"
              % ", ".join(missing))
    print("已合并 PR 共 %d 条，覆盖 %d 个仓库" % (total, len({p["repository_url"] for p in prs})))

    if updated == original:
        print("README 无变化")
        return 0

    with open(README, "w", encoding="utf-8", newline="\n") as f:
        f.write(updated)
    print("README 已更新")
    return 0


if __name__ == "__main__":
    sys.exit(main())
