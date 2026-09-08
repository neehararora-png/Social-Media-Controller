import os
import re
import json
import shutil
from datetime import datetime
from typing import Dict, List, Any

from PIL import Image, ImageDraw, ImageFont


class ImageGenerator:
    def __init__(self, output_dir: str = "output/generated_images/tiktok") -> None:
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    @staticmethod
    def _format_price(value) -> str:
        try:
            return f"{float(value):,.2f}"
        except Exception:
            return str(value)

    def create_single_crypto_image(self, crypto: Dict) -> str:
        width, height = 1080, 1920
        image = Image.new("RGB", (width, height), (14, 14, 24))
        draw = ImageDraw.Draw(image)

        accent = (140, 82, 255)
        green = (76, 190, 120)
        red = (220, 70, 95)
        white = (245, 245, 250)
        soft = (180, 180, 195)

        draw.rectangle([(0, 0), (width, 220)], fill=accent)
        draw.rectangle([(0, height - 120), (width, height)], fill=(35, 35, 50))

        name = crypto.get("name", "Unknown")
        symbol = crypto.get("symbol", "-")
        rank = crypto.get("rank", "-")
        price = self._format_price(crypto.get("price", "-"))
        change = crypto.get("change_24h", 0)
        change_text = f"24h: {change:+.2f}%" if isinstance(change, (int, float)) else f"24h: {change}"
        change_color = green if isinstance(change, (int, float)) and change >= 0 else red

        draw.text((40, 65), f"#{rank}  {symbol}", fill=white)
        draw.text((40, 290), name, fill=white)
        draw.text((40, 420), f"${price}", fill=white)
        draw.text((40, 540), change_text, fill=change_color)

        market_cap = crypto.get("market_cap", "-")
        volume = crypto.get("volume_24h", "-")
        draw.text((40, 700), f"Market Cap: {self._format_price(market_cap)}", fill=soft)
        draw.text((40, 780), f"Volume 24h: {self._format_price(volume)}", fill=soft)
        draw.text((40, height - 75), datetime.utcnow().strftime("Updated %Y-%m-%d %H:%M UTC"), fill=soft)

        filename = f"crypto_01_{str(symbol).lower()}.png"
        out_path = os.path.join(self.output_dir, filename)
        image.save(out_path, format="PNG")
        return out_path

    def _load_font(self, size: int, bold: bool = False):
        candidates = []
        if bold:
            candidates.extend([
                "C:/Windows/Fonts/segoeuib.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
            ])
        candidates.extend([
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ])
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    @staticmethod
    def _hex_to_rgb(value: str):
        value = value.lstrip("#")
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))

    def _draw_radial_glow(self, image: Image.Image, center: tuple[int, int], radius: int, color: tuple[int, int, int], max_alpha: int):
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        cx, cy = center
        for r in range(radius, 0, -12):
            alpha = int(max_alpha * (r / radius) ** 2)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*color, alpha))
        image.alpha_composite(overlay)

    def _draw_gold_bar(self, image: Image.Image):
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        shadow = (115, 90, 20, 70)
        draw.ellipse((190, 760, 500, 820), fill=shadow)

        top_poly = [(220, 610), (430, 610), (395, 665), (185, 665)]
        front_poly = [(185, 665), (395, 665), (395, 780), (185, 780)]
        side_poly = [(395, 665), (430, 610), (430, 725), (395, 780)]

        draw.polygon(top_poly, fill=(252, 246, 186, 255))
        draw.polygon(front_poly, fill=(191, 149, 63, 255))
        draw.polygon(side_poly, fill=(138, 90, 0, 255))

        font = self._load_font(24, bold=True)
        draw.text((235, 705), "FINE GOLD", fill=(92, 64, 0, 220), font=font)
        image.alpha_composite(overlay)

    def _draw_trend_chart(self, image: Image.Image, positive: bool):
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        if positive:
            color = self._hex_to_rgb("00ff88")
            points = [(420, 780), (560, 720), (690, 610), (860, 420)]
            area = points + [(860, 980), (420, 980)]
        else:
            color = self._hex_to_rgb("ff4d4d")
            points = [(420, 430), (560, 510), (690, 650), (860, 820)]
            area = points + [(860, 980), (420, 980)]

        draw.polygon(area, fill=(*color, 28))
        draw.line(points, fill=(*color, 255), width=12, joint="curve")
        end_x, end_y = points[-1]
        for radius, alpha in [(26, 40), (18, 90), (10, 255)]:
            draw.ellipse((end_x - radius, end_y - radius, end_x + radius, end_y + radius), fill=(*color, alpha))
        image.alpha_composite(overlay)

    def _draw_glass_card(self, image: Image.Image):
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rounded_rectangle((120, 1140, 960, 1620), radius=28, fill=(11, 21, 40, 165), outline=(212, 175, 55, 65), width=2)
        image.alpha_composite(overlay)

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        clean = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(name or "asset").strip())
        return clean[:80] or "asset"

    @staticmethod
    def _to_float(value: Any):
        try:
            return float(value)
        except Exception:
            return None

    def create_market_style_image(self, asset: Dict, output_path: str) -> str:
        width, height = 1080, 1920
        image = Image.new("RGB", (width, height), (10, 14, 26))
        draw = ImageDraw.Draw(image)

        gold = (212, 175, 55)
        white = (255, 255, 255)
        soft = (138, 153, 173)
        date_font = self._load_font(32)
        title_font = self._load_font(70, bold=True)
        label_font = self._load_font(30)
        asset_font = self._load_font(48, bold=True)
        price_font = self._load_font(92, bold=True)
        change_font = self._load_font(46, bold=True)

        date_text = datetime.now().strftime("[%B %d, %Y]").upper()
        draw.text((540, 120), date_text, fill=gold, font=date_font, anchor="mm")
        draw.text((540, 190), "MARKET UPDATE", fill=white, font=title_font, anchor="mm")

        draw.line([(580, 720), (680, 620), (760, 680), (880, 500)], fill=(255, 51, 51), width=12)

        draw.rounded_rectangle([(100, 920), (980, 1760)], radius=24, outline=(42, 53, 77), width=4, fill=(16, 20, 32))

        symbol = asset.get("symbol") or asset.get("requested_item") or asset.get("name") or "ASSET"
        name = asset.get("name") or symbol
        price_value = self._to_float(asset.get("price"))
        pct_value = self._to_float(asset.get("change_percent") or asset.get("change_24h"))

        asset_text = f"{name} / {symbol}".upper()
        price_text = f"${price_value:,.2f}" if isinstance(price_value, (int, float)) else f"${asset.get('price', '-') }"
        if isinstance(pct_value, (int, float)):
            pct_text = f"{pct_value:+.2f}%"
            pct_color = (50, 205, 50) if pct_value >= 0 else (255, 51, 51)
        else:
            pct_text = str(asset.get("change_percent") or asset.get("change_24h") or "N/A")
            pct_color = (255, 51, 51)

        draw.text((160, 1020), "ASSET", fill=soft, font=label_font)
        draw.text((160, 1080), asset_text, fill=white, font=asset_font)
        draw.text((160, 1220), "CURRENT PRICE", fill=soft, font=label_font)
        draw.text((160, 1300), price_text, fill=gold, font=price_font)
        draw.text((900, 1660), pct_text, fill=pct_color, font=change_font, anchor="rm")

        image.save(output_path, format="PNG")
        return output_path

    def _flatten_assets_from_json_payload(self, payload: Any) -> List[Dict]:
        assets: List[Dict] = []

        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and item.get("price") is not None:
                    assets.append(item)
            return assets

        if not isinstance(payload, dict):
            return assets

        if isinstance(payload.get("crypto"), list):
            assets.extend([row for row in payload["crypto"] if isinstance(row, dict) and row.get("price") is not None])

        market = payload.get("market")
        if isinstance(market, dict):
            for _, rows in market.items():
                if isinstance(rows, list):
                    assets.extend([row for row in rows if isinstance(row, dict) and row.get("price") is not None])

        for _, value in payload.items():
            if isinstance(value, list):
                assets.extend([row for row in value if isinstance(row, dict) and row.get("price") is not None])
            elif isinstance(value, dict):
                for _, nested in value.items():
                    if isinstance(nested, list):
                        assets.extend([row for row in nested if isinstance(row, dict) and row.get("price") is not None])

        unique_assets: List[Dict] = []
        seen = set()
        for asset in assets:
            key = (asset.get("source"), asset.get("name"), asset.get("symbol"), asset.get("price"), asset.get("change_percent"), asset.get("change_24h"))
            if key in seen:
                continue
            seen.add(key)
            unique_assets.append(asset)
        return unique_assets

    def create_images_from_current_date_json(self, data_base_dir: str = "output/data") -> Dict[str, Any]:
        date_folder = datetime.now().strftime("%Y-%m-%d")
        current_date_dir = os.path.join(data_base_dir, date_folder)
        if not os.path.isdir(current_date_dir):
            return {
                "images_created": 0,
                "output_dir": "",
                "json_files": [],
                "message": f"No current date folder found: {current_date_dir}",
            }

        json_files = [
            os.path.join(current_date_dir, f)
            for f in os.listdir(current_date_dir)
            if f.lower().endswith(".json")
        ]
        json_files.sort()

        output_dir = os.path.join(data_base_dir, f"{date_folder}_Images")
        if os.path.isdir(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        images_created = 0
        output_files: List[str] = []

        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            except Exception:
                continue

            assets = self._flatten_assets_from_json_payload(payload)
            source_tag = self._sanitize_filename(os.path.splitext(os.path.basename(json_file))[0])

            for idx, asset in enumerate(assets, 1):
                price_value = self._to_float(asset.get("price"))
                if not isinstance(price_value, (int, float)) or price_value < 1:
                    continue

                asset_name = self._sanitize_filename(asset.get("symbol") or asset.get("name") or f"asset_{idx}")
                file_name = f"{source_tag}_{idx:04d}_{asset_name}.png"
                out_path = os.path.join(output_dir, file_name)
                self.create_market_style_image(asset, out_path)
                images_created += 1
                output_files.append(out_path)

        return {
            "images_created": images_created,
            "output_dir": output_dir,
            "json_files": json_files,
            "image_files": output_files,
        }
