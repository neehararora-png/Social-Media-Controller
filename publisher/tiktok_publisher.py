import os
import random
from typing import Any, Dict, List, Optional
import requests

from publisher.base import BasePublisher, PublishResult


class TikTokPublisher(BasePublisher):
    """
    Publisher for TikTok using the TikTok Content Posting API v2.
    """

    CAPTION_LIMIT = 4000

    def __init__(self, account_name: str, credentials: Optional[Dict[str, Any]] = None):
        super().__init__("TikTok", account_name, credentials)
        self.access_token = (
            self.credentials.get("access_token")
            or os.environ.get("TIKTOK_ACCESS_TOKEN", "").strip()
        )
        self.client_key = (
            self.credentials.get("client_key")
            or os.environ.get("TIKTOK_CLIENT_KEY", "").strip()
        )

    def is_configured(self) -> bool:
        return bool(self.access_token)

    def validate_credentials(self) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "valid": True,
                "simulated": True,
                "message": "No TikTok Access Token provided. Running in sandbox/simulation mode.",
            }

        url = "https://open.tiktokapis.com/v2/user/info/"
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            params = {"fields": "open_id,union_id,avatar_url,display_name"}
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json().get("data", {}).get("user", {})
                display_name = data.get("display_name", self.account_name)
                return {
                    "valid": True,
                    "simulated": False,
                    "message": f"Connected to TikTok account '{display_name}'",
                }
            return {
                "valid": False,
                "simulated": False,
                "message": f"TikTok API error ({resp.status_code}): {resp.text}",
            }
        except Exception as e:
            return {"valid": False, "simulated": False, "message": f"Validation failed: {str(e)}"}

    def publish(
        self,
        content: str,
        media_paths: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> PublishResult:
        clean_handle = self.account_name.lstrip("@").strip() or "creator"
        content = (content or "").strip()
        options = options or {}
        valid_media = self._verify_media_exists(media_paths)

        if not valid_media and not options.get("video_url") and not options.get("image_urls"):
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message="TikTok requires at least one video or photo for content publishing.",
            )

        if len(content) > self.CAPTION_LIMIT:
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message=f"TikTok title/caption exceeds {self.CAPTION_LIMIT} characters.",
            )

        if not self.is_configured():
            # Simulation Mode
            simulated_video_id = str(random.randint(7300000000000000000, 7399999999999999999))
            post_url = f"https://www.tiktok.com/@{clean_handle}/video/{simulated_video_id}"
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=True,
                post_id=simulated_video_id,
                post_url=post_url,
                simulated=True,
                message=f"[Simulation] Content posted to TikTok @{clean_handle} with {len(valid_media)} attachment(s).",
            )

        try:
            init_url = "https://open.tiktokapis.com/v2/post/publish/content/init/"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "post_info": {
                    "title": content[:2200],
                    "privacy_level": options.get("privacy_level", "PUBLIC_TO_EVERYONE"),
                    "disable_duet": options.get("disable_duet", False),
                    "disable_stitch": options.get("disable_stitch", False),
                    "disable_comment": options.get("disable_comment", False),
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "photo_images": options.get("image_urls", []),
                },
            }

            resp = requests.post(init_url, headers=headers, json=payload, timeout=30)
            if resp.status_code in (200, 201):
                data = resp.json().get("data", {})
                publish_id = data.get("publish_id")
                return PublishResult(
                    platform=self.platform_name,
                    account_name=self.account_name,
                    success=True,
                    post_id=publish_id,
                    post_url=f"https://www.tiktok.com/@{clean_handle}",
                    simulated=False,
                    message=f"Upload initialized on TikTok (publish_id: {publish_id}).",
                    raw_response=resp.json(),
                )

            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message=f"TikTok API error ({resp.status_code}): {resp.text}",
                raw_response=resp.json() if resp.text.startswith("{") else None,
            )
        except Exception as e:
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message=f"TikTok publishing failed: {str(e)}",
            )
