import os
import random
import time
from typing import Any, Dict, List, Optional
import requests

from publisher.base import BasePublisher, PublishResult
from publisher.oauth_helper import generate_oauth1_header


class XPublisher(BasePublisher):
    """
    Publisher for X (formerly Twitter) using Twitter API v2 (Tweets)
    and API v1.1 (Media Upload).
    """

    CHAR_LIMIT = 280

    def __init__(self, account_name: str, credentials: Optional[Dict[str, Any]] = None):
        super().__init__("X (Twitter)", account_name, credentials)
        self.api_key = self.credentials.get("api_key") or os.environ.get("X_API_KEY", "").strip()
        self.api_secret = self.credentials.get("api_secret") or os.environ.get("X_API_SECRET", "").strip()
        self.access_token = self.credentials.get("access_token") or os.environ.get("X_ACCESS_TOKEN", "").strip()
        self.access_token_secret = self.credentials.get("access_token_secret") or os.environ.get("X_ACCESS_TOKEN_SECRET", "").strip()
        self.bearer_token = self.credentials.get("bearer_token") or os.environ.get("X_BEARER_TOKEN", "").strip()

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret and self.access_token and self.access_token_secret)

    def validate_credentials(self) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "valid": True,
                "simulated": True,
                "message": "No API keys provided. Running in sandbox/simulation mode.",
            }

        url = "https://api.twitter.com/2/users/me"
        try:
            auth_header = generate_oauth1_header(
                method="GET",
                url=url,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
            )
            resp = requests.get(url, headers={"Authorization": auth_header}, timeout=15)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                username = data.get("username", self.account_name)
                return {
                    "valid": True,
                    "simulated": False,
                    "message": f"Connected to X as @{username} (ID: {data.get('id')})",
                }
            return {
                "valid": False,
                "simulated": False,
                "message": f"X API error ({resp.status_code}): {resp.text}",
            }
        except Exception as e:
            return {"valid": False, "simulated": False, "message": f"Connection test failed: {str(e)}"}

    def _upload_media(self, file_path: str) -> Optional[str]:
        """Upload image to Twitter v1.1 media endpoint and return media_id_string."""
        upload_url = "https://upload.twitter.com/1.1/media/upload.json"
        auth_header = generate_oauth1_header(
            method="POST",
            url=upload_url,
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access_token,
            access_token_secret=self.access_token_secret,
        )

        with open(file_path, "rb") as media_file:
            files = {"media": media_file}
            headers = {"Authorization": auth_header}
            resp = requests.post(upload_url, headers=headers, files=files, timeout=30)

        if resp.status_code in (200, 201, 202):
            return resp.json().get("media_id_string")
        raise RuntimeError(f"X media upload failed ({resp.status_code}): {resp.text}")

    def publish(
        self,
        content: str,
        media_paths: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> PublishResult:
        clean_handle = self.account_name.lstrip("@").strip() or "user"
        content = (content or "").strip()

        # Character limit check
        if len(content) > self.CHAR_LIMIT:
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message=f"Tweet text exceeds {self.CHAR_LIMIT} characters (current length: {len(content)}).",
            )

        valid_media = self._verify_media_exists(media_paths)

        if not self.is_configured():
            # Simulation Mode
            simulated_id = str(random.randint(1890000000000000000, 1899999999999999999))
            post_url = f"https://x.com/{clean_handle}/status/{simulated_id}"
            media_note = f" with {len(valid_media)} attachment(s)" if valid_media else ""
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=True,
                post_id=simulated_id,
                post_url=post_url,
                simulated=True,
                message=f"[Simulation] Tweet scheduled/published to @{clean_handle}{media_note}.",
            )

        try:
            media_ids = []
            for path in valid_media:
                media_id = self._upload_media(path)
                if media_id:
                    media_ids.append(media_id)

            tweet_url = "https://api.twitter.com/2/tweets"
            auth_header = generate_oauth1_header(
                method="POST",
                url=tweet_url,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
            )

            payload: Dict[str, Any] = {"text": content}
            if media_ids:
                payload["media"] = {"media_ids": media_ids}

            resp = requests.post(
                tweet_url,
                headers={"Authorization": auth_header, "Content-Type": "application/json"},
                json=payload,
                timeout=20,
            )

            if resp.status_code in (200, 201):
                res_data = resp.json().get("data", {})
                tweet_id = res_data.get("id")
                post_url = f"https://x.com/{clean_handle}/status/{tweet_id}"
                return PublishResult(
                    platform=self.platform_name,
                    account_name=self.account_name,
                    success=True,
                    post_id=tweet_id,
                    post_url=post_url,
                    simulated=False,
                    message=f"Tweet published successfully to @{clean_handle}.",
                    raw_response=resp.json(),
                )

            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message=f"X API error ({resp.status_code}): {resp.text}",
                raw_response=resp.json() if resp.text.startswith("{") else None,
            )
        except Exception as e:
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message=f"Publish failed: {str(e)}",
            )
