# -*- coding: utf-8 -*-
"""△→○ に回収された行のうち、反証段の裏取りが取れていない行を洗い出す。

T3層では検索枠切れで反証段が動けない波があり、「回収したが誰も検証していない○」が
残りうる。○は架電対象になるため、誤った回収は §1 の無報酬事故に直結する。
最終成果物に載せる前に、この一覧を潰す必要がある。
"""
import csv, json, re, sys
sys.path.insert(0, "/home/user/-/tokium")
from normalize_results import load_all, normalize

SP = "/tmp/claude-0/-home-user--/fcda6a82-279b-5a30-a006-b52ce02ba704/scratchpad"

# 反証段が「検証できなかった」と自認している表現
UNVERIFIED = [r"未検証", r"検索枠(が)?(切れ|枯渇|尽き)", r"追認も反証もできて",
              r"1クエリも(実行|打て)", r"200/200", r"確認できなかった"]

def main():
    rows = list(csv.reader(open(f"{SP}/tokium.csv", encoding="utf-8-sig")))[1:]
    R = {i+2: (list(r)+[""]*8)[:8] for i, r in enumerate(rows)}
    out = load_all(SP)
    for x in out.values(): x["I"], _ = normalize(x["I"])
    res = []
    for n, v in sorted(out.items()):
        if R[n][7][:1] != "△":        # 元が△＝T3で回収された行のみ
            continue
        if not v["I"].startswith("○"):
            continue
        flag = any(re.search(p, v["I"]) for p in UNVERIFIED)
        res.append({"行": n, "取引先名": R[n][2], "法人番号": R[n][1],
                    "未検証の疑い": "YES" if flag else "",
                    "I列": v["I"][:300], "J列": v.get("J", "")[:200]})
    return res

if __name__ == "__main__":
    res = main()
    sus = [r for r in res if r["未検証の疑い"]]
    print(f"△→○ に回収された行: {len(res)}行  / うち裏取りが疑わしい: {len(sus)}行")
    for r in sus:
        print(f"\n  [行{r['行']}] {r['取引先名']}")
        print(f"    {r['I列'][:200]}")
    p = "/home/user/-/tokium/results/recovered_rows_to_recheck.csv"
    with open(p, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(res[0].keys())); w.writeheader(); w.writerows(res)
    print(f"\n-> {p}")
