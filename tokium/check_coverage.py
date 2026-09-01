# -*- coding: utf-8 -*-
"""検証カバレッジの整合チェック。

RULES §5-2 が警告する「書き戻し行数の不一致」を毎波検出するための番人。
入力ブロックの行数と出力の要素数が一致するか、出力が欠落していないか、
行番号が入力とずれていないかを見る。API断でブロックが落ちても気付けるようにする。
"""
import json, glob, os, re, sys

def check(SP):
    problems = []
    for inf in sorted(glob.glob(f"{SP}/waves/w*_b*.json")):
        m = re.search(r"w(\d+)_b(\d+)\.json$", os.path.basename(inf))
        if not m: continue
        w, b = m.group(1), m.group(2)
        outf = f"{SP}/waves/out_w{w}_b{b}.json"
        src = json.load(open(inf, encoding="utf-8"))
        if not os.path.exists(outf):
            problems.append((w, b, "未実行または出力欠落", len(src), None)); continue
        dst = json.load(open(outf, encoding="utf-8"))
        if len(src) != len(dst):
            problems.append((w, b, "行数不一致", len(src), len(dst))); continue
        srows = [x["行"] for x in src]; drows = [x["行"] for x in dst]
        if srows != drows:
            problems.append((w, b, f"行番号がずれている 入力先頭{srows[:3]} 出力先頭{drows[:3]}",
                             len(src), len(dst)))
    return problems

if __name__ == "__main__":
    SP = "/tmp/claude-0/-home-user--/fcda6a82-279b-5a30-a006-b52ce02ba704/scratchpad"
    ran = sys.argv[1:] or None      # 引数で「実行済みの波番号」を渡すと未実行分を除外
    p = check(SP)
    if ran:
        p = [x for x in p if x[0].lstrip("0") in {r.lstrip("0") for r in ran} or x[0] == "00"]
    hard = [x for x in p if x[2] != "未実行または出力欠落"]
    print(f"チェック対象の不整合: {len(p)}件（うち行数・行番号の異常 {len(hard)}件）")
    for w, b, msg, ni, no in p:
        print(f"  波{w} blk{b}: 入力{ni}行 出力{no} — {msg}")
    sys.exit(1 if hard else 0)
