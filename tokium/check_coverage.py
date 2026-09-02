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

def check_contradictions(SP):
    """判定と G列/I列 の内部矛盾を検出する。

    ・架電可なのに G列が「確認不可」「対象外」のまま
    ・△→○ に回収した行なのに I列に金額の記載がない
    どちらも「結論だけ動かして根拠を書いていない」状態で、成果物として使えない。
    """
    import csv, re
    sys.path.insert(0, "/home/user/-/tokium")
    from verdict import build
    rows = list(csv.reader(open(f"{SP}/tokium.csv", encoding="utf-8-sig")))[1:]
    G = {i+2: (list(r)+[""]*8)[6] for i, r in enumerate(rows)}
    out = []
    for r in build():
        I = r["I列_検証結果"]
        if r["架電可"] == "○" and re.search(r"確認不可|対象外", G[r["行"]]) \
           and "G列訂正" not in I[:30] and not I.startswith("○ 回収"):
            out.append((r["行"], r["取引先名"], "架電可だがG列が確認不可/対象外のまま"))
        if r["最終判定"] == "架電可（回収）" and not re.search(r"\d[\d,\.]*\s*(億|兆|百万)", I):
            out.append((r["行"], r["取引先名"], "回収行だがI列に金額の記載がない"))
    return out

if __name__ == "__main__":
    SP = "/tmp/claude-0/-home-user--/fcda6a82-279b-5a30-a006-b52ce02ba704/scratchpad"
    ran = sys.argv[1:] or None      # 引数で「実行済みの波番号」を渡すと未実行分を除外
    p = check(SP)
    if ran:
        p = [x for x in p if x[0].lstrip("0") in {r.lstrip("0") for r in ran} or x[0] == "00"]
    con = check_contradictions(SP)
    if con:
        print(f"内部矛盾: {len(con)}行")
        for n, nm, msg in con[:10]: print(f"  行{n} {nm[:22]} — {msg}")
    hard = [x for x in p if x[2] != "未実行または出力欠落"] + con
    print(f"チェック対象の不整合: {len(p)}件（うち行数・行番号の異常 {len(hard)}件）")
    for w, b, msg, ni, no in p:
        print(f"  波{w} blk{b}: 入力{ni}行 出力{no} — {msg}")
    sys.exit(1 if hard else 0)
