# -*- coding: utf-8 -*-
"""検索枠切れで未検証のまま残った行を集め、再走用の波を作る。
並列数を上げるとWebSearchの200回枠を奪い合い、末尾のブロックが丸ごと0クエリになる。
これは検出できる（エージェントが「未検証（検索枠切れ）」と自己申告する）ので、
毎回この掃き出しを回して取りこぼしを繰り越す。"""
import csv, json, sys, os

SP = "/tmp/claude-0/-home-user--/fcda6a82-279b-5a30-a006-b52ce02ba704/scratchpad"

def main(wave=97, blocks=4):
    rows = [r for r in csv.DictReader(open("tokium/results/IJ_paste_FULL.csv", encoding="utf-8-sig"))
            if r["最終判定"] == "未検証" and r["I列_検証結果"]]
    if not rows:
        print("検索枠切れの未検証行なし"); return 0
    src = list(csv.reader(open("tokium/raw/source_4422rows.csv", encoding="utf-8-sig")))[1:]
    out = []
    for r in rows:
        n = int(r["行"]); s = (list(src[n - 2]) + [""] * 8)[:8]
        out.append({"行": n, "リスクスコア": 99, "法人番号": s[1], "取引先名": s[2],
                    "Webサイト": s[3], "E列_SF売上レンジ": s[4],
                    "G列_本来の売上高": s[5], "H列_ソース判定": s[7]})
    nb = min(blocks, len(out))
    for b in range(nb):
        chunk = out[b::nb]
        json.dump(chunk, open(f"{SP}/waves/w{wave}_b{b}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    m = json.load(open(f"{SP}/waves/manifest.json", encoding="utf-8"))
    m = [w for w in m if w["wave"] != wave]
    m.append({"wave": wave, "tier": "T3_確認不可", "cost": 4.0, "blocks": nb, "n": len(out)})
    json.dump(m, open(f"{SP}/waves/manifest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"波{wave}: 未検証{len(out)}行を{nb}ブロックで再走用に切り出した")
    print("  ", [r["行"] for r in out])
    return len(out)

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 97)
