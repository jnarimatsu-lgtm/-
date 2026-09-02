# -*- coding: utf-8 -*-
"""検索枠切れ（WebSearch 200/200）が起きた波を、ワークフローのジャーナルから検出する。
requeue_unverified.py はエージェントが「未検証」と自己申告した行しか拾えない。
反証層が枯渇した場合はその申告が出ないまま1次判定が素通りするので、こちらで見る。"""
import json, os, re, glob, collections, sys

W = "/root/.claude/projects/-home-user--/fcda6a82-279b-5a30-a006-b52ce02ba704/subagents/workflows"

def main():
    runs = collections.defaultdict(lambda: {"wave": None, "starved": 0, "agents": 0})
    for jf in glob.glob(f"{W}/*/journal.jsonl"):
        run = os.path.basename(os.path.dirname(jf))
        try:
            txt = open(jf, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        m = re.search(r'"wave"\s*:\s*(\d+)', txt)
        if m: runs[run]["wave"] = int(m.group(1))
        runs[run]["agents"] = txt.count('"type":"result"')
        runs[run]["starved"] = len(re.findall(r"web search budget \(200 of 200\)", txt))
    bad = [(v["wave"], k, v) for k, v in runs.items() if v["starved"]]
    if not bad:
        print("検索枠切れの記録なし"); return 0
    print("検索枠切れ（200/200）が記録された実行:")
    for wave, run, v in sorted(bad, key=lambda x: (x[0] is None, x[0])):
        print("  波%-5s %s  枯渇イベント%d回 / エージェント%d"
              % (wave if wave is not None else "?", run[:20], v["starved"], v["agents"]))
    print("\n※ 反証層が枯渇した波は、1次判定が反証を受けずに成果物へ入っている。")
    return len(bad)

if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 0)
