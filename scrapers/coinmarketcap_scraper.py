import json
from datetime import datetime
from typing import Dict, List

import requests


class CoinMarketCapScraper:
    def __init__(self, timeout: int = 20) -> None:
        self.url = "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing?start=1&limit=30&sortBy=market_cap&sortType=desc&convert=USD&cryptoType=all&tagType=all&audited=false"
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0"
        }

    def scrape_top_30(self) -> List[Dict]:
        response = requests.get(self.url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()

        rows = payload.get("data", {}).get("cryptoCurrencyList", [])
        now = datetime.utcnow().isoformat()
        result: List[Dict] = []

        for row in rows:
            quote = (row.get("quotes") or [{}])[0]
            result.append(
                {
                    "source": "coinmarketcap",
                    "category": "crypto",
                    "rank": row.get("cmcRank"),
                    "name": row.get("name"),
                    "symbol": row.get("symbol"),
                    "price": quote.get("price"),
                    "change_24h": quote.get("percentChange24h"),
                    "scraped_at": now,
                }
            )

        return result

    def scrape(self) -> List[Dict]:
        return self.scrape_top_30()

    def export_json(self, data: List[Dict], path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
