#!/bin/sh
# コンテナ再起動で /tmp が飛んだときの復旧。git にある退避からスクラッチパッドを戻す。
# 波の入力（tier割当と行の担当）と元データはここにしか無いので、これが無いと再計画になる。
set -e
cd /home/user/-
SP=/tmp/claude-0/-home-user--/fcda6a82-279b-5a30-a006-b52ce02ba704/scratchpad
mkdir -p "$SP/waves"
cp tokium/waves_input/*.json "$SP/waves/"          # 波の入力 + manifest
cp tokium/raw/out_w*.json "$SP/waves/" 2>/dev/null || true   # 済んだ波の出力
cp tokium/raw/tokium_source_with_GH.csv "$SP/tokium.csv"
echo "復旧: 入力 $(ls $SP/waves/w*_b*.json | wc -l) / 出力 $(ls $SP/waves/out_w*.json 2>/dev/null | wc -l)"
python3 tokium/verdict.py | tail -2
