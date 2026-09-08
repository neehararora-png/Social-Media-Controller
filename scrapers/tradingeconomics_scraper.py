from datetime import datetime
from typing import Dict, List

import requests
from bs4 import BeautifulSoup


class TradingEconomicsScraper:
    def __init__(self, timeout: int = 25) -> None:
        self.timeout = timeout
        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.commodities_url = "https://tradingeconomics.com/commodities"
        self.shares_url = "https://tradingeconomics.com/shares"
        self.required_commodities = {
            "Crude Oil": ["crude oil", "wti crude", "brent"],
            "Natural Gas": ["natural gas", "nat gas"],
            "Coal": ["coal"],
            "Propane": ["propane"],
            "Gold": ["gold"],
            "Silver": ["silver"],
            "Copper": ["copper"],
            "Steel": ["steel"],
            "Lithium": ["lithium"],
            "Platinum": ["platinum"],
            "Lumber": ["lumber"],
            "Aluminum": ["aluminum", "aluminium"],
            "Tin": ["tin"],
            "Zinc": ["zinc"],
            "Nickel": ["nickel"],
            "Palladium": ["palladium"],
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
    def _safe_lower(value) -> str:
        return str(value).strip().lower() if value is not None else ""

    def _fetch_html(self, url: str) -> str:
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    @staticmethod
    def _find_index(headers: List[str], options: List[str], default: int) -> int:
        lowered = [h.lower() for h in headers]
        for idx, text in enumerate(lowered):
            if any(opt in text for opt in options):
                return idx
        return default

    def _parse_rows_with_headers(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.select("table")
        if not tables:
            return []
        parsed: List[Dict] = []
        now = datetime.utcnow().isoformat()

        for table in tables:
            headers = [th.get_text(" ", strip=True) for th in table.select("thead th")]
            if not headers:
                first_row = table.select_one("tr")
                headers = [th.get_text(" ", strip=True) for th in first_row.select("th")] if first_row else []

            name_idx = self._find_index(headers, ["commodity", "name", "company", "symbol"], 0)
            price_idx = self._find_index(headers, ["price", "last"], 1)
            pct_idx = self._find_index(headers, ["%", "percent", "chg%", "change %"], 3)
            weekly_idx = self._find_index(headers, ["weekly", "1w", "week"], -1)

            rows = table.select("tbody tr") or table.select("tr")
            for tr in rows:
                cells = [c.get_text(" ", strip=True) for c in tr.select("td")]
                if len(cells) < 2:
                    continue

                name = cells[name_idx] if name_idx < len(cells) else cells[0]
                price = self._to_number(cells[price_idx]) if price_idx < len(cells) else None
                change_pct = self._to_number(cells[pct_idx]) if pct_idx < len(cells) else None
                weekly_change = self._to_number(cells[weekly_idx]) if weekly_idx >= 0 and weekly_idx < len(cells) else None

                if not isinstance(price, (int, float)) or price < 1:
                    continue

                parsed.append(
                    {
                        "name": name,
                        "price": price,
                        "change_percent": change_pct,
                        "weekly_change": weekly_change,
                        "scraped_at": now,
                        "source": "tradingeconomics",
                    }
                )

        return parsed

    def _match_commodity_label(self, raw_name: str) -> str:
        normalized = self._safe_lower(raw_name)
        for label, aliases in self.required_commodities.items():
            if any(alias in normalized for alias in aliases):
                return label
        return ""

    def scrape_commodities_required(self) -> List[Dict]:
        html = self._fetch_html(self.commodities_url)
        parsed = self._parse_rows_with_headers(html)
        best_by_label: Dict[str, Dict] = {}
        for row in parsed:
            label = self._match_commodity_label(row.get("name", ""))
            if not label:
                continue
            if label not in best_by_label:
                best_by_label[label] = row

        out: List[Dict] = []
        now = datetime.utcnow().isoformat()
        for label in self.required_commodities.keys():
            base = best_by_label.get(label)
            if base:
                out.append(
                    {
                        **base,
                        "requested_item": label,
                        "found": True,
                        "category": "commodities",
                    }
                )
            else:
                out.append(
                    {
                        "name": label,
                        "requested_item": label,
                        "price": None,
                        "change_percent": None,
                        "weekly_change": None,
                        "scraped_at": now,
                        "source": "tradingeconomics",
                        "found": False,
                        "category": "commodities",
                    }
                )
        return out

    def scrape_shares_top_gainers_losers(self, top_n: int = 10) -> Dict[str, List[Dict]]:
        html = self._fetch_html(self.shares_url)
        parsed = self._parse_rows_with_headers(html)
        rows_with_pct = [
            r
            for r in parsed
            if isinstance(r.get("change_percent"), (int, float))
            and isinstance(r.get("price"), (int, float))
            and r.get("price", 0) >= 1
        ]

        gainers_sorted = sorted(rows_with_pct, key=lambda x: x.get("change_percent", 0), reverse=True)
        losers_sorted = sorted(rows_with_pct, key=lambda x: x.get("change_percent", 0))

        gainers = [
            {
                **row,
                "category": "shares_top_gainers",
            }
            for row in gainers_sorted[:top_n]
        ]
        losers = [
            {
                **row,
                "category": "shares_top_losers",
            }
            for row in losers_sorted[:top_n]
        ]

        return {
            "shares_top_gainers": gainers,
            "shares_top_losers": losers,
        }

    def scrape_all(self) -> Dict[str, List[Dict]]:
        result: Dict[str, List[Dict]] = {
            "commodities": self.scrape_commodities_required(),
        }
        result.update(self.scrape_shares_top_gainers_losers())
        return result

    def scrape_required_sections(self) -> Dict[str, List[Dict]]:
        return self.scrape_all()
