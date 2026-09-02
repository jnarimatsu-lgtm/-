# -*- coding: utf-8 -*-
"""I列から「最終的に架電してよいか」を一意に決める。

I列の「○」は層によって2つの意味で使われている：
  - 「○ 妥当」＝ **既存のG/H列の記載が正しい**（元判定を支持する）
  - 「○ 回収」＝ **架電可に戻した**（元△/×を覆した）
元判定が△や×の行で「○ 妥当」は「その除外が正しい」を意味するため、
これを架電可と数えると RULES §1 の無報酬事故を作り込むことになる。
実際、加藤化学（§6-6 が名指しで「確認不可が正解」とした企業）と
カーギルジャパン合同会社（§3-6 法人格NG）が架電可に化けていた。
"""
import csv, re, sys
sys.path.insert(0, "/home/user/-/tokium")
from normalize_results import load_all, normalize

SP = "/tmp/claude-0/-home-user--/fcda6a82-279b-5a30-a006-b52ce02ba704/scratchpad"

def verdict(orig_mark, I):
    """(架電可か, 判定ラベル) を返す。orig_mark は元H列の先頭記号。"""
    I = (I or "").strip()
    if re.match(r"^○\s*回収", I):
        return True, "架電可（回収）"
    if re.match(r"^○", I):
        # 「○ 妥当」＝既存記載を支持 → 元判定に従う
        if orig_mark == "○":
            return True, ("架電可（G列訂正あり）" if "G列訂正" in I[:24] else "架電可")
        return False, f"架電不可（元{orig_mark}판정が妥当と確認）".replace("판정", "判定")
    if I.startswith("×"): return False, "架電不可（×要修正）"
    if I.startswith("△"): return False, "架電不可（△要再確認）"
    if I.startswith("未検証"): return False, "未検証"
    return False, "架電不可（保留）"

def build():
    rows = list(csv.reader(open(f"{SP}/tokium.csv", encoding="utf-8-sig")))[1:]
    R = {i+2: (list(r)+[""]*8)[:8] for i, r in enumerate(rows)}
    out = load_all(SP)
    for x in out.values(): x["I"], _ = normalize(x["I"])
    res = []
    for n in sorted(out):
        r = R[n]; ok, label = verdict(r[7][:1], out[n]["I"])
        res.append({"行": n, "取引先ID": r[0], "法人番号": r[1], "取引先名": r[2],
                    "元H判定": r[7][:1], "最終判定": label, "架電可": "○" if ok else "×",
                    "I列_検証結果": out[n]["I"], "J列_ソース": out[n].get("J", "")})
    return res

if __name__ == "__main__":
    from collections import Counter
    res = build()
    c = Counter(r["最終判定"] for r in res)
    ok = sum(1 for r in res if r["架電可"] == "○")
    summary = (f"検証済み {len(res)}/4422行 ({len(res)/4422*100:.1f}%) → "
               f"架電可 {ok}行 ({ok/len(res)*100:.1f}%) / 架電不可 {len(res)-ok}行")
    detail = "\n".join(f"   {k:<28}{v:>5}" for k, v in c.most_common())
    open("/home/user/-/tokium/results/SUMMARY.txt", "w", encoding="utf-8").write(summary + "\n" + detail + "\n")
    print(summary)
    p = "/home/user/-/tokium/results/IJ_paste.csv"
    with open(p, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(res[0].keys())); w.writeheader(); w.writerows(res)
