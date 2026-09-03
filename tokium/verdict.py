# -*- coding: utf-8 -*-
"""I列から「最終的に架電してよいか」を一意に決める。

I列の「○」は層によって2つの意味で使われている：
  - 「○ 妥当」＝ **既存のG/H列の記載が正しい**（元判定を支持する）
  - 「○ 回収」＝ **架電可に戻した**（元△/×を覆した）
元判定が△や×の行の「○ 妥当」は**両方の意味で使われていた**：
  - (a)「その除外が正しい」… 例「○ 妥当（△判定が正しい）。…単体売上高は非公表」
  - (b)「この会社は基準を満たす。ただしG列に訂正が要る」… 例「○ 妥当（G列訂正：
        601億円（2026年3月期・単体））…単体601億で300億以上のため架電可」
当初は (a) と決め打ちしていたため、(b) の行を架電不可に倒していた。
東海旅客鉄道（連結営業収益2兆62億円）が架電不可になっていたのがそれで、
これは「実際はOKなのに確認不可」＝§1が実害と明記する側の誤りである。
そこで本文が基準充足を明言し、かつ除外を支持する語が無いときだけ架電可とする。
逆向きの取りこぼし（加藤化学＝§6-6が「確認不可が正解」と名指しした企業、
カーギルジャパン合同会社＝§3-6法人格NG）は NEG 側で確実に落とす。
"""
import csv, re, sys
sys.path.insert(0, "/home/user/-/tokium")
from normalize_results import load_all, normalize

SP = "/tmp/claude-0/-home-user--/fcda6a82-279b-5a30-a006-b52ce02ba704/scratchpad"

# 除外を支持する語。ひとつでもあれば架電不可（迷ったら落とす側に倒す）
NEG = re.compile(
    r"(△判定が正しい|×判定が正しい|確認不可で正しい|除外(結論)?は?維持|除外が正しい|除外という結論"
    r"|載せてはいけない|300億(円)?(を)?(下回|未満)|基準(を)?下回|基準未満|非公表|法人格(が)?消滅"
    r"|合併により消滅|裏取りは未了|§3-8|鮮度(切れ|外)|確認不可|判定は△|△のまま|×のまま|×は正しい"
    r"|既存の×|既存判定|法人格NG|一律NG|対象外|NG法人格|判定が反転する見込み|結論は不変"
    r"|結論は変わらない|判定は反転しない|単体(値|売上高)?(は|が)?(確認|取得)でき(ず|ない)"
    r"|単体実額は未取得|値は未確定)")
# 基準充足を明言する語
POS = re.compile(
    r"(架電可|架電OK|300億(円)?(以上|を(大きく|大幅に)?(超|上回))|基準(を)?(大幅|桁違いに)?(超過|上回|クリア)"
    r"|基準の約?[\d.,]+倍|判定は?(安定|不変|○で維持)|○(を)?維持)")


def verdict(orig_mark, I):
    """(架電可か, 判定ラベル) を返す。orig_mark は元H列の先頭記号。"""
    I = (I or "").strip()
    if re.match(r"^○\s*回収", I):
        return True, "架電可（回収）"
    if re.match(r"^○", I):
        if orig_mark == "○":
            return True, ("架電可（G列訂正あり）" if "G列訂正" in I[:24] else "架電可")
        # 元△/× の行は、本文が基準充足を明言し除外語が無いときだけ架電可に戻す
        if POS.search(I) and not NEG.search(I):
            return True, ("架電可（G列訂正あり）" if "G列訂正" in I[:40] else "架電可（回収）")
        return False, f"架電不可（元{orig_mark}判定が妥当と確認）"
    if I.startswith("×"): return False, "架電不可（×要修正）"
    if I.startswith("△"): return False, "架電不可（△要再確認）"
    if I.startswith("未検証"): return False, "未検証"
    return False, "架電不可（保留）"

def build():
    rows = list(csv.reader(open(f"{SP}/tokium.csv", encoding="utf-8-sig")))[1:]
    R = {i+2: (list(r)+[""]*8)[:8] for i, r in enumerate(rows)}
    out = load_all(SP)
    # 検索枠が回復したあとに掛け直した優先監査の結果で上書きする。
    # 波の出力より新しいので、再集計しても監査の結論が波の結論に戻らないようにする。
    import json, os
    ovp = "/home/user/-/tokium/raw/audit_overrides.json"
    if os.path.exists(ovp):
        for k, v in json.load(open(ovp, encoding="utf-8")).items():
            n = int(k)
            if n in out:
                out[n]["I"] = v["I"]
                if v.get("J"): out[n]["J"] = v["J"]
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
    def unstable(u):
        """CMSのアップロード置き場より、IRトップや適時開示のURLを先に出す。
        綴りからPDFの実在を当てることはできない（WebFetchが遮断されていて確認不能で、
        pamphlet.pdf と 2ggeghasdw.pdf は母音比が同じ）。そこで綴りは見ず、
        経路の安定性だけで並べる。差し替え・整理で消えやすいのは uploads 配下。"""
        return bool(re.search(r"/wp-content/uploads/|/wp/wp-content/|/uploads/\d{4}/", u))
    moved = 0
    for r in full:
        j = (r.get("J列_ソース") or "").strip()
        if not j: continue
        parts = [x.strip() for x in re.split(r"[;\s]+", j) if x.strip().startswith("http")]
        if len(parts) < 2: continue
        keep = [u for u in parts if not unstable(u)]
        late = [u for u in parts if unstable(u)]
        if late and keep and parts != keep + late:
            r["J列_ソース"] = "; ".join(keep + late); moved += 1
    if moved: print(f"J列: CMSアップロード配下のURLを末尾に回した行 {moved}")

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
