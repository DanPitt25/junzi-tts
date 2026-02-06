#!/usr/bin/env python3
"""
Scrape Chinese Text Project for parallel Chinese-English texts.
Uses Legge translations where available.

Usage:
    python scrape_ctp.py                              # Scrape all texts
    python scrape_ctp.py mengzi zhuangzi             # Scrape specific texts
    python scrape_ctp.py --resume mengzi             # Resume from a specific text
    python scrape_ctp.py --scraper-api KEY           # Use ScraperAPI (free tier: 5000 req/mo)
    python scrape_ctp.py --scrape-do KEY             # Use Scrape.do (free tier: 1000 req/mo)
    python scrape_ctp.py --zenrows KEY               # Use ZenRows (free tier: 1000 req/mo)
    python scrape_ctp.py --proxy host:port           # Use a specific proxy
    python scrape_ctp.py --no-proxy                  # Direct connection (no proxy)

Get free API keys:
    ScraperAPI: https://www.scraperapi.com/ (5000 free requests/month)
    Scrape.do:  https://scrape.do/ (1000 free requests/month)
    ZenRows:    https://www.zenrows.com/ (1000 free requests/month)

Requirements:
    pip install requests
"""

import json
import random
import sys
import time
from pathlib import Path
from html.parser import HTMLParser

try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")
    sys.exit(1)

# Texts to scrape with their CTP paths
TEXTS = {
    "analects": {
        "base_url": "https://ctext.org/analects",
        "title": "論語",
        "titleEn": "Analects",
        "chapters": [
            "xue-er", "wei-zheng", "ba-yi", "li-ren", "gong-ye-chang",
            "yong-ye", "shu-er", "tai-bo", "zi-han", "xiang-dang",
            "xian-jin", "yan-yuan", "zi-lu", "xian-wen", "wei-ling-gong",
            "ji-shi", "yang-huo", "wei-zi", "zi-zhang", "yao-yue"
        ]
    },
    "mengzi": {
        "base_url": "https://ctext.org/mengzi",
        "title": "孟子",
        "titleEn": "Mencius",
        "chapters": [
            "liang-hui-wang-i", "liang-hui-wang-ii",
            "gong-sun-chou-i", "gong-sun-chou-ii",
            "teng-wen-gong-i", "teng-wen-gong-ii",
            "li-lou-i", "li-lou-ii",
            "wan-zhang-i", "wan-zhang-ii",
            "gaozi-i", "gaozi-ii",
            "jin-xin-i", "jin-xin-ii"
        ]
    },
    "daxue": {
        "base_url": "https://ctext.org/liji/da-xue",
        "title": "大學",
        "titleEn": "Great Learning",
        "chapters": None  # Single page
    },
    "zhongyong": {
        "base_url": "https://ctext.org/liji/zhong-yong",
        "title": "中庸",
        "titleEn": "Doctrine of the Mean",
        "chapters": None  # Single page
    },
    "daodejing": {
        "base_url": "https://ctext.org/dao-de-jing",
        "title": "道德經",
        "titleEn": "Dao De Jing",
        "chapters": None  # Single page
    },
    "zhuangzi": {
        "base_url": "https://ctext.org/zhuangzi",
        "title": "莊子",
        "titleEn": "Zhuangzi",
        "chapters": [
            # Inner Chapters (內篇) 1-7
            "enjoyment-in-untroubled-ease",      # 1 逍遙遊
            "adjustment-of-controversies",        # 2 齊物論
            "nourishing-the-lord-of-life",        # 3 養生主
            "man-in-the-world-associated-with",   # 4 人間世
            "seal-of-virtue-complete",            # 5 德充符
            "great-and-most-honoured-master",     # 6 大宗師
            "normal-course-for-rulers-and-kings", # 7 應帝王
            # Outer Chapters (外篇) 8-22
            "webbed-toes",                        # 8 駢拇
            "horsess-hoofs",                      # 9 馬蹄
            "cutting-open-satchels",              # 10 胠篋
            "letting-be-and-exercising-forbearance", # 11 在宥
            "heaven-and-earth",                   # 12 天地
            "tian-dao",                           # 13 天道
            "revolution-of-heaven",               # 14 天運
            "ingrained-ideas",                    # 15 刻意
            "correcting-the-nature",              # 16 繕性
            "floods-of-autumn",                   # 17 秋水
            "perfect-enjoyment",                  # 18 至樂
            "full-understanding-of-life",         # 19 達生
            "tree-on-the-mountain",               # 20 山木
            "tian-zi-fang",                       # 21 田子方
            "knowledge-rambling-in-the-north",    # 22 知北遊
            # Miscellaneous Chapters (雜篇) 23-33
            "geng-sang-chu",                      # 23 庚桑楚
            "xu-wu-gui",                          # 24 徐無鬼
            "ze-yang",                            # 25 則陽
            "what-comes-from-without",            # 26 外物
            "metaphorical-language",              # 27 寓言
            "kings-who-have-wished-to-resign",    # 28 讓王
            "robber-zhi",                         # 29 盜跖
            "delight-in-the-sword-fight",         # 30 說劍
            "old-fisherman",                      # 31 漁父
            "lie-yu-kou",                         # 32 列禦寇
            "tian-xia"                            # 33 天下
        ]
    },
    "mozi": {
        "base_url": "https://ctext.org/mozi",
        "title": "墨子",
        "titleEn": "Mozi",
        "chapters": [
            "qin-shi", "xiu-shen", "suo-ran", "fa-yi", "qi-huan", "ci-guo", "san-bian",
            "shang-xian-i", "shang-xian-ii", "shang-xian-iii",
            "shang-tong-i", "shang-tong-ii", "shang-tong-iii",
            "jian-ai-i", "jian-ai-ii", "jian-ai-iii",
            "fei-gong-i", "fei-gong-ii", "fei-gong-iii",
            "jie-yong-i", "jie-yong-ii", "jie-zang-i", "jie-zang-ii", "jie-zang-iii",
            "tian-zhi-i", "tian-zhi-ii", "tian-zhi-iii",
            "ming-gui-i", "ming-gui-ii", "ming-gui-iii",
            "fei-yue-i", "fei-ming-i", "fei-ming-ii", "fei-ming-iii",
            "fei-ru-i", "fei-ru-ii",
            "da-qu", "xiao-qu", "geng-zhu", "gui-yi",
            "gong-meng", "lu-wen", "gong-shu"
        ]
    },
    "book-of-poetry": {
        "base_url": "https://ctext.org/book-of-poetry",
        "title": "詩經",
        "titleEn": "Book of Poetry",
        "chapters": [
            # Airs of the States (國風)
            "odes-of-zhou-and-the-south", "odes-of-shao-and-the-south",
            "odes-of-bei", "odes-of-yong", "odes-of-wei", "odes-of-the-royal-domain",
            "odes-of-zheng", "odes-of-qi", "odes-of-wei-ii", "odes-of-tang",
            "odes-of-qin", "odes-of-chen", "odes-of-gui", "odes-of-cao", "odes-of-bin",
            # Lesser Odes (小雅)
            "decade-of-lu-ming", "decade-of-bai-hua", "decade-of-tong-gong",
            "decade-of-qi-fu", "decade-of-xiao-min", "decade-of-bei-shan",
            "decade-of-sang-hu", "decade-of-du-ren-shi",
            # Greater Odes (大雅)
            "decade-of-wen-wang", "decade-of-sheng-min", "decade-of-dang",
            # Hymns (頌)
            "sacrificial-odes-of-zhou", "sacrificial-odes-of-lu", "sacrificial-odes-of-shang"
        ]
    },
    "yijing": {
        "base_url": "https://ctext.org/book-of-changes",
        "title": "易經",
        "titleEn": "Book of Changes (I Ching)",
        "chapters": [
            "qian", "kun", "zhun", "meng", "xu", "song", "shi", "bi",
            "xiao-xu", "lv", "tai", "pi", "tong-ren", "da-you", "qian2", "yu",
            "sui", "gu", "lin", "guan", "shi-he", "bi2", "bo", "fu",
            "wu-wang", "da-xu", "yi", "da-guo", "kan", "li",
            "xian", "heng", "dun", "da-zhuang", "jin", "ming-yi", "jia-ren", "kui",
            "jian", "xie", "sun", "yi2", "guai", "gou", "cui", "sheng", "kun2", "jing",
            "ge", "ding", "zhen", "gen", "jian2", "gui-mei", "feng", "lv2",
            "xun", "dui", "huan", "jie", "zhong-fu", "xiao-guo", "ji-ji", "wei-ji",
            "xi-ci-i", "xi-ci-ii", "shuo-gua", "xu-gua", "za-gua"
        ]
    },
    "xunzi": {
        "base_url": "https://ctext.org/xunzi",
        "title": "荀子",
        "titleEn": "Xunzi",
        "chapters": [
            "quan-xue", "xiu-shen", "bu-gou", "rong-ru", "fei-xiang", "fei-shi-er-zi",
            "zhong-ni", "ru-xiao", "wang-zhi", "fu-guo", "wang-ba", "jun-dao",
            "chen-dao", "zhi-shi", "yi-bing", "qiang-guo", "tian-lun", "zheng-lun",
            "li-lun", "yue-lun", "jie-bi", "zheng-ming", "xing-e", "jun-zi",
            "cheng-xiang", "fu-pian", "da-lue", "you-zuo", "zi-dao", "fa-xing",
            "ai-gong", "yao-wen"
        ]
    },
    "hanfeizi": {
        "base_url": "https://ctext.org/hanfeizi",
        "title": "韓非子",
        "titleEn": "Han Feizi",
        "chapters": [
            "chu-jian-qin", "cun-han", "nan-yan", "ai-chen", "zhu-dao",
            "you-du", "er-bing", "yang-quan", "ba-jian", "shi-guo",
            "gu-fen", "shuo-nan", "he-shi", "jian-jie-shi-chen",
            "wang-zheng", "san-shou", "bei-nei", "nan-mian", "shi-xie",
            "jie-lao", "yu-lao", "shuo-lin-i", "shuo-lin-ii",
            "guan-xing", "an-wei", "shou-dao", "yong-ren", "gong-ming",
            "da-ti", "nei-chu-shuo-shang", "nei-chu-shuo-xia",
            "wai-chu-shuo-zuo-shang", "wai-chu-shuo-zuo-xia",
            "wai-chu-shuo-you-shang", "wai-chu-shuo-you-xia",
            "nan-i", "nan-ii", "nan-iii", "nan-iv",
            "wen-bian", "wen-tian", "ding-fa", "shuo-yi", "gui-shi",
            "liu-fan", "ba-shuo", "ba-jing", "wu-du", "xian-xue", "zhong-xiao", "ren-zhu"
        ]
    },
    "liji": {
        "base_url": "https://ctext.org/liji",
        "title": "禮記",
        "titleEn": "Book of Rites",
        "chapters": [
            "qu-li-i", "qu-li-ii", "tan-gong-i", "tan-gong-ii",
            "wang-zhi", "yue-ling", "zeng-zi-wen", "wen-wang-shi-zi",
            "li-yun", "li-qi", "jiao-te-sheng", "nei-ze", "yu-zao",
            "ming-tang-wei", "sang-fu-xiao-ji", "da-zhuan", "shao-yi",
            "xue-ji", "yue-ji", "za-ji-i", "za-ji-ii", "sang-da-ji",
            "ji-fa", "ji-yi", "ji-tong", "jing-jie", "ai-gong-wen",
            "zhong-ni-yan-ju", "kong-zi-xian-ju", "fang-ji", "biao-ji",
            "zi-yi", "ben-sang", "wen-sang", "fu-wen", "jian-zhuan",
            "san-nian-wen", "shen-yi", "tou-hu", "ru-xing", "da-xue", "guan-yi",
            "hun-yi", "xiang-yin-jiu-yi", "she-yi", "yan-yi", "pin-yi", "sang-fu-si-zhi"
        ]
    },
    "shangshu": {
        "base_url": "https://ctext.org/shang-shu",
        "title": "尚書",
        "titleEn": "Book of Documents",
        "chapters": [
            # Tang Shu (虞書)
            "yao-dian", "shun-dian", "da-yu-mo", "gao-yao-mo", "yi-ji",
            # Xia Shu (夏書)
            "yu-gong", "gan-shi", "wu-zi-zhi-ge", "yin-zheng",
            # Shang Shu (商書)
            "tang-shi", "zhong-hui-zhi-gao", "tang-gao", "yi-xun", "tai-jia-i",
            "tai-jia-ii", "tai-jia-iii", "xian-you-yi-de", "pan-geng-i",
            "pan-geng-ii", "pan-geng-iii", "yue-ming-i", "yue-ming-ii",
            "yue-ming-iii", "gao-zong-rong-ri", "xi-bo-kan-li", "wei-zi",
            # Zhou Shu (周書)
            "tai-shi-i", "tai-shi-ii", "tai-shi-iii", "mu-shi", "wu-cheng",
            "hong-fan", "lv-ao", "jin-teng", "da-gao", "wei-zi-zhi-ming",
            "kang-gao", "jiu-gao", "zi-cai", "zhao-gao", "luo-gao",
            "duo-shi", "wu-yi", "jun-shi", "cai-zhong-zhi-ming", "duo-fang",
            "li-zheng", "zhou-guan", "jun-chen", "gu-ming", "kang-wang-zhi-gao",
            "bi-ming", "jun-ya", "jiong-ming", "lv-xing", "wen-hou-zhi-ming", "fei-shi"
        ]
    },
    "chunqiu-zuozhuan": {
        "base_url": "https://ctext.org/chun-qiu-zuo-zhuan",
        "title": "春秋左傳",
        "titleEn": "Erta: Zuo Zhuan",
        "chapters": [
            "yin-gong", "huan-gong", "zhuang-gong", "min-gong", "xi-gong-i", "xi-gong-ii",
            "wen-gong-i", "wen-gong-ii", "xuan-gong-i", "xuan-gong-ii",
            "cheng-gong-i", "cheng-gong-ii", "xiang-gong-i", "xiang-gong-ii", "xiang-gong-iii",
            "zhao-gong-i", "zhao-gong-ii", "zhao-gong-iii", "zhao-gong-iv",
            "ding-gong-i", "ding-gong-ii", "ai-gong-i", "ai-gong-ii"
        ]
    },
    "xiaojing": {
        "base_url": "https://ctext.org/xiao-jing",
        "title": "孝經",
        "titleEn": "Classic of Filial Piety",
        "chapters": None  # Single page
    },
    "erya": {
        "base_url": "https://ctext.org/er-ya",
        "title": "爾雅",
        "titleEn": "Erya",
        "chapters": [
            "shi-gu", "shi-yan", "shi-xun", "shi-qin", "shi-gong", "shi-qi",
            "shi-yue", "shi-qin2", "shi-tian", "shi-qiu", "shi-shan", "shi-shui",
            "shi-cao", "shi-mu", "shi-chong", "shi-yu", "shi-niao", "shi-shou", "shi-chu"
        ]
    },
    "liezi": {
        "base_url": "https://ctext.org/liezi",
        "title": "列子",
        "titleEn": "Liezi",
        "chapters": [
            "tian-rui", "huang-di", "zhou-mu-wang", "zhong-ni", "tang-wen",
            "li-ming", "yang-zhu", "shuo-fu"
        ]
    },
    "guanzi": {
        "base_url": "https://ctext.org/guanzi",
        "title": "管子",
        "titleEn": "Guanzi",
        "chapters": [
            "mu-min", "xing-shi", "quan-xiu", "li-zheng", "cheng-ma", "qi-fa", "ban-fa",
            "you-guan", "you-guan-tu", "wu-fu", "xiao-kuang", "xiao-cheng", "xiao-ni",
            "ba-yan", "ba-guan", "fa-jin", "zhong-ling", "shu-yan", "di-yuan", "di-tu",
            "di-shu", "du-di", "jiu-shou", "qi-chen-qi-zhu", "shan-zhi-shu", "shan-quan-shu",
            "shan-guo-gui", "hai-wang", "guo-xu", "ru-guo", "jiu-bai", "huan-gong-wen",
            "da-kuang", "zhong-kuang", "xiao-kuang2", "wang-yan", "shu-wu-yi", "ji-zhang",
            "wen-yi", "zheng-shi-yi", "xiao-wen", "qi-wen", "qi-nei", "di-yuan2",
            "qing-zhong-jia", "qing-zhong-yi", "qing-zhong-bing", "qing-zhong-ding",
            "qing-zhong-wu", "qing-zhong-ji"
        ]
    },
    "sunzi": {
        "base_url": "https://ctext.org/art-of-war",
        "title": "孫子兵法",
        "titleEn": "Art of War",
        "chapters": [
            "ji-pian", "zuo-zhan", "mou-gong", "jun-xing", "bing-shi",
            "xu-shi", "jun-zheng", "jiu-bian", "xing-jun", "di-xing",
            "jiu-di", "huo-gong", "yong-jian"
        ]
    },
    "yanzi-chunqiu": {
        "base_url": "https://ctext.org/yanzi-chun-qiu",
        "title": "晏子春秋",
        "titleEn": "Yanzi Chunqiu",
        "chapters": [
            "nei-pian-jian-shang", "nei-pian-jian-xia", "nei-pian-wen-shang",
            "nei-pian-wen-xia", "nei-pian-za-shang", "nei-pian-za-xia",
            "wai-pian-shang", "wai-pian-xia"
        ]
    },
    "huainanzi": {
        "base_url": "https://ctext.org/huainanzi",
        "title": "淮南子",
        "titleEn": "Huainanzi",
        "chapters": [
            "yuan-dao", "su-zhen", "tian-wen", "zhui-xing", "shi-ze",
            "lan-ming", "jing-shen", "ben-jing", "zhu-shu", "miu-cheng",
            "qi-su", "dao-ying", "fan-lun", "quan-yan", "bing-lue",
            "shuo-shan", "shuo-lin", "ren-jian", "xiu-wu", "tai-zu", "yao-lue"
        ]
    },
    "shiji": {
        "base_url": "https://ctext.org/shiji",
        "title": "史記",
        "titleEn": "Records of the Grand Historian",
        "chapters": [
            # Basic Annals (本紀)
            "wu-di-ben-ji", "xia-ben-ji", "yin-ben-ji", "zhou-ben-ji",
            "qin-ben-ji", "qin-shi-huang-ben-ji", "xiang-yu-ben-ji",
            "gao-zu-ben-ji", "lv-tai-hou-ben-ji", "xiao-wen-ben-ji",
            "xiao-jing-ben-ji", "xiao-wu-ben-ji",
            # Tables (表)
            "san-dai-shi-biao", "shi-er-zhu-hou-nian-biao", "liu-guo-nian-biao",
            "qin-chu-zhi-ji-yue-biao", "han-xing-yi-lai-zhu-hou-wang-nian-biao",
            "gao-zu-gong-chen-hou-zhe-nian-biao", "hui-jing-jian-hou-zhe-nian-biao",
            "jian-yuan-yi-lai-hou-zhe-nian-biao", "jian-yuan-yi-lai-wang-zi-hou-zhe-nian-biao",
            "han-xing-yi-lai-jiang-xiang-ming-chen-nian-biao"
        ]
    },
}

OUTPUT_DIR = Path("translations")

# Browser profiles - complete sets of headers that look like real browsers
BROWSER_PROFILES = [
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "max-age=0",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "max-age=0",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
    },
]

# Global session for persistent cookies
_session = None
_proxy = None
_proxy_list = []
_proxy_index = 0
_use_proxy = False  # Default to no proxy now
_scraping_service = 'scraperapi'  # Default to ScraperAPI
_api_key = "25eafe26d8a38e8e1ffd8c2aa907cf23"  # ScraperAPI key


def build_scraping_params(target_url: str) -> tuple[str, dict]:
    """Build the URL and params for the scraping service, or return original URL if no service."""
    global _scraping_service, _api_key

    if _scraping_service == 'scraperapi':
        # ScraperAPI uses params: api_key and url
        return "https://api.scraperapi.com/", {"api_key": _api_key, "url": target_url}

    elif _scraping_service == 'scrapedo':
        # Scrape.do uses params: token and url
        return "https://api.scrape.do/", {"token": _api_key, "url": target_url}

    elif _scraping_service == 'zenrows':
        # ZenRows uses params: apikey and url
        return "https://api.zenrows.com/v1/", {"apikey": _api_key, "url": target_url}

    return target_url, {}


def get_session():
    """Get or create a requests session with browser-like settings."""
    global _session, _proxy, _use_proxy
    if _session is None:
        _session = requests.Session()
        profile = random.choice(BROWSER_PROFILES)
        _session.headers.update(profile)

        # Set up manual proxy if specified (not used with scraping services)
        if _use_proxy and _proxy_list and not _scraping_service:
            proxy = _proxy_list[0]
            _session.proxies = {
                "http": f"http://{proxy}",
                "https": f"http://{proxy}",
            }
            print(f"  Using proxy: {proxy}")

    return _session


def reset_session():
    """Reset the session (use when rate limited)."""
    global _session
    _session = None
    print("  Session reset, trying new proxy...")


class CTEXTParser(HTMLParser):
    """Parse CTP HTML to extract parallel Chinese-English passages."""

    def __init__(self):
        super().__init__()
        self.passages = []
        self.current_zh = ''
        self.current_en = ''
        self.in_ctext_td = False
        self.in_etext_td = False
        self.pending_zh = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get('class', '')
        if tag == 'td':
            if cls == 'ctext':
                self.in_ctext_td = True
                self.current_zh = ''
            elif cls == 'etext':
                self.in_etext_td = True
                self.current_en = ''

    def handle_endtag(self, tag):
        if tag == 'td':
            if self.in_ctext_td:
                self.in_ctext_td = False
                zh = self.current_zh.strip()
                if zh:
                    self.pending_zh = zh
            elif self.in_etext_td:
                self.in_etext_td = False
                en = self.current_en.strip()
                if self.pending_zh and en:
                    self.passages.append({
                        'zh': self.pending_zh,
                        'en': en
                    })
                    self.pending_zh = None

    def handle_data(self, data):
        if self.in_ctext_td:
            self.current_zh += data
        elif self.in_etext_td:
            self.current_en += data


def fetch_chapter(url: str, retries: int = 3) -> list:
    """Fetch a chapter page and parse passages with retry logic."""
    session = get_session()

    # Build the actual request URL and params (may go through scraping service)
    request_url, params = build_scraping_params(url)

    for attempt in range(retries):
        try:
            # Small random delay to seem human (0.3-0.8s for API, 0.5-1.5s for direct)
            if _scraping_service:
                delay = 0.3 + random.random() * 0.5
            else:
                delay = 0.5 + random.random()
            time.sleep(delay)

            # Set referer to look like we navigated from parent page (for direct requests)
            if not _scraping_service:
                base_url = "/".join(url.rsplit("/", 1)[:-1]) if "/" in url else url
                session.headers["Referer"] = base_url

            response = session.get(request_url, params=params, timeout=60)

            if response.status_code == 200:
                parser = CTEXTParser()
                parser.feed(response.text)
                return parser.passages
            elif response.status_code == 403:
                print(f"    Rate limited (403), resetting session...")
                reset_session()
                session = get_session()
                # Wait a bit before retry
                time.sleep(3 + random.random() * 2)
            elif response.status_code == 404:
                print(f"    Not found (404): {url}")
                return []
            else:
                print(f"    HTTP error {response.status_code}: {url}")
                time.sleep(2)

        except requests.exceptions.Timeout:
            print(f"    Timeout, retrying...")
            time.sleep(2)
        except requests.exceptions.ConnectionError as e:
            print(f"    Connection error: {e}")
            reset_session()
            time.sleep(3)
        except Exception as e:
            print(f"    Error: {e}")
            time.sleep(2)

    print(f"    Failed after {retries} attempts: {url}")
    return []


def format_chapter_title(slug: str) -> str:
    """Convert slug to readable title."""
    return slug.replace("-", " ").title()


def scrape_text(text_id: str, info: dict) -> dict:
    """Scrape a single text."""
    print(f"\nProcessing {info['titleEn']}...")

    output = {
        "id": text_id,
        "title": info["title"],
        "titleEn": info["titleEn"],
        "source": "Chinese Text Project (ctext.org) - James Legge translation",
        "chapters": []
    }

    if info["chapters"] is None:
        # Single page text
        print(f"    Fetching {info['base_url']}...")
        passages = fetch_chapter(info["base_url"])
        if passages:
            output["chapters"].append({
                "number": "1",
                "title": info["titleEn"],
                "passages": [{"ref": str(i+1), **p} for i, p in enumerate(passages)]
            })
    else:
        # Multiple chapters
        for i, chapter_slug in enumerate(info["chapters"], 1):
            url = f"{info['base_url']}/{chapter_slug}"
            print(f"    [{i}/{len(info['chapters'])}] Fetching {chapter_slug}...")
            passages = fetch_chapter(url)

            if passages:
                output["chapters"].append({
                    "number": str(i),
                    "title": format_chapter_title(chapter_slug),
                    "slug": chapter_slug,
                    "passages": [{"ref": f"{i}:{j+1}", **p} for j, p in enumerate(passages)]
                })

    # Summary
    total_passages = sum(len(ch["passages"]) for ch in output["chapters"])
    print(f"  Found {len(output['chapters'])} chapters, {total_passages} passages")

    return output


def save_output(output: dict, output_path: Path):
    """Save output to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    total = sum(len(ch["passages"]) for ch in output["chapters"])
    print(f"  Saved {len(output['chapters'])} chapters, {total} passages to {output_path}")


def main():
    global _proxy_list, _proxy, _use_proxy, _scraping_service, _api_key

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Parse command line args
    args = sys.argv[1:]

    # Handle scraping service options
    for service_flag, service_name in [
        ("--scraper-api", "scraperapi"),
        ("--scrape-do", "scrapedo"),
        ("--zenrows", "zenrows"),
    ]:
        if service_flag in args:
            idx = args.index(service_flag)
            if idx + 1 < len(args):
                _api_key = args[idx + 1]
                _scraping_service = service_name
                print(f"Using {service_name} scraping service")
                args = [a for i, a in enumerate(args) if i != idx and i != idx + 1]
            else:
                print(f"Error: {service_flag} requires an API key")
                sys.exit(1)
            break

    # Handle --proxy option
    if "--proxy" in args:
        proxy_idx = args.index("--proxy")
        if proxy_idx + 1 < len(args):
            custom_proxy = args[proxy_idx + 1]
            _proxy_list = [custom_proxy]
            _proxy = custom_proxy
            _use_proxy = True
            print(f"Using custom proxy: {custom_proxy}")
            args = [a for i, a in enumerate(args) if i != proxy_idx and i != proxy_idx + 1]
        else:
            print("Error: --proxy requires a host:port argument")
            sys.exit(1)

    # Handle --no-proxy option (now the default anyway)
    if "--no-proxy" in args:
        _use_proxy = False
        _proxy_list = []
        args = [a for a in args if a != "--no-proxy"]

    if "--resume" in args:
        resume_idx = args.index("--resume")
        resume_from = args[resume_idx + 1] if resume_idx + 1 < len(args) else None
        args = [a for a in args if a != "--resume" and a != resume_from]
        texts_to_scrape = list(TEXTS.keys())
        if resume_from and resume_from in texts_to_scrape:
            start_idx = texts_to_scrape.index(resume_from)
            texts_to_scrape = texts_to_scrape[start_idx:]
    elif args:
        texts_to_scrape = [a for a in args if a in TEXTS]
        if not texts_to_scrape:
            print(f"Unknown texts: {args}")
            print(f"Available: {', '.join(TEXTS.keys())}")
            sys.exit(1)
    else:
        texts_to_scrape = list(TEXTS.keys())

    # Show what mode we're running in
    if _scraping_service:
        print(f"Mode: {_scraping_service} API")
    elif _use_proxy:
        print(f"Mode: Custom proxy")
    else:
        print("Mode: Direct connection (may be rate limited)")

    print(f"Will scrape: {', '.join(texts_to_scrape)}")
    print(f"Output directory: {OUTPUT_DIR.absolute()}")
    print("Press Ctrl+C to stop (progress will be saved)\n")

    for text_id in texts_to_scrape:
        info = TEXTS[text_id]
        output_path = OUTPUT_DIR / f"{text_id}.json"

        # Load existing translation if it exists
        existing = None
        existing_slugs = set()
        if output_path.exists():
            try:
                with open(output_path, encoding="utf-8") as f:
                    existing = json.load(f)
                # Build set of already-scraped chapter slugs
                for ch in existing.get("chapters", []):
                    if ch.get("slug"):
                        existing_slugs.add(ch["slug"])
                    elif ch.get("number"):
                        existing_slugs.add(ch["number"])
            except Exception as e:
                print(f"  Warning: Could not load existing {output_path}: {e}")

        print(f"\nProcessing {info['titleEn']}...")

        # Check if we need to scrape anything
        if info["chapters"] is None:
            # Single page text - skip if already exists with content
            if existing and existing.get("chapters") and existing["chapters"][0].get("passages"):
                print(f"  Already complete, skipping.")
                continue
            chapters_to_scrape = [None]  # Marker for single-page
        else:
            # Filter to only missing chapters
            chapters_to_scrape = [
                (i, slug) for i, slug in enumerate(info["chapters"], 1)
                if slug not in existing_slugs
            ]
            if not chapters_to_scrape:
                print(f"  All {len(info['chapters'])} chapters already scraped, skipping.")
                continue
            print(f"  {len(chapters_to_scrape)} of {len(info['chapters'])} chapters to scrape")

        # Start with existing data or fresh structure
        if existing:
            output = existing
        else:
            output = {
                "id": text_id,
                "title": info["title"],
                "titleEn": info["titleEn"],
                "source": "Chinese Text Project (ctext.org) - James Legge translation",
                "chapters": []
            }

        try:
            if info["chapters"] is None:
                # Single page text
                print(f"    Fetching {info['base_url']}...")
                passages = fetch_chapter(info["base_url"])
                if passages:
                    output["chapters"].append({
                        "number": "1",
                        "title": info["titleEn"],
                        "passages": [{"ref": str(i+1), **p} for i, p in enumerate(passages)]
                    })
            else:
                # Multiple chapters - only scrape missing ones
                for i, chapter_slug in chapters_to_scrape:
                    url = f"{info['base_url']}/{chapter_slug}"
                    print(f"    [{i}/{len(info['chapters'])}] {chapter_slug}...")
                    passages = fetch_chapter(url)

                    if passages:
                        output["chapters"].append({
                            "number": str(i),
                            "title": format_chapter_title(chapter_slug),
                            "slug": chapter_slug,
                            "passages": [{"ref": f"{i}:{j+1}", **p} for j, p in enumerate(passages)]
                        })

                # Sort chapters by number after adding new ones
                output["chapters"].sort(key=lambda ch: int(ch.get("number", 0)))

        except KeyboardInterrupt:
            print("\n\nInterrupted! Saving partial progress...")
            save_output(output, output_path)
            print("Run with --resume to continue later")
            sys.exit(0)

        save_output(output, output_path)

    print("\nDone!")


if __name__ == "__main__":
    main()
