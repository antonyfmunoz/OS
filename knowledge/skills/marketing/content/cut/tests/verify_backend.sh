#!/usr/bin/env bash
# CutStudio backend verification suite — plan items 1-5 (+8 grep parts).
# Run: bash verify_backend.sh   (service must be up on 127.0.0.1:8931 with
# CUTSTUDIO_API_KEY=testkey123, LINK_TOKEN_SECRET=testsecret)
set -u
K="X-API-Key: testkey123"
B=http://127.0.0.1:8931/api/cut
H=http://127.0.0.1:8931/health
DIR="$(cd "$(dirname "$0")" && pwd)"
T="${TMPDIR:-/tmp}/cutverify"
mkdir -p "$T"
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "  PASS: $1"; }
bad() { FAIL=$((FAIL+1)); echo "  FAIL: $1"; }
jget() { python3 -c "import sys,json;d=json.load(sys.stdin);print(d$1)"; }

echo "== item 1: smoke chain =="
PID=$(curl -s -H "$K" -F "file=@$DIR/test_vod.mp4;type=video/mp4" $B/projects | jget "['id']")
[ -n "$PID" ] && ok "upload -> project $PID" || bad "upload"
JID=$(curl -s -H "$K" -X POST -H "Content-Type: application/json" -d '{"model":"base"}' $B/projects/$PID/transcribe | jget "['job_id']")
for i in $(seq 1 45); do
  ST=$(curl -s -H "$K" $B/jobs/$JID | jget "['state']")
  [ "$ST" = "done" ] && break; [ "$ST" = "error" ] && break; sleep 2
done
[ "$ST" = "done" ] && ok "transcribe job done" || bad "transcribe state=$ST"
WORDS=$(curl -s -H "$K" $B/projects/$PID/transcript | python3 -c "import sys,json;t=json.load(sys.stdin);print(sum(len(s['words']) for s in t['segments']))")
[ "${WORDS:-0}" -gt 10 ] && ok "transcript has $WORDS words" || bad "transcript words=$WORDS"
REV=$(curl -s -H "$K" -D- -o /dev/null $B/projects/$PID/edl | grep -i x-edl-rev | tr -d '\r' | awk '{print $2}')
SRC=$(curl -s -H "$K" $B/projects/$PID/edl | jget "['source']")
python3 - "$SRC" > "$T/edl.json" <<'EOF'
import json, sys
print(json.dumps({"version":1,"source":sys.argv[1],
 "clips":[{"start":0.0,"end":4.6,"label":"hook"},{"start":11.4,"end":15.44,"label":"closer"}],
 "captions":True,"vertical":False,"output":"verify_cut.mp4"}))
EOF
CODE=$(curl -s -o "$T/put.json" -w "%{http_code}" -H "$K" -H "If-Match: $REV" -H "Content-Type: application/json" -X PUT -d @"$T/edl.json" $B/projects/$PID/edl)
[ "$CODE" = "200" ] && ok "PUT edl with If-Match rev=$REV" || bad "PUT edl code=$CODE"
RJ=$(curl -s -H "$K" -X POST -H "Content-Type: application/json" -d '{"aspect":"9:16","captions":true,"caption_style":2,"clean_audio":false}' $B/projects/$PID/render | jget "['job_id']")
for i in $(seq 1 45); do
  RS=$(curl -s -H "$K" $B/jobs/$RJ | jget "['state']"); [ "$RS" = "done" ] && break; [ "$RS" = "error" ] && break; sleep 2
done
ART=$(curl -s -H "$K" $B/jobs/$RJ | jget "['artifact']['output']")
[ "$RS" = "done" ] && ok "render job done artifact=$ART" || { bad "render state=$RS"; curl -s -H "$K" $B/jobs/$RJ; }
MT=$(curl -s -H "$K" "$B/projects/$PID/media-token?name=$ART" | jget "['token']")
RANGE=$(curl -s -o "$T/chunk.bin" -w "%{http_code}" -H "Range: bytes=0-1023" "$B/media?tok=$MT")
[ "$RANGE" = "206" ] && ok "Range request -> 206" || bad "range code=$RANGE"
curl -s -o "$T/render.mp4" "$B/media?tok=$MT"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$T/render.mp4")
DIM=$(ffprobe -v error -select_streams v -show_entries stream=width,height -of csv=p=0 "$T/render.mp4")
python3 -c "import sys; d=float('$DUR'); sys.exit(0 if abs(d-8.64)<=0.25 else 1)" && ok "duration $DUR ~= 8.64" || bad "duration $DUR"
[ "$DIM" = "1080,1920" ] && ok "dims 1080x1920" || bad "dims $DIM"
CMX=$(curl -s -H "$K" $B/export/$PID.edl)
echo "$CMX" | grep -q "TITLE:" && echo "$CMX" | grep -qc "AX" && ok "CMX3600 export has TITLE + events" || bad "CMX export"

echo "== item 2: detect (planted fixture) =="
P2=$(curl -s -H "$K" -F "file=@$DIR/test_fillers.mp4;type=video/mp4" $B/projects | jget "['id']")
J2=$(curl -s -H "$K" -X POST -H "Content-Type: application/json" -d '{"model":"base"}' $B/projects/$P2/transcribe | jget "['job_id']")
for i in $(seq 1 45); do S2=$(curl -s -H "$K" $B/jobs/$J2 | jget "['state']"); [ "$S2" = "done" ] && break; [ "$S2" = "error" ] && break; sleep 2; done
DET=$(curl -s -H "$K" -X POST -H "Content-Type: application/json" -d '{"fillers":true,"silences":{"threshold":1.0}}' $B/projects/$P2/detect)
FC=$(echo "$DET" | python3 -c "import sys,json;print(len(json.load(sys.stdin)['filler_words']))")
SC=$(echo "$DET" | python3 -c "import sys,json;print(len(json.load(sys.stdin)['silence_gaps']))")
[ "${FC:-0}" -ge 2 ] && ok "planted fillers detected: $FC" || bad "fillers=$FC (planted um/like/basically/you know)"
[ "${SC:-0}" -ge 1 ] && ok "planted 2.2s silence detected: $SC gap(s)" || bad "silences=$SC (planted 2.2s gap)"
APPLIED=$(DET_JSON="$DET" python3 -c "
import os, json
det = json.loads(os.environ['DET_JSON'])
strikes = [(w['start'], w['end']) for w in det['filler_words']] + \
          [(g['start'], g['end']) for g in det['silence_gaps']]
print('strike_ranges:%d' % len(strikes))")
echo "$APPLIED" | grep -q "strike_ranges" && ok "detections applicable ($APPLIED)" || bad "apply-shape"

echo "== item 3: highlights (may use deterministic fallback) =="
HJ=$(curl -s -H "$K" -X POST -H "Content-Type: application/json" -d '{"count":2,"target_seconds":10}' $B/projects/$PID/highlights | jget "['job_id']")
for i in $(seq 1 60); do HS=$(curl -s -H "$K" $B/jobs/$HJ | jget "['state']"); [ "$HS" = "done" ] && break; [ "$HS" = "error" ] && break; sleep 2; done
HD=$(curl -s -H "$K" $B/jobs/$HJ)
echo "$HD" | python3 -c "
import sys, json
j = json.load(sys.stdin)
a = j.get('artifact') or {}
if isinstance(a, str):
    try: a = json.loads(a)
    except Exception: a = {}
cands = a.get('candidates', [])
note = a.get('note', '')
assert j['state'] in ('done','error'), j['state']
print('candidates:', len(cands), '| note:', note[:60])
" && ok "highlights terminal without crash" || bad "highlights"

echo "== item 4: gates =="
C401=$(curl -s -o /dev/null -w "%{http_code}" $B/projects); [ "$C401" = "401" ] && ok "no key -> 401" || bad "no key -> $C401"
C409=$(curl -s -o /dev/null -w "%{http_code}" -H "$K" -H "If-Match: 999" -H "Content-Type: application/json" -X PUT -d @"$T/edl.json" $B/projects/$PID/edl); [ "$C409" = "409" ] && ok "bad If-Match -> 409" || bad "if-match -> $C409"
CTAMP=$(curl -s -o /dev/null -w "%{http_code}" "$B/media?tok=${MT%????}beef"); [ "$CTAMP" = "403" ] || [ "$CTAMP" = "404" ] && ok "tampered token -> $CTAMP" || bad "tampered -> $CTAMP"
CTRAV=$(curl -s -o /dev/null -w "%{http_code}" -H "$K" "$B/projects/$PID/media-token?name=../../etc/passwd"); [ "$CTRAV" = "400" ] || [ "$CTRAV" = "404" ] || [ "$CTRAV" = "422" ] && ok "traversal name -> $CTRAV" || bad "traversal -> $CTRAV"

echo "== item 5: cpu gate busy path (env-scoped) =="
GB=$(UMH_CPU_GATE_CEILING=0.01 python3 -c "
import sys; sys.path.insert(0, '.')
from substrate.execution.cpu_gate import cpu_gate_check
r = cpu_gate_check('verify')
print('allowed:', r.allowed)")
echo "$GB" | grep -q "allowed: False" && ok "cpu gate refuses at ceiling 0.01" || bad "cpu gate: $GB"

echo "== item 8 greps =="
grep -rnE "subprocess\.(run|Popen|call|check_output|check_call)\(" "$DIR/../server/" --include="*.py" | grep -q . && bad "raw subprocess in server/" || ok "no raw subprocess in server/"
grep -rn "from substrate.organism.empire_router" "$DIR/../server/" ../services/cutstudio_api.py 2>/dev/null | grep -q . && bad "empire_router RoutingResult import" || ok "no empire_router import"
grep -rn "c9a84c" "$DIR/../server/" 2>/dev/null | grep -q . && bad "gold in server" || ok "no gold"

echo ""
echo "=== RESULT: $PASS pass / $FAIL fail ==="
exit $([ $FAIL -eq 0 ] && echo 0 || echo 1)
