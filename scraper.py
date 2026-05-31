#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
斗鱼主播等级爬虫 - Douyu Streamer Level Scraper

功能：
1. 从斗鱼 mixList API 获取所有在线主播列表
2. 通过 betard API 查询每个主播的等级信息
3. 按等级从大到小排序，输出前100名
4. 结果保存为 data.json 供前端页面使用

用法:
    python scraper.py          # 交互模式（终端输出详细日志）
    python scraper.py --ci     # CI 模式（精简输出，适合 GitHub Actions）
"""

import argparse
import asyncio
import json
import sys
import time
import os
import traceback

try:
    import aiohttp
except ImportError:
    print("错误: 需要 aiohttp 库，请运行: pip install aiohttp")
    sys.exit(1)

# ============================================================
# 配置
# ============================================================
MIXLIST_URL = "https://www.douyu.com/gapi/rkc/directory/mixList/0_0/{page}"
BETARD_URL = "https://www.douyu.com/betard/{room_id}"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "data.json")
LOG_FILE = os.path.join(SCRIPT_DIR, "scraper.log")
TOP_N = 100
MAX_CONCURRENT = 15
REQUEST_TIMEOUT = 10
MAX_RETRIES = 3
OVERALL_TIMEOUT = 600  # 整体超时(秒)，CI 模式下超时则退出
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.douyu.com/",
}

# 全局模式标记
CI_MODE = False


# ============================================================
# 工具函数
# ============================================================
def log(msg: str):
    """日志输出，CI 模式下写入文件，交互模式输出到终端"""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    if CI_MODE:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
        # CI 模式下也输出关键信息到 stdout
        if "error" in msg.lower() or "Step" in msg or "FAIL" in msg or "完成" in msg or "总计" in msg:
            print(line, flush=True)
    else:
        print(line, flush=True)


def load_existing_data() -> dict | None:
    """加载已有的 data.json，用于爬取失败时保留旧数据"""
    try:
        if os.path.isfile(OUTPUT_FILE):
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


async def fetch_json(session: aiohttp.ClientSession, url: str,
                     retries: int = MAX_RETRIES) -> dict | None:
    """异步获取 JSON 数据，带重试机制"""
    for attempt in range(1, retries + 1):
        try:
            async with session.get(url, headers=HEADERS,
                                   timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as resp:
                if resp.status == 200:
                    text = await resp.text(encoding="utf-8")
                    return json.loads(text)
                else:
                    log(f"  HTTP {resp.status} for {url[:80]}... (attempt {attempt})")
        except asyncio.TimeoutError:
            log(f"  Timeout for {url[:80]}... (attempt {attempt})")
        except Exception as e:
            log(f"  Error: {type(e).__name__}: {e} (attempt {attempt})")

        if attempt < retries:
            await asyncio.sleep(1 * attempt)

    log(f"  FAILED after {retries} retries: {url[:80]}...")
    return None


# ============================================================
# 第一步: 获取所有主播列表
# ============================================================
async def fetch_all_streamers(session: aiohttp.ClientSession) -> list[dict]:
    """从 mixList API 拉取所有页面的主播基础信息"""
    log("Step 1: 获取主播列表 (mixList API)")

    all_streamers = []
    seen_rids = set()
    page = 1
    empty_count = 0

    while empty_count < 3:
        url = MIXLIST_URL.format(page=page)
        data = await fetch_json(session, url)
        if data is None or data.get("code") != 0:
            empty_count += 1
            page += 1
            continue

        rl = data.get("data", {}).get("rl", [])
        if not rl:
            empty_count += 1
            page += 1
            continue

        empty_count = 0
        new_count = 0
        for item in rl:
            rid = item.get("rid")
            if rid and rid not in seen_rids:
                seen_rids.add(rid)
                nn = (item.get("nn") or "").replace("\xa0", " ").replace("　", " ").strip()
                c2name = (item.get("c2name") or "").replace("\xa0", " ").replace("　", " ").strip()
                all_streamers.append({"rid": rid, "nn": nn, "c2name": c2name})
                new_count += 1

        log(f"  Page {page}: {len(rl)} raw, {new_count} new (累计 {len(all_streamers)})")
        page += 1

    log(f"  总计获取 {len(all_streamers)} 个唯一主播")
    return all_streamers


# ============================================================
# 第二步: 获取主播等级
# ============================================================
async def fetch_one_level(session: aiohttp.ClientSession,
                          sem: asyncio.Semaphore,
                          streamer: dict,
                          idx: int, total: int) -> dict:
    """获取单个主播的等级信息"""
    rid = streamer["rid"]
    url = BETARD_URL.format(room_id=rid)

    async with sem:
        data = await fetch_json(session, url)

    level = 0
    experience = 0.0
    nickname = streamer["nn"]
    category = streamer["c2name"]

    if data is not None:
        room = data.get("room") or {}
        nickname = (room.get("nickname") or streamer["nn"])
        nickname = nickname.replace("\xa0", " ").replace("　", " ").strip()
        category = (room.get("second_lvl_name") or streamer["c2name"])
        category = category.replace("\xa0", " ").replace("　", " ").strip()
        level_info = room.get("levelInfo") or {}
        try:
            level = int(level_info.get("level", 0))
        except (ValueError, TypeError):
            level = 0
        experience = float(level_info.get("experience", 0))

    if idx % 250 == 0 or idx == total:
        log(f"  Progress: {idx}/{total}")

    return {
        "rank": 0,
        "nickname": nickname,
        "category": category,
        "level": level,
        "experience": experience,
        "room_id": rid,
    }


async def fetch_all_levels(session: aiohttp.ClientSession,
                           streamers: list[dict]) -> list[dict]:
    """并发获取所有主播的等级"""
    log(f"Step 2: 获取主播等级 (betard API, 并发={MAX_CONCURRENT})")

    sem = asyncio.Semaphore(MAX_CONCURRENT)
    total = len(streamers)

    tasks = [fetch_one_level(session, sem, s, i + 1, total)
             for i, s in enumerate(streamers)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    valid_results = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            valid_results.append({
                "rank": 0,
                "nickname": streamers[i]["nn"],
                "category": streamers[i]["c2name"],
                "level": 0,
                "experience": 0,
                "room_id": streamers[i]["rid"],
            })
        else:
            valid_results.append(r)

    log(f"  成功获取 {len(valid_results)} 个主播的等级")
    return valid_results


# ============================================================
# 第三步: 排序并输出
# ============================================================
def sort_and_output(results: list[dict]) -> list[dict]:
    """按等级从大到小排序，输出前100名到 data.json"""
    log("Step 3: 排序并输出 Top 100")

    # 按 level 降序，level 相同按 experience 降序
    results.sort(key=lambda x: (x["level"], x["experience"]), reverse=True)

    top100 = results[:TOP_N]
    for i, item in enumerate(top100):
        item["rank"] = i + 1

    levels = [item["level"] for item in top100]
    log(f"  Top 100 等级范围: Lv.{min(levels)} ~ Lv.{max(levels)}")
    log(f"  No.1: Lv.{levels[0]} - {top100[0]['nickname']} ({top100[0]['category']})")

    output = {
        "update_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "update_timestamp": int(time.time()),
        "total_streamers_scanned": len(results),
        "top_count": TOP_N,
        "data": top100,
    }

    # 原子写入：先写临时文件，成功后再 rename
    tmp_file = OUTPUT_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, OUTPUT_FILE)

    log(f"  结果已保存到: {OUTPUT_FILE}")
    return top100


# ============================================================
# 主函数
# ============================================================
async def run_scraper() -> int:
    """运行爬虫，返回 0=成功, 1=失败"""
    start_time = time.time()
    log(f"斗鱼主播等级爬虫启动 (mode={'CI' if CI_MODE else 'interactive'})")
    log(f"输出文件: {OUTPUT_FILE}")

    try:
        connector = aiohttp.TCPConnector(
            limit=MAX_CONCURRENT + 10,
            limit_per_host=MAX_CONCURRENT + 10,
        )
        async with aiohttp.ClientSession(connector=connector) as session:
            # Step 1: 获取主播列表
            streamers = await fetch_all_streamers(session)
            if not streamers:
                log("FAIL: 未获取到任何主播数据")
                return 1

            # Step 2: 获取等级
            results = await fetch_all_levels(session, streamers)

        # Step 3: 排序输出
        top100 = sort_and_output(results)

        # 预览前20
        log("Top 20 预览:")
        for item in top100[:20]:
            log(f"  #{item['rank']:<3} {item['nickname']:<20} {item['category']:<12} Lv.{item['level']}")

        elapsed = time.time() - start_time
        log(f"完成! 总耗时: {elapsed:.1f} 秒")
        return 0

    except Exception as e:
        log(f"FAIL: 爬虫异常: {e}")
        if CI_MODE:
            traceback.print_exc()
        return 1


def main():
    global CI_MODE

    parser = argparse.ArgumentParser(description="斗鱼主播等级爬虫")
    parser.add_argument("--ci", action="store_true",
                        help="CI 模式: 精简输出 + 失败时保留旧数据")
    args = parser.parse_args()
    CI_MODE = args.ci

    if CI_MODE:
        # CI 模式: 清空旧日志，记录开始
        try:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write(f"=== Scraper CI Log - {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        except Exception:
            pass

    # 运行爬虫
    try:
        ret = asyncio.run(asyncio.wait_for(run_scraper(), timeout=OVERALL_TIMEOUT))
    except asyncio.TimeoutError:
        log(f"FAIL: 整体超时 ({OVERALL_TIMEOUT}秒)，保留旧数据")
        ret = 1
    except Exception as e:
        log(f"FAIL: 爬虫致命错误: {e}")
        traceback.print_exc()
        ret = 1

    # CI 模式下，如果爬虫失败且存在旧数据，保留旧数据
    if ret != 0 and CI_MODE:
        old = load_existing_data()
        if old and old.get("data") and len(old["data"]) > 0:
            log("CI 模式: 爬取失败，保留已有 data.json 不变")
            # 如果 data.json 不存在（被删除），恢复旧数据
            if not os.path.isfile(OUTPUT_FILE):
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(old, f, ensure_ascii=False, indent=2)
                log("已从备份恢复旧数据")
            print("Scraper failed but old data preserved.", flush=True)
        else:
            log("CI 模式: 爬取失败且无旧数据可恢复")

    sys.exit(ret)


if __name__ == "__main__":
    main()
