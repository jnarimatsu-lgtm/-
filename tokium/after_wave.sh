#!/bin/sh
# 1波終わるごとの定型処理: 整合チェック -> 結果集約 -> コミット
# 使い方: sh tokium/after_wave.sh <完了した波番号...>
set -e
cd /home/user/-
python3 tokium/check_coverage.py "$@" | tail -1 || echo "!! 整合エラーあり — resume が必要"
python3 tokium/verdict.py
# 生データをリポジトリへ退避（scratchpad は揮発する）
SP=/tmp/claude-0/-home-user--/fcda6a82-279b-5a30-a006-b52ce02ba704/scratchpad
mkdir -p tokium/raw
cp "$SP"/waves/out_w*.json tokium/raw/ 2>/dev/null || true

git add -A
git -c user.name="Claude" -c user.email="noreply@anthropic.com" \
    commit -q -m "Verification results through wave $(echo "$@" | awk '{print $NF}')" \
    -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UyEh5Ye6BaH5LywWUyJuxb" 2>/dev/null || echo "(変更なし)"
git push -q -u origin claude/verify-columns-g-h-d8cdz9
cat tokium/results/SUMMARY.txt
