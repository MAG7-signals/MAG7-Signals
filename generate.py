#!/usr/bin/env python3
"""Mag7 每日信号 page generator.

Builds a single self-contained index.html dashboard (Chinese UI) with the
latest price, day change %, and buy/sell signal state on 1h/2h/4h/daily/
weekly for the 7 US tech giants. Indicator is kept anonymous on the page.

Data: Yahoo Finance (single source). Intended to run once per trading day
after the US close; the weekly bar is the forming week until Friday close.
"""
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, "/home/hatch/workspace/trading")
sys.path.insert(0, "/home/hatch/workspace/trading/scanner")
from smi_watchlist_monitor import compute, fetch_1h, resample_1h  # noqa: E402
from weekly_candidates import fetch_weekly  # noqa: E402

ET = ZoneInfo("America/New_York")
BASE = "/home/hatch/workspace/trading/mag7_page"

MAG7 = [
    ("AAPL", "苹果"),
    ("MSFT", "微软"),
    ("GOOGL", "谷歌"),
    ("AMZN", "亚马逊"),
    ("NVDA", "英伟达"),
    ("META", "Meta"),
    ("TSLA", "特斯拉"),
]
TF_LABELS = [("1h", "1小时"), ("2h", "2小时"), ("4h", "4小时"),
             ("daily", "日线"), ("weekly", "周线")]
YOUTUBE_URL = "https://www.youtube.com/channel/UCDO3rHsGbwk9ITIOqnxKubQ"


def tf_signal(bars):
    """Return dict(side, trig, close) from a close-price frame, or None."""
    ind = compute(bars[["close"]])
    if len(ind) == 0:
        return None
    last = ind.iloc[-1]
    gap = float(last["SMI"]) - float(last["Signal"])
    side = (ind["SMI"] > ind["Signal"]).astype(int)
    flips = side[side != side.shift(1)]
    trig = flips.index[-1]
    return {"side": "BUY" if gap > 0 else "SELL",
            "trig": trig, "close": float(last["close"])}


def fmt_trig(t, weekly=False):
    t = t.astimezone(ET)
    if weekly:
        monday = (t - timedelta(days=t.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0)
        return monday.strftime("%Y-%m-%d")
    if t.hour == 0 and t.minute == 0:
        return t.strftime("%Y-%m-%d")
    return t.strftime("%m-%d %H:%M")


def analyze(ticker):
    """Full Mag7 row for one ticker; missing legs become None."""
    out = {"ticker": ticker, "legs": {}, "price": None, "chg": None}
    try:
        bars = fetch_1h(ticker)
    except Exception as e:
        out["error"] = str(e)
        return out
    if len(bars) == 0:
        out["error"] = "no 1h data"
        return out
    out["price"] = float(bars["close"].iloc[-1])
    # daily closes on ET calendar days (last bin may be today's forming day)
    dd = bars.resample("1D").agg({"close": "last"}).dropna()
    if len(dd) >= 2:
        out["chg"] = (float(dd["close"].iloc[-1]) /
                       float(dd["close"].iloc[-2]) - 1) * 100
    series = {
        "1h": bars,
        "2h": resample_1h(bars, 2),
        "4h": resample_1h(bars, 4),
        "daily": dd,
    }
    for key, b in series.items():
        try:
            out["legs"][key] = tf_signal(b) if len(b) else None
        except Exception:
            out["legs"][key] = None
    try:
        out["legs"]["weekly"] = tf_signal(fetch_weekly(ticker))
    except Exception:
        out["legs"]["weekly"] = None
    return out


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0e1320;color:#e8ecf4;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.5}
.wrap{max-width:760px;margin:0 auto;padding:16px 14px 40px}
header.hero{background:linear-gradient(135deg,#1b2a4a,#0e1320);border:1px solid #26324d;border-radius:14px;padding:22px 18px;margin-bottom:14px}
header.hero h1{font-size:24px;letter-spacing:2px}
header.hero p.sub{color:#9aa6bd;font-size:13px;margin-top:6px}
header.hero p.ts{color:#c7d0e2;font-size:13px;margin-top:10px}
.legend{background:#141b2e;border:1px solid #26324d;border-radius:10px;padding:10px 14px;font-size:13px;color:#9aa6bd;margin-bottom:14px}
.bd{display:inline-block;min-width:44px;text-align:center;font-size:13px;font-weight:700;border-radius:20px;padding:2px 10px;margin:0 4px}
.bd.buy{background:rgba(229,72,77,.15);color:#ff6b6f;border:1px solid #e5484d}
.bd.sell{background:rgba(47,158,95,.15);color:#4ade80;border:1px solid #2f9e5f}
.card{background:#141b2e;border:1px solid #26324d;border-radius:12px;padding:14px;margin-bottom:12px}
.chead{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.cname{font-size:17px;font-weight:700}
.ctick{color:#8b94a7;font-size:13px;margin-left:6px}
.cprice{text-align:right}
.px{font-size:18px;font-weight:700}
.chg{display:inline-block;font-size:13px;font-weight:700;border-radius:6px;padding:1px 8px;margin-left:6px}
.chg.up{color:#ff6b6f;background:rgba(229,72,77,.12)}
.chg.down{color:#4ade80;background:rgba(47,158,95,.12)}
.chg.flat{color:#9aa6bd;background:rgba(154,166,189,.12)}
.sigs{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}
.sig{background:#0e1320;border:1px solid #232d47;border-radius:8px;padding:8px 4px;text-align:center}
.sig .tf{display:block;font-size:11px;color:#8b94a7;margin-bottom:4px}
.sig .bd{margin:0 0 4px}
.sig .tg{display:block;font-size:10px;color:#6b7690}
.sig .na{font-size:12px;color:#6b7690}
.follow{background:#141b2e;border:1px solid #26324d;border-radius:12px;padding:16px;margin:18px 0;text-align:center}
.follow h2{font-size:16px;margin-bottom:6px}
.follow p{font-size:13px;color:#9aa6bd;margin-bottom:12px}
.btns{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.btn{display:inline-block;background:#e5484d;color:#fff;font-weight:700;font-size:14px;border-radius:24px;padding:10px 22px;text-decoration:none}
.btn.ghost{background:transparent;border:1px solid #3a4763;color:#c7d0e2}
footer{font-size:12px;color:#6b7690;text-align:center;line-height:1.8;padding:0 8px}
@media(max-width:480px){.sigs{grid-template-columns:repeat(5,1fr);gap:4px}.sig .tg{font-size:9px}}
"""


def badge_html(leg, weekly=False):
    if not leg:
        return '<span class="na">—</span>'
    cls = "buy" if leg["side"] == "BUY" else "sell"
    txt = "买入" if leg["side"] == "BUY" else "卖出"
    return (f'<span class="bd {cls}">{txt}</span>'
            f'<span class="tg">{fmt_trig(leg["trig"], weekly)}</span>')


def card_html(ticker, cname, data):
    if data.get("error") or data["price"] is None:
        body = '<div class="sig" style="grid-column:1/-1"><span class="na">数据缺失</span></div>'
        price_html = '<span class="px">—</span>'
    else:
        chg = data["chg"]
        if chg is None:
            chg_html = '<span class="chg flat">—</span>'
        else:
            cls = "up" if chg > 0 else ("down" if chg < 0 else "flat")
            chg_html = f'<span class="chg {cls}">{"+" if chg > 0 else ""}{chg:.2f}%</span>'
        price_html = f'<span class="px">${data["price"]:.2f}</span>{chg_html}'
        cells = []
        for key, label in TF_LABELS:
            cells.append(
                f'<div class="sig"><span class="tf">{label}</span>'
                f'{badge_html(data["legs"].get(key), weekly=(key == "weekly"))}</div>')
        body = "".join(cells)
    return (f'<article class="card"><div class="chead">'
            f'<div><span class="cname">{cname}</span>'
            f'<span class="ctick">{ticker}</span></div>'
            f'<div class="cprice">{price_html}</div></div>'
            f'<div class="sigs">{body}</div></article>')


def build(rows, updated):
    cards = "".join(card_html(t, n, d) for (t, n), d in zip(MAG7, rows))
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>七巨头每日信号</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header class="hero">
<h1>七巨头每日信号</h1>
<p class="sub">美国科技七巨头 · 每日走势与买卖信号追踪</p>
<p class="ts">更新时间：{updated}（美东）</p>
</header>
<div class="legend"><span class="bd buy">买入</span> 买入信号 <span class="bd sell">卖出</span> 卖出信号 ｜ 括号时间为信号触发K线 ｜ 日涨跌幅红色为涨、绿色为跌</div>
{cards}
<section class="follow">
<h2>📣 关注我们，每日信号更新</h2>
<p>把每天的信号追踪装进口袋</p>
<div class="btns">
<a class="btn" href="{YOUTUBE_URL}">YouTube · 散户投资者联盟</a>
<a class="btn ghost" href="#" data-todo="instagram-url">Instagram（待补充）</a>
<a class="btn ghost" href="#" data-todo="threads-url">Threads（待补充）</a>
</div>
</section>
<footer>
<p>信号由量化模型生成，仅供参考，不构成投资建议。市场有风险，投资需谨慎。</p>
<p>数据每日美东收盘后更新；周线为本周形成中K线，周五收盘后最终确认。</p>
</footer>
</div>
</body>
</html>
"""


def main():
    rows = []
    for ticker, cname in MAG7:
        try:
            data = analyze(ticker)
        except Exception as e:
            data = {"ticker": ticker, "legs": {}, "price": None,
                    "chg": None, "error": str(e)}
        rows.append(data)
        legs = data["legs"]
        leg_txt = " ".join(
            f"{k}={'—' if not legs.get(k) else legs[k]['side']}"
            for k, _ in TF_LABELS)
        px = f"${data['price']:.2f}" if data["price"] else "NO_DATA"
        chg = f"{data['chg']:+.2f}%" if data["chg"] is not None else "—"
        print(f"{ticker} {cname}: {px} {chg} | {leg_txt}")
    updated = datetime.now(ET).strftime("%Y-%m-%d %H:%M")
    html = build(rows, updated)
    out = f"{BASE}/index.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {out} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
