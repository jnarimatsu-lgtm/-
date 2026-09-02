#!/bin/sh
# 成果物の一括検査。納品前・波の取り込み後にこれを回す。
cd /home/user/-
echo "=========== TOKIUM 直アポ大 成果物チェック ==========="
echo
echo "--- 1. 進捗 ---"
cat tokium/results/SUMMARY.txt
echo
echo "--- 2. §3-6 法人格（社名ベース・決定的） ---"
python3 tokium/guard_legal_form.py | head -1
echo
echo "--- 3. 貼り付け整合（行数・連番・取引先ID） ---"
python3 - <<'PY'
import csv
f=list(csv.DictReader(open('tokium/results/IJ_paste_FULL.csv',encoding='utf-8-sig')))
src=list(csv.reader(open('tokium/raw/source_4422rows.csv',encoding='utf-8-sig')))[1:]
ns=[int(r['行']) for r in f]
ok = len(f)==4422 and ns==list(range(2,4424)) and all(r['取引先ID']==src[int(r['行'])-2][0] for r in f)
print("  %d行 / 連番 %s / ID一致 %s → %s" % (len(f), ns==list(range(2,4424)),
      all(r['取引先ID']==src[int(r['行'])-2][0] for r in f), "OK" if ok else "NG"))
PY
echo
echo "--- 4. 反証層が枯渇した波（1次判定が素通りしている） ---"
python3 tokium/check_starvation.py | tail -3
echo
echo "--- 5. 検索枠切れで未検証のまま残る行 ---"
python3 - <<'PY'
import csv
f=[r for r in csv.DictReader(open('tokium/results/IJ_paste_FULL.csv',encoding='utf-8-sig'))]
print("  自己申告の未検証: %d行 / 未処理（波が未実行）: %d行"
      % (sum(1 for r in f if r['最終判定']=='未検証' and r['I列_検証結果']),
         sum(1 for r in f if not r['I列_検証結果'])))
PY
echo
echo "--- 6. 要確認リスト（先方判断・薄いマージン） ---"
for f in thin_margin_watchlist.csv G_column_corrections.csv inferred_number_risk.json \
         reorganization_rows.json exclude_regardless_of_catr.json koukoku_bs_only.json \
         same_name_pairs.json gbiz_hojinbango_mismatch.json legal_form_violations.json; do
  p="tokium/results/$f"
  [ -f "$p" ] && printf "  %-38s %s件\n" "$f" "$(python3 -c "
import json,csv,sys
p='$p'
print(len(json.load(open(p,encoding='utf-8'))) if p.endswith('.json') else len(list(csv.DictReader(open(p,encoding='utf-8-sig')))))" 2>/dev/null)"
done
echo
echo "--- 7. 先方確認事項 ---"
grep -c '^## ' tokium/results/OPEN_QUESTIONS.md | sed 's/^/  見出し /'
