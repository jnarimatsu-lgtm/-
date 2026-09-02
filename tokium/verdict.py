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

    # ---- 貼り付け用（全4,422行・欠番なし）----------------------------------
    # §5-2: 未検証行を詰めた表をそのまま貼ると、最初の欠番以降が1行ずつずれる。
    # 実際にこの事故が元データの2707〜2719行で起きているので、必ず全長で出す。
    rows = list(csv.reader(open(f"{SP}/tokium.csv", encoding="utf-8-sig")))[1:]
    byrow = {r["行"]: r for r in res}
    cols = list(res[0].keys())
    full = []
    for i, src in enumerate(rows):
        n = i + 2
        src = (list(src) + [""] * 8)[:8]
        r = byrow.get(n)
        if r is None:
            r = {k: "" for k in cols}
            r.update({"行": n, "取引先ID": src[0], "法人番号": src[1], "取引先名": src[2],
                      "元H判定": src[7][:1], "最終判定": "未検証", "架電可": ""})
        full.append(r)
    assert len(full) == len(rows) == 4422, f"行数不一致 {len(full)} != 4422"
    assert [r["行"] for r in full] == list(range(2, 4424)), "行番号が連番でない"
    for r in full:  # 取引先IDが元データと一致することを1行ずつ確認（§5-2のずれ検出）
        assert r["取引先ID"] == (list(rows[r["行"] - 2]) + [""])[0], f"行{r['行']} で取引先IDがずれている"
    # 判定にも出典の集合にも手を入れない。並び順だけを変える。
    def suspicious(u):
        m = re.search(r"/([^/]+)\.pdf$", u, re.I)
        if not m: return False
        stem = m.group(1).lower()
        if re.search(r"\d{4,}", stem): return False          # 日付・IDはCMS由来
        core = re.sub(r"^\d+|\d+$", "", stem)
        if re.search(r"\d", core): return False               # 内部に数字＝ハッシュ
        return bool(re.fullmatch(r"[a-z]{8,14}", core)) and len(re.findall(r"[aeiou]", core)) <= 1
    moved = 0
    for r in full:
        j = (r.get("J列_ソース") or "").strip()
        if not j: continue
        parts = [x.strip() for x in re.split(r"[;\s]+", j) if x.strip().startswith("http")]
        if len(parts) < 2: continue
        keep = [u for u in parts if not suspicious(u)]
        susp = [u for u in parts if suspicious(u)]
        if susp and keep:
            r["J列_ソース"] = "; ".join(keep + susp); moved += 1
    if moved: print(f"J列: 実在未確認のPDFを末尾に回した行 {moved}")

    pf = "/home/user/-/tokium/results/IJ_paste_FULL.csv"
    with open(pf, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(full)
    # I列・J列だけを切り出した、そのまま貼れる2列版
    pc = "/home/user/-/tokium/results/IJ_columns_only.csv"
    with open(pc, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh); w.writerow(["I列_検証結果", "J列_ソース"])
        for r in full: w.writerow([r["I列_検証結果"], r["J列_ソース"]])
    # §4 は H列を1セル300字以内と定める。I列に明文の制限はないが、アポインターが
    # セル内で読み切れるよう300字版も出す。判定記号とG列訂正は必ず先頭に来るので、
    # 文末（。）で切り詰めても「架電可否」と「採用値」は失われない。
    def shorten(t, lim=300):
        if len(t) <= lim: return t
        cut = t[:lim]
        i = cut.rfind("。")
        return (cut[:i + 1] if i >= lim // 2 else cut[:lim - 1]) + ("" if i >= lim // 2 else "…")
    # 綴りが乱打に見えるPDF（実在をWebFetchで確認できない）は、同じ行に別のURLが
    # あるなら末尾へ回す。アポインターが最初にクリックするURLは開けるものにする。

    ps = "/home/user/-/tokium/results/IJ_columns_short.csv"
    with open(ps, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh); w.writerow(["I列_検証結果", "J列_ソース"])
        for r in full: w.writerow([shorten(r["I列_検証結果"]), r["J列_ソース"]])
    print(f"貼り付け用: {pf} / {pc} / {ps} を全{len(full)}行で出力（欠番なし・ID照合済み）")
