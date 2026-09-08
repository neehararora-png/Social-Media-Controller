import re
from datetime import datetime
from typing import Dict, List

import requests
from bs4 import BeautifulSoup


class YahooFinanceScraper:
    def __init__(self, timeout: int = 25) -> None:
        self.timeout = timeout
        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.tabs = {
            "most_active": "https://ca.finance.yahoo.com/markets/stocks/most-active/",
            "trending_now": "https://ca.finance.yahoo.com/markets/stocks/trending/",
            "top_gainers": "https://ca.finance.yahoo.com/markets/stocks/gainers/",
            "top_losers": "https://ca.finance.yahoo.com/markets/stocks/losers/",
        }
        self.screener_ids = {
            "most_active": "most_actives",
            "trending_now": "all_cryptocurrencies_us",
            "top_gainers": "day_gainers",
            "top_losers": "day_losers",
        }

    @staticmethod
    def _to_number(text: str):
        if text is None:
            return None
        raw = text.replace(",", "").replace("%", "").strip()
        if raw in {"", "-", "N/A"}:
            return None
        try:
            return float(raw)
        except ValueError:
            return text.strip()

    @staticmethod
    def _find_index(headers: List[str], options: List[str], default: int) -> int:
        lowered = [h.lower() for h in headers]
        for idx, text in enumerate(lowered):
            if any(opt in text for opt in options):
                return idx
        return default

    def _fetch_html(self, url: str) -> str:
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def _parse_table(self, html: str, tab_name: str) -> List[Dict]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one("table")
        if table is None:
            return []

        headers = [th.get_text(" ", strip=True) for th in table.select("thead th")]
        symbol_idx = self._find_index(headers, ["symbol", "ticker"], 0)
        name_idx = self._find_index(headers, ["name"], 1)
        price_idx = self._find_index(headers, ["price", "last"], 2)
        change_pct_idx = self._find_index(headers, ["change %", "% change", "%chg"], 4)
        wk52_idx = self._find_index(headers, ["52-week", "52 week", "52wk", "52w"], 6)

        rows = table.select("tbody tr") or table.select("tr")
        now = datetime.utcnow().isoformat()
        data: List[Dict] = []

        for tr in rows:
            cells = [c.get_text(" ", strip=True) for c in tr.select("td")]
            if len(cells) < 3:
                continue

            symbol = cells[symbol_idx] if symbol_idx < len(cells) else cells[0]
            name = cells[name_idx] if name_idx < len(cells) else (cells[1] if len(cells) > 1 else "")
            price = self._to_number(cells[price_idx]) if price_idx < len(cells) else None
            change_percent = self._to_number(cells[change_pct_idx]) if change_pct_idx < len(cells) else None
            wk52_change_percent = self._to_number(cells[wk52_idx]) if wk52_idx < len(cells) else None

            if not isinstance(price, (int, float)) or price < 1:
                continue

            data.append(
                {
                    "source": "yahoofinance",
                    "tab": tab_name,
                    "symbol": symbol,
                    "name": name,
                    "price": price,
                    "change_percent": change_percent,
                    "wk52_change_percent": wk52_change_percent,
                    "scraped_at": now,
                }
            )

        return data

    def _fetch_screener_json(self, screen_id: str) -> List[Dict]:
        url = f"https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?count=50&scrIds={screen_id}"
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()

        finance = payload.get("finance", {})
        results = finance.get("result", [])
        if not results:
            return []
        return results[0].get("quotes", []) or []

    def _parse_screener_quotes(self, quotes: List[Dict], tab_name: str) -> List[Dict]:
        now = datetime.utcnow().isoformat()
        data: List[Dict] = []
        for q in quotes:
            symbol = q.get("symbol")
            if not symbol:
                continue
            price = q.get("regularMarketPrice")
            if not isinstance(price, (int, float)) or price < 1:
                continue
            data.append(
                {
                    "source": "yahoofinance",
                    "tab": tab_name,
                    "symbol": symbol,
                    "name": q.get("shortName") or q.get("longName") or "",
                    "price": price,
                    "change_percent": q.get("regularMarketChangePercent"),
                    "wk52_change_percent": q.get("fiftyTwoWeekChangePercent"),
                    "scraped_at": now,
                }
            )
        return data

    def scrape_required_tabs(self) -> Dict[str, List[Dict]]:
        out: Dict[str, List[Dict]] = {}
        for tab, url in self.tabs.items():
            parsed: List[Dict] = []
            try:
                html = self._fetch_html(url)
                parsed = self._parse_table(html, tab)
            except Exception:
                parsed = []

            if not parsed:
                try:
                    quotes = self._fetch_screener_json(self.screener_ids[tab])
                    parsed = self._parse_screener_quotes(quotes, tab)
                except Exception:
                    parsed = []
            out[tab] = parsed
        return out
