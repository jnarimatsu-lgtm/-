#!/bin/sh
# 1波終わるごとの定型処理: 整合チェック -> 結果集約 -> コミット
# 使い方: sh tokium/after_wave.sh <完了した波番号...>
set -e
cd /home/user/-
python3 tokium/check_coverage.py "$@" || echo "!! 整合エラーあり — resume が必要"
python3 - <<'PY'
import json,csv,sys,glob
from collections import Counter
sys.path.insert(0,"/home/user/-/tokium")
from normalize_results import load_all, normalize
SP="/tmp/claude-0/-home-user--/fcda6a82-279b-5a30-a006-b52ce02ba704/scratchpad"
rows=list(csv.reader(open(f"{SP}/tokium.csv",encoding="utf-8-sig")))[1:]
R={i+2:(list(r)+[""]*8)[:8] for i,r in enumerate(rows)}
out=load_all(SP)
for x in out.values(): x["I"],_=normalize(x["I"])
def kind(I):
    if I.startswith("○ 妥当（G列訂正"): return "○維持(G列訂正)"
    if I.startswith("○"): return "○維持"
    if I.startswith("×"): return "×要修正"
    if I.startswith("△"): return "△要再確認"
    if I.startswith("未検証"): return "未検証"
    return "保留"
c=Counter(kind(v["I"]) for v in out.values())
ng=c.get("△要再確認",0)+c.get("×要修正",0)+c.get("保留",0)+c.get("未検証",0)
print(f"累計 {len(out)}/4422行 ({len(out)/4422*100:.1f}%)  架電不可 {ng} ({ng/len(out)*100:.1f}%)  要是正 {ng+c.get('○維持(G列訂正)',0)}")
print("  " + " / ".join(f"{k} {v}" for k,v in c.most_common()))
p="/home/user/-/tokium/results/IJ_paste.csv"
with open(p,"w",encoding="utf-8-sig",newline="") as fh:
    w=csv.writer(fh); w.writerow(["行","取引先ID","法人番号","取引先名","元H判定","I列_検証結果","J列_ソース"])
    for n in sorted(out):
        r=R[n]; w.writerow([n,r[0],r[1],r[2],r[7][:1],out[n]["I"],out[n].get("J","")])
PY
git add -A
git -c user.name="Claude" -c user.email="noreply@anthropic.com" \
    commit -q -m "Verification results through wave $(echo "$@" | awk '{print $NF}')" \
    -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UyEh5Ye6BaH5LywWUyJuxb" 2>/dev/null || echo "(変更なし)"
git push -q -u origin claude/verify-columns-g-h-d8cdz9
