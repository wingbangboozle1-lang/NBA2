#!/bin/bash
# Baseline checker chain in committed CI order (publish-parity.yml "Rebuild every generated tree")
cd /home/user/NBA2
run() { name="$1"; shift; echo "=== $name ==="; "$@" > "audit/session-f4a5531f/baseline/$name.log" 2>&1; echo "$name rc=$?"; }
run 01_build_site_data python -m nba2.pipeline.build_site_data
run 02_build_site     python -m nba2.pipeline.build_site
run 03_backtest_build python -m backtest.engine.build
run 04_v2_build       python -m nba2.v2
run 05_settlement     python -m nba2.settlement_page
run 06_v3_build       python -m nba2.v3
run 07_v4_build       python -m nba2.v4
run 08_v5_build       python -m nba2.v5
run 09_v6_build       python -m nba2.v6
run 10_v2_check       python -m nba2.v2.check
run 11_v3_check       python -m nba2.v3.check
run 12_lint           python -m nba2.pipeline.lint
run 13_links          python3 tools/check_links_all.py
run 14_seal_verify    python -c "from nba2.models import ledger as LD; import glob,json,pathlib,sys; ok=True
for f in sorted(glob.glob('data/raw/ledger/sealed-*.json')):
    p=pathlib.Path(f); good,stored,rec=LD.verify(p); n=json.loads(p.read_text())['header']['n_predictions']
    print(f'sealed {n:3d} predictions  {stored[:16]}  {\"VERIFIED\" if good else \"BROKEN\"}'); ok=ok and good
sys.exit(0 if ok else 1)"
run 15_v2_live        python -m nba2.v2.live
run 16_crosscheck     python3 tools/crosscheck_site.py
run 17_verify_site    python3 tools/verify_site.py
