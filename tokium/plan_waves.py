# -*- coding: utf-8 -*-
"""全4,422行をリスク層に分け、WebSearch予算(200/実行)に収まる波に割り付ける。

層ごとに1行あたりの検索予算を変えることで、実行回数を圧縮する。
高リスク(子会社への連結値適用・catr.jp依存)は厚く、法人格NGが自明な行は薄く。
"""
import csv, json, os, re, sys
from collections import Counter

SP = "/tmp/claude-0/-home-user--/fcda6a82-279b-5a30-a006-b52ce02ba704/scratchpad"
NG_KAKU = ["合同会社","有限会社","信用金庫","信用組合","医療法人","社会福祉法人","農業協同組合",
           "生活協同組合","相互会社","一般社団法人","一般財団法人","財団法人","独立行政法人",
           "合資会社","合名会社","労働金庫","共済組合"]
SEARCH_BUDGET = 200          # 1ワークフロー実行あたりのWebSearch上限
BLOCKS_PER_RUN = 5           # 1実行あたりの並列ブロック数

def tier(n, r, risk_scores):
    name, G, H = r[2], r[6], r[7]
    mark = H[:1]
    if mark == "×" and any(k in name for k in NG_KAKU):
        return "T4_法人格NG", 0.3      # 社名で自明。検索ほぼ不要
    if mark == "○":
        s = risk_scores.get(n, 0)
        return ("T1_高リスク○", 3.0) if s >= 6 else ("T2_通常○", 2.0)
    if mark == "△":
        return "T3_確認不可", 2.0        # 1次が諦めすぎていないかの回収
    return "T5_その他×", 1.0

def main():
    rows = list(csv.reader(open(f"{SP}/tokium.csv", encoding="utf-8-sig")))[1:]
    R = {i+2: (list(r)+[""]*8)[:8] for i, r in enumerate(rows)}
    risk = {x["行"]: x["score"] for x in json.load(open(f"{SP}/risk_rows.json", encoding="utf-8"))}
    done = set(range(2, 62))                                   # パイロット済み
    for f in ["w2/in_00.json","w2/in_01.json","w2/in_02.json","w2/in_03.json","w2/in_04.json"]:
        p = f"{SP}/{f}"
        if os.path.exists(p):
            done |= {x["行"] for x in json.load(open(p, encoding="utf-8"))}   # ウェーブ2

    buckets = {}
    for n, r in R.items():
        if n in done: continue
        t, cost = tier(n, r, risk)
        buckets.setdefault((t, cost), []).append(n)

    print(f"検証済み(除外): {len(done)}行\n")
    print(f"{'層':<16}{'行数':>7}{'検索/行':>9}{'行/実行':>9}{'実行回数':>9}")
    print("-" * 52)
    waves = []
    total_runs = 0
    for (t, cost), ns in sorted(buckets.items()):
        per_run = int(SEARCH_BUDGET / cost)
        per_run = (per_run // BLOCKS_PER_RUN) * BLOCKS_PER_RUN   # ブロック数で割り切る
        runs = -(-len(ns) // per_run)
        total_runs += runs
        print(f"{t:<16}{len(ns):>7}{cost:>9}{per_run:>9}{runs:>9}")
        for i in range(0, len(ns), per_run):
            waves.append({"tier": t, "cost": cost, "rows": ns[i:i+per_run]})
    print("-" * 52)
    print(f"{'合計':<16}{sum(len(v) for v in buckets.values()):>7}{'':>9}{'':>9}{total_runs:>9}")

    os.makedirs(f"{SP}/waves", exist_ok=True)
    for wi, w in enumerate(waves):
        ns = w["rows"]
        per_blk = -(-len(ns) // BLOCKS_PER_RUN)
        w["blocks"] = 0
        for bi in range(0, len(ns), per_blk):
            chunk = ns[bi:bi+per_blk]
            data = [{"行": n, "リスクスコア": risk.get(n, 0), "法人番号": R[n][1], "取引先名": R[n][2],
                     "Webサイト": R[n][3], "E列_SF売上レンジ": R[n][4],
                     "G列_本来の売上高": R[n][6], "H列_ソース判定": R[n][7]} for n in chunk]
            json.dump(data, open(f"{SP}/waves/w{wi:02d}_b{w['blocks']}.json", "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            w["blocks"] += 1
    json.dump([{"wave": i, "tier": w["tier"], "cost": w["cost"],
                "blocks": w["blocks"], "n": len(w["rows"])} for i, w in enumerate(waves)],
              open(f"{SP}/waves/manifest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n生成: {len(waves)}波 -> {SP}/waves/")

if __name__ == "__main__":
    main()
