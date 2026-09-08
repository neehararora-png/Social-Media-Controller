import json
import os
from datetime import datetime
from typing import Dict, List


class DataProcessor:
    def __init__(self, output_dir: str = "output/data") -> None:
        self.base_output_dir = output_dir
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    @staticmethod
    def _date_folder_name() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def get_date_output_dir(self) -> str:
        date_dir = os.path.join(self.base_output_dir, self._date_folder_name())
        os.makedirs(date_dir, exist_ok=True)
        self.output_dir = date_dir
        return date_dir

    def get_path_in_date_dir(self, filename: str) -> str:
        date_dir = self.get_date_output_dir()
        return os.path.join(date_dir, filename)

    @staticmethod
    def _safe_float(value):
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return value

    def process_crypto(self, items: List[Dict]) -> List[Dict]:
        cleaned: List[Dict] = []
        for item in items:
            if not item.get("name") or not item.get("symbol"):
                continue
            cleaned.append(
                {
                    **item,
                    "price": self._safe_float(item.get("price")),
                    "change_24h": self._safe_float(item.get("change_24h")),
                    "market_cap": self._safe_float(item.get("market_cap")),
                    "volume_24h": self._safe_float(item.get("volume_24h")),
                }
            )
        return cleaned

    def process_market(self, by_category: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        out: Dict[str, List[Dict]] = {}
        for category, rows in by_category.items():
            cleaned = []
            for row in rows:
                if not row.get("name"):
                    continue
                cleaned.append(
                    {
                        **row,
                        "price": self._safe_float(row.get("price")),
                        "change": self._safe_float(row.get("change")),
                        "change_percent": self._safe_float(row.get("change_percent")),
                    }
                )
            out[category] = cleaned
        return out

    def export_all(
        self,
        crypto_rows: List[Dict],
        market_rows_by_category: Dict[str, List[Dict]],
    ) -> Dict[str, str]:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        date_dir = self.get_date_output_dir()
        files = {}

        json_path = os.path.join(date_dir, f"data_{ts}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "generated_at": datetime.utcnow().isoformat(),
                    "crypto_count": len(crypto_rows),
                    "market_counts": {k: len(v) for k, v in market_rows_by_category.items()},
                    "crypto": crypto_rows,
                    "market": market_rows_by_category,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        files["snapshot_json"] = json_path
        return files
