import os
import random
from typing import Any, Dict, List, Optional
import requests

from publisher.base import BasePublisher, PublishResult


class FacebookPublisher(BasePublisher):
    """
    Publisher for Facebook Pages using the Meta Graph API.
    """

    CHAR_LIMIT = 63206

    def __init__(self, account_name: str, credentials: Optional[Dict[str, Any]] = None):
        super().__init__("Facebook", account_name, credentials)
        self.page_id = (
            self.credentials.get("page_id")
            or self.credentials.get("account_id")
            or os.environ.get("FB_PAGE_ID", "").strip()
        )
        self.access_token = (
            self.credentials.get("access_token")
            or os.environ.get("FB_PAGE_ACCESS_TOKEN", "").strip()
        )

    def is_configured(self) -> bool:
        return bool(self.page_id and self.access_token)

    def validate_credentials(self) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "valid": True,
                "simulated": True,
                "message": "No Facebook Page ID / Page Access Token. Running in sandbox/simulation mode.",
            }

        url = f"https://graph.facebook.com/v20.0/{self.page_id}"
        try:
            resp = requests.get(
                url,
                params={"fields": "id,name,link", "access_token": self.access_token},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                name = data.get("name", self.account_name)
                return {
                    "valid": True,
                    "simulated": False,
                    "message": f"Connected to Facebook Page '{name}' (ID: {data.get('id')})",
                }
            return {
                "valid": False,
                "simulated": False,
                "message": f"Facebook API error ({resp.status_code}): {resp.text}",
            }
        except Exception as e:
            return {"valid": False, "simulated": False, "message": f"Validation failed: {str(e)}"}

    def publish(
        self,
        content: str,
        media_paths: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> PublishResult:
        clean_name = self.account_name.strip() or "Page"
        content = (content or "").strip()
        valid_media = self._verify_media_exists(media_paths)

        if not content and not valid_media:
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message="Facebook post must have either text message or media.",
            )

        if not self.is_configured():
            # Simulation Mode
            fake_page = self.page_id or "100234567890123"
            fake_post = str(random.randint(122000000000000, 122999999999999))
            post_id = f"{fake_page}_{fake_post}"
            post_url = f"https://www.facebook.com/{fake_page}/posts/{fake_post}"
            media_info = f" with {len(valid_media)} attachment(s)" if valid_media else ""
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=True,
                post_id=post_id,
                post_url=post_url,
                simulated=True,
                message=f"[Simulation] Published to Facebook Page '{clean_name}'{media_info}.",
            )

        try:
            if valid_media:
                # Upload first image as primary photo post
                first_image = valid_media[0]
                photo_url = f"https://graph.facebook.com/v20.0/{self.page_id}/photos"
                with open(first_image, "rb") as img_file:
                    files = {"source": img_file}
                    data = {"caption": content, "access_token": self.access_token}
                    resp = requests.post(photo_url, data=data, files=files, timeout=30)
            else:
                # Text-only post to page feed
                feed_url = f"https://graph.facebook.com/v20.0/{self.page_id}/feed"
                data = {"message": content, "access_token": self.access_token}
                resp = requests.post(feed_url, data=data, timeout=20)

            if resp.status_code in (200, 201):
                res_json = resp.json()
                post_id = res_json.get("post_id") or res_json.get("id")
                post_url = f"https://www.facebook.com/{post_id}"
                return PublishResult(
                    platform=self.platform_name,
                    account_name=self.account_name,
                    success=True,
                    post_id=post_id,
                    post_url=post_url,
                    simulated=False,
                    message=f"Published successfully to Facebook Page '{clean_name}'.",
                    raw_response=res_json,
                )

            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message=f"Facebook API error ({resp.status_code}): {resp.text}",
                raw_response=resp.json() if resp.text.startswith("{") else None,
            )
        except Exception as e:
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message=f"Facebook publish failed: {str(e)}",
            )
