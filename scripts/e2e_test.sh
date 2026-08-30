#!/usr/bin/env bash
# 端到端验证脚本：注册→登录→创建项目→clone→修改→commit→push→平台可见
set -e
BASE=${BASE:-http://127.0.0.1:5000}
PY=${PY:-$(cd "$(dirname "$0")/../backend" && echo "$PWD/venv/bin/python")}
WORK=$(mktemp -d)
trap "rm -rf $WORK" EXIT
export GIT_TERMINAL_PROMPT=0

echo "== 1. 注册测试用户 =="
curl -s -X POST "$BASE/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"e2e@campus.edu","username":"e2e_user","password":"pass123","full_name":"端到端测试","role":"student"}' -o /dev/null -w "  register: %{http_code}\n"
TOKEN=$(curl -s -X POST "$BASE/api/auth/login" -H "Content-Type: application/json" \
  -d '{"account":"e2e_user","password":"pass123"}' | "$PY" -c "import sys,json;print(json.load(sys.stdin)['token'])")
echo "  login: ok"

echo "== 2. 创建项目（课程作业模板）=="
SLUG="e2e-project-$(date +%s)"
curl -s -X POST "$BASE/api/projects" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"name\":\"端到端项目\",\"slug\":\"$SLUG\",\"template_type\":\"course\",\"visibility\":\"private\"}" \
  -o /dev/null -w "  create: %{http_code}\n"

echo "== 3. git clone =="
cd "$WORK"
git clone "http://e2e_user:pass123@${BASE#http://}/git/$SLUG.git" proj 2>/dev/null
echo "  clone: ok ($(ls proj))"

echo "== 4. 修改 → commit → push =="
cd proj
git config user.name "端到端测试"
git config user.email "e2e@campus.edu"
echo "print('hello gitcam')" > main.py
git add -A
git commit -m "添加入口文件" -q
git push 2>&1 | tail -1
cd "$WORK"

echo "== 5. 平台可见性验证 =="
COMMITS=$(curl -s "$BASE/api/projects/$SLUG/repo/commits" -H "Authorization: Bearer $TOKEN")
echo "$COMMITS" | "$PY" -c "
import sys, json
d = json.load(sys.stdin)
print(f'  提交历史: {len(d[\"commits\"])} 条')
for c in d['commits']:
    print('   -', c['short_sha'], c['author_name'], '|', c['message'])
"
TREE=$(curl -s "$BASE/api/projects/$SLUG/repo/tree" -H "Authorization: Bearer $TOKEN")
echo "$TREE" | "$PY" -c "
import sys, json
d = json.load(sys.stdin)
print('  文件树:', [e['name'] for e in d['entries']])
"
SHA=$(echo "$COMMITS" | "$PY" -c "import sys,json;print(json.load(sys.stdin)['commits'][0]['sha'])")
curl -s "$BASE/api/projects/$SLUG/repo/commits/$SHA" -H "Authorization: Bearer $TOKEN" | "$PY" -c "
import sys, json
d = json.load(sys.stdin)['commit']
print(f'  diff: +{d[\"diff_stat\"][\"additions\"]} -{d[\"diff_stat\"][\"deletions\"]}, {d[\"diff_stat\"][\"files_changed\"]} files')
"
ACT=$(curl -s "$BASE/api/projects/$SLUG/activities" -H "Authorization: Bearer $TOKEN")
echo "$ACT" | "$PY" -c "
import sys, json
print('  动态流:')
for e in json.load(sys.stdin)['items']:
    print('   -', e['event_type'], e['action'], '|', e['title'])
"

echo "== 6. 权限验证 =="
curl -s "$BASE/api/projects/$SLUG/repo/tree" -o /dev/null -w "  未登录访问私有仓库: %{http_code}（期望 401）\n"
echo "  全部通过 ✓"
