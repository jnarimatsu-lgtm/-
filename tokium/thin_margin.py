# -*- coding: utf-8 -*-
"""基準300億円に対する余裕が薄い○行の抽出（監視リスト）。

架電可否は現時点で○でも、基準ギリギリの行は次期決算で条件外に転落しうる。
RULES §1 の「アポインターが無報酬になる」事故を先回りして潰すための一覧。

金額は原則 G列から取る。I列は「G列訂正：」が明示されている場合のみ、
訂正後の金額を優先する（I列本文にはルール文言の「300億」が頻出するため、
素朴に最初の億円表記を拾うと誤検出する）。
"""
import csv, json, re, sys
sys.path.insert(0, "/home/user/-/tokium")
from normalize_results import load_all, normalize
from audit_gh import parse_oku

SP = "/tmp/claude-0/-home-user--/fcda6a82-279b-5a30-a006-b52ce02ba704/scratchpad"

def corrected_amount(I, G):
    """I列にG列訂正が示されていればその金額、なければG列の金額。"""
    m = re.search(r"G列訂正[：:](.{0,160})", I)
    if m:
        # 訂正本文から最初の金額を取る。ただし基準値そのもの(300億)は除く
        for cand in re.finditer(r"(\d[\d,]*(?:\.\d+)?)\s*(?:兆\d[\d,]*(?:\.\d+)?億|兆|億|百万)円", m.group(1)):
            v = parse_oku(cand.group(0))
            if v and abs(v - 300.0) > 0.01:
                return v, "I列(訂正)"
    v = parse_oku(G)
    return (v, "G列") if v else (None, None)

def main(lo=300.0, hi=400.0):
    rows = list(csv.reader(open(f"{SP}/tokium.csv", encoding="utf-8-sig")))[1:]
    R = {i+2: (list(r)+[""]*8)[:8] for i, r in enumerate(rows)}
    out = load_all(SP)
    for x in out.values(): x["I"], _ = normalize(x["I"])
    res = []
    for n, v in sorted(out.items()):
        if not v["I"].startswith("○"): continue
        amt, src = corrected_amount(v["I"], R[n][6])
        if amt is None or not (lo <= amt < hi): continue
        res.append({"行": n, "取引先名": R[n][2], "法人番号": R[n][1],
                    "採用値_億円": round(amt, 2), "金額の出所": src,
                    "余裕率": round((amt-300)/300*100, 1),
                    "G列": R[n][6], "I列": v["I"][:200]})
    return res

if __name__ == "__main__":
    res = main()
    print(f"300〜400億円の○行: {len(res)}件（350億未満 {sum(1 for r in res if r['採用値_億円']<350)}件）\n")
    for r in sorted(res, key=lambda x: x["採用値_億円"])[:20]:
        print(f"  {r['採用値_億円']:>8.2f}億 (余裕{r['余裕率']:>5.1f}%) 行{r['行']:<5} {r['取引先名'][:28]:<30} [{r['金額の出所']}]")
    with open("/home/user/-/tokium/results/thin_margin_watchlist.csv", "w",
              encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(res[0].keys()))
        w.writeheader(); w.writerows(sorted(res, key=lambda x: x["採用値_億円"]))
    print(f"\n-> tokium/results/thin_margin_watchlist.csv")
