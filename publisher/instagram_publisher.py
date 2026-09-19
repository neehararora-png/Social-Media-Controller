import os
import random
import string
from typing import Any, Dict, List, Optional
import requests

from publisher.base import BasePublisher, PublishResult


class InstagramPublisher(BasePublisher):
    """
    Publisher for Instagram Business / Creator accounts via the Meta Graph API.
    """

    CAPTION_LIMIT = 2200

    def __init__(self, account_name: str, credentials: Optional[Dict[str, Any]] = None):
        super().__init__("Instagram", account_name, credentials)
        self.instagram_account_id = (
            self.credentials.get("account_id")
            or self.credentials.get("instagram_account_id")
            or os.environ.get("INSTAGRAM_ACCOUNT_ID", "").strip()
        )
        self.access_token = (
            self.credentials.get("access_token")
            or os.environ.get("INSTAGRAM_ACCESS_TOKEN", "").strip()
        )

    def is_configured(self) -> bool:
        return bool(self.instagram_account_id and self.access_token)

    def validate_credentials(self) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "valid": True,
                "simulated": True,
                "message": "No Instagram Business ID / Access Token. Running in sandbox/simulation mode.",
            }

        url = f"https://graph.facebook.com/v20.0/{self.instagram_account_id}"
        try:
            resp = requests.get(
                url,
                params={"fields": "id,username,name", "access_token": self.access_token},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                username = data.get("username", self.account_name)
                return {
                    "valid": True,
                    "simulated": False,
                    "message": f"Connected to Instagram account @{username} (ID: {data.get('id')})",
                }
            return {
                "valid": False,
                "simulated": False,
                "message": f"Meta Graph API error ({resp.status_code}): {resp.text}",
            }
        except Exception as e:
            return {"valid": False, "simulated": False, "message": f"Validation error: {str(e)}"}

    @staticmethod
    def _generate_fake_shortcode() -> str:
        chars = string.ascii_letters + string.digits + "_-"
        return "".join(random.choices(chars, k=11))

    def publish(
        self,
        content: str,
        media_paths: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> PublishResult:
        clean_handle = self.account_name.lstrip("@").strip() or "user"
        content = (content or "").strip()
        options = options or {}

        # Instagram requires media
        valid_media = self._verify_media_exists(media_paths)
        public_image_url = options.get("public_image_url") or options.get("image_url")

        if not valid_media and not public_image_url:
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message="Instagram requires an image or video attachment for posts.",
            )

        if len(content) > self.CAPTION_LIMIT:
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message=f"Instagram caption exceeds {self.CAPTION_LIMIT} characters (current length: {len(content)}).",
            )

        if not self.is_configured():
            # Simulation Mode
            shortcode = self._generate_fake_shortcode()
            post_id = str(random.randint(17900000000000000, 17999999999999999))
            post_url = f"https://www.instagram.com/p/{shortcode}/"
            media_info = f" with {len(valid_media)} media file(s)" if valid_media else " with image URL"
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=True,
                post_id=post_id,
                post_url=post_url,
                simulated=True,
                message=f"[Simulation] Photo post published to Instagram @{clean_handle}{media_info}.",
            )

        # Real Meta Graph API publication
        try:
            # Step 1: Create media container
            container_url = f"https://graph.facebook.com/v20.0/{self.instagram_account_id}/media"
            container_payload = {
                "caption": content,
                "access_token": self.access_token,
            }
            if public_image_url:
                container_payload["image_url"] = public_image_url
            else:
                # Meta Graph API requires an accessible URL
                return PublishResult(
                    platform=self.platform_name,
                    account_name=self.account_name,
                    success=False,
                    message="Meta Graph API requires images to be served from a publicly reachable URL. Provide 'image_url' or use simulation mode.",
                )

            res_cont = requests.post(container_url, data=container_payload, timeout=25)
            if res_cont.status_code not in (200, 201):
                return PublishResult(
                    platform=self.platform_name,
                    account_name=self.account_name,
                    success=False,
                    message=f"Instagram container creation error: {res_cont.text}",
                    raw_response=res_cont.json() if res_cont.text.startswith("{") else None,
                )

            creation_id = res_cont.json().get("id")

            # Step 2: Publish media container
            publish_url = f"https://graph.facebook.com/v20.0/{self.instagram_account_id}/media_publish"
            res_pub = requests.post(
                publish_url,
                data={"creation_id": creation_id, "access_token": self.access_token},
                timeout=25,
            )

            if res_pub.status_code in (200, 201):
                post_id = res_pub.json().get("id")
                return PublishResult(
                    platform=self.platform_name,
                    account_name=self.account_name,
                    success=True,
                    post_id=post_id,
                    post_url=f"https://www.instagram.com/p/{self._generate_fake_shortcode()}/",
                    simulated=False,
                    message=f"Published successfully to Instagram @{clean_handle}.",
                    raw_response=res_pub.json(),
                )

            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message=f"Instagram publish error: {res_pub.text}",
                raw_response=res_pub.json() if res_pub.text.startswith("{") else None,
            )
        except Exception as e:
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message=f"Instagram publishing failed: {str(e)}",
            )
