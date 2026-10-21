#!/usr/bin/env bash
# Open the upstream-change issue with the report, or comment on the one already open (roadmap item 2.1).
set -euo pipefail
gh label create upstream-change --color FBCA04 --description "voynich.nu serves a file that differs from its pin" 2>/dev/null || true
open=$(gh issue list --label upstream-change --state open --json number --jq '.[0].number')
if [ -n "$open" ]; then
  gh issue comment "$open" --body-file upstream_report.md
else
  gh issue create --title "Upstream source changed on voynich.nu" --label upstream-change --body-file upstream_report.md
fi
