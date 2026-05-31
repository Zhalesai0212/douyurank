#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
斗鱼主播等级爬虫 - 功能测试套件
Douyu Streamer Level Scraper - Test Suite

测试范围:
1. 文件存在性检查
2. scraper.py 语法检查
3. index.html 结构完整性检查
4. douyu API 连通性测试 (mixList + betard)
5. 完整流水线测试 (3页数据，端到端)
6. JSON 输出格式验证
"""

import asyncio
import json
import os
import sys
import time

# 确保 UTF-8 输出
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PASS_COUNT = 0
FAIL_COUNT = 0
SKIP_COUNT = 0


def test_header(name: str):
    """打印测试模块标题"""
    print()
    print("=" * 60)
    print(f"  {name}")
    print("=" * 60)


def check(name: str, condition: bool, detail: str = "") -> bool:
    """记录测试结果"""
    global PASS_COUNT, FAIL_COUNT, SKIP_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"  [PASS] {name}")
    else:
        FAIL_COUNT += 1
        print(f"  [FAIL] {name}" + (f" - {detail}" if detail else ""))
    return condition


def skip(name: str, reason: str = ""):
    """跳过测试"""
    global SKIP_COUNT
    SKIP_COUNT += 1
    print(f"  [SKIP] {name}" + (f" - {reason}" if reason else ""))


# ================================================================
# Test 1: 文件存在性检查
# ================================================================
def test_file_existence():
    test_header("Test 1: File Existence Check")

    files = [
        ("scraper.py", "Main scraper script"),
        ("index.html", "Frontend display page"),
        ("requirements.txt", "Python dependencies"),
    ]
    for filename, desc in files:
        path = os.path.join(TEST_DIR, filename)
        check(f"{filename} ({desc})", os.path.isfile(path),
              f"File not found: {path}")


# ================================================================
# Test 2: Python 语法检查
# ================================================================
def test_python_syntax():
    test_header("Test 2: Python Syntax Check")

    import py_compile
    scraper_path = os.path.join(TEST_DIR, "scraper.py")
    try:
        py_compile.compile(scraper_path, doraise=True)
        check("scraper.py syntax", True)
    except py_compile.PyCompileError as e:
        check("scraper.py syntax", False, str(e))


# ================================================================
# Test 3: HTML 结构完整性检查
# ================================================================
def test_html_structure():
    test_header("Test 3: HTML Structure Check")

    html_path = os.path.join(TEST_DIR, "index.html")
    if not os.path.isfile(html_path):
        skip("index.html structure", "File not found")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    checks = [
        ("DOCTYPE declaration", "<!DOCTYPE html>" in content),
        ("html tag", "<html" in content),
        ("head tag", "<head>" in content or "<head " in content),
        ("head close", "</head>" in content),
        ("body tag", "<body>" in content or "<body " in content),
        ("body close", "</body>" in content),
        ("html close", "</html>" in content),
        ("title tag", "<title>" in content),
        ("charset meta", 'charset="UTF-8"' in content or "charset='UTF-8'" in content),
        ("table element", "<table" in content),
        ("tbody element", "<tbody" in content),
        ("script block", "<script>" in content or "<script " in content),
        ("fetch API call", "fetch(" in content),
        ("rank logic", "rank" in content.lower()),
        ("level logic", "level" in content.lower()),
        ("nickname field", "nickname" in content.lower()),
        ("category field", "category" in content.lower()),
        ("CSS styles", "<style>" in content or "<style " in content),
        ("responsive CSS", "@media" in content),
    ]

    for name, condition in checks:
        check(f"  {name}", condition)


# ================================================================
# Test 4: API 连通性测试
# ================================================================
async def test_api_connectivity():
    test_header("Test 4: Douyu API Connectivity")

    try:
        import aiohttp
    except ImportError:
        skip("API connectivity", "aiohttp not installed")
        return

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.douyu.com/",
    }

    async with aiohttp.ClientSession() as session:
        # 4a: mixList API
        print()
        print("  --- Test 4a: mixList API ---")
        try:
            url = "https://www.douyu.com/gapi/rkc/directory/mixList/0_0/1"
            async with session.get(url, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = json.loads(await resp.text(encoding="utf-8"))
                rl = data.get("data", {}).get("rl", [])
                check("mixList HTTP 200", resp.status == 200,
                      f"status={resp.status}")
                check("mixList code=0", data.get("code") == 0,
                      f"code={data.get('code')}")
                check("mixList returns data", len(rl) > 0,
                      f"got {len(rl)} items")
                if rl:
                    first = rl[0]
                    check("mixList has rid", "rid" in first)
                    check("mixList has nn", "nn" in first)
                    check("mixList has c2name", "c2name" in first)
                    rid = first["rid"]
        except Exception as e:
            check("mixList connectivity", False, str(e))
            rid = None

        # 4b: betard API
        print()
        print("  --- Test 4b: betard API ---")
        if rid:
            try:
                url = f"https://www.douyu.com/betard/{rid}"
                async with session.get(url, headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = json.loads(await resp.text(encoding="utf-8"))
                    room = data.get("room", {})
                    check("betard HTTP 200", resp.status == 200,
                          f"status={resp.status}")
                    check("betard has room", bool(room))
                    check("betard has levelInfo", "levelInfo" in room)
                    check("betard has nickname", "nickname" in room)
                    check("betard has second_lvl_name", "second_lvl_name" in room)
                    li = room.get("levelInfo", {})
                    check("betard has level", "level" in li)
                    check("betard has experience", "experience" in li)
                    check("betard level is numeric",
                          str(li.get("level", "")).isdigit(),
                          f"level={li.get('level')}")
            except Exception as e:
                check("betard connectivity", False, str(e))
        else:
            skip("betard test", "No rid from mixList")


# ================================================================
# Test 5: 完整流水线功能测试 (3页数据)
# ================================================================
async def test_full_pipeline():
    test_header("Test 5: Full Pipeline (3 pages, end-to-end)")

    try:
        import aiohttp
    except ImportError:
        skip("Full pipeline", "aiohttp not installed")
        return

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.douyu.com/",
    }

    async with aiohttp.ClientSession() as session:
        # 5a: Fetch streamers
        print()
        print("  --- Test 5a: Fetch streamers ---")
        streamers = []
        for page in range(1, 4):
            url = f"https://www.douyu.com/gapi/rkc/directory/mixList/0_0/{page}"
            try:
                async with session.get(url, headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = json.loads(await resp.text(encoding="utf-8"))
                    rl = data.get("data", {}).get("rl", [])
                    for item in rl:
                        streamers.append({
                            "rid": item["rid"],
                            "nn": (item.get("nn", "") or "").replace("\xa0", " ").strip(),
                            "c2name": item.get("c2name", ""),
                        })
            except Exception as e:
                check(f"Page {page} fetch", False, str(e))

        check("Fetched streamers count", len(streamers) > 0,
              f"got {len(streamers)}")
        if not streamers:
            return

        # 5b: Fetch levels
        print()
        print(f"  --- Test 5b: Fetch levels ({len(streamers)} streamers) ---")
        sem = asyncio.Semaphore(10)
        results = []

        async def fetch_one(s):
            async with sem:
                try:
                    url = f"https://www.douyu.com/betard/{s['rid']}"
                    async with session.get(url, headers=headers,
                                           timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        data = json.loads(await resp.text(encoding="utf-8"))
                        room = data.get("room", {})
                        li = room.get("levelInfo", {})
                        return {
                            "nickname": room.get("nickname") or s["nn"],
                            "category": room.get("second_lvl_name") or s["c2name"],
                            "level": int(li.get("level", 0)),
                            "experience": float(li.get("experience", 0)),
                            "room_id": s["rid"],
                        }
                except Exception:
                    return {
                        "nickname": s["nn"],
                        "category": s["c2name"],
                        "level": 0,
                        "experience": 0,
                        "room_id": s["rid"],
                    }

        tasks = [fetch_one(s) for s in streamers]
        results = await asyncio.gather(*tasks)
        check("Level fetch complete", len(results) == len(streamers))
        leveled = [r for r in results if r["level"] > 0]
        check("Streamers with level data",
              len(leveled) > len(results) * 0.8,  # At least 80% have levels
              f"{len(leveled)}/{len(results)} have levels")

        # 5c: Sort
        print()
        print("  --- Test 5c: Sort and validate ---")
        results.sort(key=lambda x: (x["level"], x["experience"]), reverse=True)
        top10 = results[:10]

        # Verify descending order
        levels = [r["level"] for r in results if r["level"] > 0]
        check("Sort order (descending)",
              all(levels[i] >= levels[i + 1] for i in range(len(levels) - 1)))

        print(f"  Top 10 preview:")
        for i, item in enumerate(top10):
            print(f"    #{i+1} {item['nickname']:<20} {item['category']:<12} Lv.{item['level']}")

        # 5d: JSON output
        print()
        print("  --- Test 5d: JSON output format ---")
        output = {
            "update_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_streamers_scanned": len(results),
            "top_count": 10,
            "data": top10,
        }
        json_str = json.dumps(output, ensure_ascii=False, indent=2)
        parsed = json.loads(json_str)
        check("Valid JSON", isinstance(parsed, dict))
        check("Has update_time", "update_time" in parsed)
        check("Has data array", isinstance(parsed.get("data"), list))
        check("Data array has items", len(parsed["data"]) > 0)
        for field in ["nickname", "category", "level", "room_id"]:
            check(f"Items have '{field}'",
                  all(field in d for d in parsed["data"]))


# ================================================================
# Test 6: data.json 文件测试 (如果存在)
# ================================================================
def test_data_json():
    test_header("Test 6: data.json Validation")

    data_path = os.path.join(TEST_DIR, "data.json")
    if not os.path.isfile(data_path):
        skip("data.json validation", "File not found (run scraper.py first)")
        return

    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        check("data.json is valid JSON", True)
        check("Has update_time field", "update_time" in data)
        check("Has total_streamers_scanned", "total_streamers_scanned" in data)
        check("Has data array", isinstance(data.get("data"), list))
        check("Data is non-empty", len(data.get("data", [])) > 0)

        items = data.get("data", [])
        for field in ["rank", "nickname", "category", "level", "experience", "room_id"]:
            check(f"Items have '{field}' field",
                  all(field in item for item in items))

        # Verify sort order
        levels = [item["level"] for item in items]
        check("Items sorted by level descending",
              all(levels[i] >= levels[i + 1] for i in range(len(levels) - 1)))

        # Verify ranks
        check("Rank numbers are sequential",
              all(items[i]["rank"] == i + 1 for i in range(len(items))))

    except json.JSONDecodeError as e:
        check("data.json is valid JSON", False, str(e))
    except Exception as e:
        check("data.json validation", False, str(e))


# ================================================================
# Main
# ================================================================
def main():
    global PASS_COUNT, FAIL_COUNT, SKIP_COUNT

    print("=" * 60)
    print("  斗鱼主播等级排行榜 - 自动化测试套件")
    print(f"  Test Directory: {TEST_DIR}")
    print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Sync tests
    test_file_existence()
    test_python_syntax()
    test_html_structure()

    # Async tests
    asyncio.run(test_api_connectivity())
    asyncio.run(test_full_pipeline())

    # data.json test
    test_data_json()

    # Summary
    total = PASS_COUNT + FAIL_COUNT + SKIP_COUNT
    print()
    print("=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    print(f"  Total:  {total}")
    print(f"  Passed: {PASS_COUNT}")
    print(f"  Failed: {FAIL_COUNT}")
    print(f"  Skipped: {SKIP_COUNT}")
    print()

    if FAIL_COUNT == 0:
        print("  [RESULT] ALL TESTS PASSED" if SKIP_COUNT == 0
              else f"  [RESULT] ALL RUN TESTS PASSED ({SKIP_COUNT} skipped)")
        print()
        print("  下一步: 运行 python scraper.py 生成完整数据")
    else:
        print(f"  [RESULT] {FAIL_COUNT} TEST(S) FAILED")
        print()

    return 0 if FAIL_COUNT == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
