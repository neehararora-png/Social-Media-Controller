from data_processor.data_processor import DataProcessor
from scrapers.coinmarketcap_scraper import CoinMarketCapScraper
from scrapers.tradingeconomics_scraper import TradingEconomicsScraper
from scrapers.yahoofinance_scraper import YahooFinanceScraper
from image_generator.image_generator import ImageGenerator
from flask import Flask, jsonify, render_template, request
import os
import json
from datetime import datetime


CONNECTIONS_FILE = os.path.join("output", "connections.json")


def _load_connections() -> dict:
    if not os.path.exists(CONNECTIONS_FILE):
        return {}
    try:
        with open(CONNECTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_connections(connections: dict) -> None:
    os.makedirs(os.path.dirname(CONNECTIONS_FILE), exist_ok=True)
    with open(CONNECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(connections, f, indent=2, ensure_ascii=False)


def run_end_to_end() -> dict:
    cmc = CoinMarketCapScraper()
    te = TradingEconomicsScraper()
    processor = DataProcessor(output_dir="output/data")
    image_generator = ImageGenerator(output_dir="output/generated_images/tiktok")

    print("STEP 1: Scraping live data...")
    crypto = cmc.scrape_top_30()
    market = te.scrape_required_sections()

    print(f"- CoinMarketCap rows: {len(crypto)}")
    print(f"- TradingEconomics rows: {sum(len(v) for v in market.values())}")

    print("STEP 2: Processing and exporting (JSON only)...")
    clean_crypto = processor.process_crypto(crypto)
    clean_market = processor.process_market(market)
    date_dir = processor.get_date_output_dir()
    snapshot_json = os.path.join(date_dir, f"data_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
    with open(snapshot_json, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": datetime.utcnow().isoformat(),
                "crypto_count": len(clean_crypto),
                "market_counts": {k: len(v) for k, v in clean_market.items()},
                "crypto": clean_crypto,
                "market": clean_market,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    files = {
        "snapshot_json": snapshot_json,
    }

    print("STEP 3: Generating one demo image...")
    image_path = None
    image_generated = False
    if clean_crypto:
        image_path = image_generator.create_single_crypto_image(clean_crypto[0])
        image_generated = bool(image_path)

    print("Done. Output files:")
    for key, value in files.items():
        print(f"- {key}: {value}")

    result = {
        "counts": {
            "crypto": len(clean_crypto),
            "market": sum(len(v) for v in clean_market.values()),
        },
        "files": {
            **files,
            "image": image_path,
        },
        "image": {
            "generated": image_generated,
            "path": image_path,
        },
    }
    return result


def run_coinmarketcap_only() -> dict:
    cmc = CoinMarketCapScraper()
    processor = DataProcessor(output_dir="output/data")
    crypto = cmc.scrape_top_30()
    clean_crypto = processor.process_crypto(crypto)

    cmc_json = processor.get_path_in_date_dir("coinmarketcap_top30_latest.json")
    with open(cmc_json, "w", encoding="utf-8") as f:
        json.dump(clean_crypto, f, indent=2, ensure_ascii=False)

    return {
        "counts": {"crypto": len(clean_crypto)},
        "files": {
            "crypto_json": cmc_json,
        },
        "scraped_json": clean_crypto,
    }


def run_tradingeconomics_only() -> dict:
    te = TradingEconomicsScraper()
    processor = DataProcessor(output_dir="output/data")
    market = te.scrape_required_sections()
    clean_market = processor.process_market(market)

    for category, rows in clean_market.items():
        clean_market[category] = [
            row
            for row in rows
            if isinstance(row.get("price"), (int, float)) and row.get("price", 0) >= 1
        ]

    te_json = processor.get_path_in_date_dir("tradingeconomics_required_latest.json")
    with open(te_json, "w", encoding="utf-8") as f:
        json.dump(clean_market, f, indent=2, ensure_ascii=False)

    files = {
        "tradingeconomics_json": te_json,
    }

    return {
        "counts": {k: len(v) for k, v in clean_market.items()},
        "files": files,
        "scraped_json": clean_market,
    }


def run_yahoofinance_only() -> dict:
    yahoo = YahooFinanceScraper()
    processor = DataProcessor(output_dir="output/data")
    data_by_tab = yahoo.scrape_required_tabs()

    for tab, rows in data_by_tab.items():
        data_by_tab[tab] = [
            row
            for row in rows
            if isinstance(row.get("price"), (int, float)) and row.get("price", 0) >= 1
        ]

    json_path = processor.get_path_in_date_dir("yahoofinance_latest.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data_by_tab, f, indent=2, ensure_ascii=False)

    files = {
        "yahoofinance_json": json_path,
    }

    return {
        "counts": {k: len(v) for k, v in data_by_tab.items()},
        "files": files,
        "scraped_json": data_by_tab,
    }


def run_image_generator_from_current_date() -> dict:
    generator = ImageGenerator(output_dir="output/generated_images/tiktok")
    result = generator.create_images_from_current_date_json(data_base_dir="output/data")
    return {
        "counts": {
            "images_created": result.get("images_created", 0),
            "json_files": len(result.get("json_files", [])),
        },
        "files": {
            "images_output_dir": result.get("output_dir", ""),
            "json_inputs": result.get("json_files", []),
        },
        "generated_images": result.get("image_files", []),
        "message": result.get("message", ""),
    }


app = Flask(__name__, template_folder="templates")


@app.get("/")
def landing():
    return render_template("landing.html")


@app.get("/dashboard")
def home():
    return render_template("index.html")


@app.get("/connection-handler")
def connection_handler():
    return render_template("connection_handler.html")


@app.get("/image-builder")
def image_builder():
    return render_template("image_builder.html")


@app.get("/publish-work")
def publish_work():
    return render_template("publish_work.html")


@app.post("/api/run")
def api_run():
    try:
        result = run_end_to_end()
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/scrape/coinmarketcap")
def api_scrape_coinmarketcap():
    try:
        return jsonify(run_coinmarketcap_only()), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/scrape/tradingeconomics")
def api_scrape_tradingeconomics():
    try:
        return jsonify(run_tradingeconomics_only()), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/scrape/yahoofinance")
def api_scrape_yahoofinance():
    try:
        return jsonify(run_yahoofinance_only()), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/image-generator")
def api_image_generator():
    try:
        return jsonify(run_image_generator_from_current_date()), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.get("/api/connections")
def api_get_connections():
    try:
        return jsonify({"connections": _load_connections()}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/connections")
def api_create_or_update_connection():
    try:
        payload = request.get_json(force=True) or {}
        name = (payload.get("name") or "").strip()
        original_name = (payload.get("original_name") or "").strip()
        accounts = payload.get("accounts") or []

        if not name:
            return jsonify({"error": "Connection name is required"}), 400
        if not isinstance(accounts, list) or len(accounts) == 0:
            return jsonify({"error": "At least one account is required"}), 400
        for account in accounts:
            if not account.get("platform") or not account.get("account_name"):
                return jsonify({"error": "Each account must have a platform and account name"}), 400

        connections = _load_connections()
        if original_name and original_name in connections and original_name != name:
            del connections[original_name]
        connections[name] = {"accounts": accounts}
        _save_connections(connections)
        return jsonify({"success": True, "name": name}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.delete("/api/connections/<name>")
def api_delete_connection(name: str):
    try:
        connections = _load_connections()
        if name in connections:
            del connections[name]
            _save_connections(connections)
            return jsonify({"success": True}), 200
        return jsonify({"error": "Connection not found"}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/image-builder/generate")
def api_image_builder_generate():
    try:
        files = request.files.getlist("files") or []
        output_folder = (request.form.get("output_folder") or "").strip()
        use_custom_prompt = request.form.get("use_custom_prompt") == "1"
        custom_prompt = (request.form.get("custom_prompt") or "").strip()
        api_key = (request.form.get("api_key") or "").strip()

        if not files:
            return jsonify({"error": "No files uploaded"}), 400
        if not output_folder:
            return jsonify({"error": "Output folder is required"}), 400

        os.makedirs(output_folder, exist_ok=True)

        saved_files = []
        for f in files:
            if not f.filename:
                continue
            safe_name = os.path.basename(f.filename)
            out_path = os.path.join(output_folder, safe_name)
            f.save(out_path)
            saved_files.append(out_path)

        result = {
            "mode": "custom_prompt" if use_custom_prompt else "hardcoded_prompt",
            "output_folder": output_folder,
            "saved_input_files": saved_files,
            "files_count": len(saved_files),
        }
        if use_custom_prompt:
            result["custom_prompt_used"] = bool(custom_prompt)
            result["api_key_provided"] = bool(api_key)
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/publish-work")
def api_publish_work():
    try:
        files = request.files.getlist("files") or []
        connection_name = (request.form.get("connection_name") or "").strip()

        if not files:
            return jsonify({"error": "No files uploaded"}), 400
        if not connection_name:
            return jsonify({"error": "Connection is required"}), 400

        connections = _load_connections()
        connection = connections.get(connection_name)
        if not connection:
            return jsonify({"error": "Connection not found"}), 404

        accounts = connection.get("accounts") or []
        if not accounts:
            return jsonify({"error": "Selected connection has no accounts"}), 400

        results = {}
        for account in accounts:
            platform = account.get("platform")
            try:
                if platform in {"TikTok", "Instagram", "Snapchat", "Youtube", "X(Twitter)", "Facebook"}:
                    results[platform] = {"status": "pass", "message": f"Simulated upload to {platform}"}
                else:
                    results[platform] = {"status": "fail", "message": "Unsupported platform"}
            except Exception as e:
                results[platform] = {"status": "fail", "message": str(e)}

        return jsonify({"success": True, "connection_name": connection_name, "results": results}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
