#!/usr/bin/env python3
"""gitcam 接口压测脚本：并发测试核心接口，输出 QPS / p50 / p95。

用法：
    python scripts/benchmark.py [--concurrency 50] [--total 500] [--base http://127.0.0.1:5000]
"""

import argparse
import concurrent.futures
import json
import statistics
import sys
import time
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:5000"
SLUG = "admin-demo"
ADMIN = ("admin", "%bAnMeuwxksHKaPm")


def http_json(method, path, data=None, token=None, timeout=30):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode() or "{}")
        return time.perf_counter() - start, resp.status, payload
    except urllib.error.HTTPError as e:
        return time.perf_counter() - start, e.code, {}


def login():
    _, status, data = http_json("POST", "/api/auth/login", {"account": ADMIN[0], "password": ADMIN[1]})
    return data.get("token")


SCENARIOS = {
    "login": lambda t, b: http_json_impl("POST", "/api/auth/login", {"account": ADMIN[0], "password": ADMIN[1]}, base=b),
    "projects": lambda t, b: http_json_impl("GET", "/api/projects", token=t, base=b),
    "repo_tree": lambda t, b: http_json_impl("GET", f"/api/projects/{SLUG}/repo/tree", token=t, base=b),
    "commits": lambda t, b: http_json_impl("GET", f"/api/projects/{SLUG}/repo/commits", token=t, base=b),
    "posts": lambda t, b: http_json_impl("GET", f"/api/projects/{SLUG}/posts", token=t, base=b),
    "issues": lambda t, b: http_json_impl("GET", f"/api/projects/{SLUG}/issues", token=t, base=b),
}


def http_json_impl(method, path, data=None, token=None, base=BASE, timeout=30):
    url = f"{base}{path}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode() or "{}")
        return time.perf_counter() - start, resp.status, payload
    except urllib.error.HTTPError as e:
        return time.perf_counter() - start, e.code, {}


def http_json(method, path, data=None, token=None, timeout=30):
    return http_json_impl(method, path, data, token, BASE, timeout)


def login():
    _, status, data = http_json("POST", "/api/auth/login", {"account": ADMIN[0], "password": ADMIN[1]})
    return data.get("token")


def main():
    parser = argparse.ArgumentParser(description="gitcam API 压测")
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--total", type=int, default=500)
    parser.add_argument("--base", default=BASE)
    args = parser.parse_args()
    base = args.base
    http_json_global = {"BASE": base}

    token = login_impl(base)
    if not token:
        print("登录失败，无法压测"); sys.exit(1)
    print(f"压测目标: {base}  并发={args.concurrency}  每接口请求={args.total}\n")
    print(f"{'接口':<12}{'QPS':>10}{'p50(ms)':>10}{'p95(ms)':>10}{'错误':>6}{'耗时(s)':>10}")
    print("-" * 58)
    results = []
    for name, fn in SCENARIOS.items():
        r = run_scenario(name, fn, token, args.concurrency, args.total, base)
        results.append(r)
        print(f"{r['name']:<12}{r['qps']:>10}{r['p50_ms']:>10}{r['p95_ms']:>10}{r['errors']:>6}{r['elapsed_s']:>10}")
    avg_qps = round(sum(r["qps"] for r in results) / len(results), 1)
    print("-" * 58)
    print(f"{'平均':<12}{avg_qps:>10}")
    return results


def login_impl(base):
    url = f"{base}/api/auth/login"
    req = urllib.request.Request(
        url,
        data=json.dumps({"account": ADMIN[0], "password": ADMIN[1]}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode()).get("token")
    except Exception:
        return None


def run_scenario(name, fn, token, concurrency, total, base):
    latencies = []
    errors = 0
    lock = __import__("threading").Lock()

    def worker(_):
        nonlocal errors
        latency, status, _ = fn(token, base)
        with lock:
            latencies.append(latency * 1000)
            if status >= 400:
                errors += 1

    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        list(pool.map(worker, range(total)))
    elapsed = time.perf_counter() - start

    latencies.sort()
    qps = total / elapsed if elapsed else 0
    p50 = latencies[len(latencies) // 2] if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95) - 1] if latencies else 0
    return {
        "name": name,
        "total": total,
        "qps": round(qps, 1),
        "p50_ms": round(p50, 1),
        "p95_ms": round(p95, 1),
        "errors": errors,
        "elapsed_s": round(elapsed, 2),
    }


if __name__ == "__main__":
    main()
