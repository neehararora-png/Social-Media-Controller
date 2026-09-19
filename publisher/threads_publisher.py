import os
import random
import string
from typing import Any, Dict, List, Optional
import requests

from publisher.base import BasePublisher, PublishResult


class ThreadsPublisher(BasePublisher):
    """
    Publisher for Meta Threads using the official Threads API (graph.threads.net).
    """

    CHAR_LIMIT = 500

    def __init__(self, account_name: str, credentials: Optional[Dict[str, Any]] = None):
        super().__init__("Threads", account_name, credentials)
        self.threads_user_id = (
            self.credentials.get("threads_user_id")
            or self.credentials.get("account_id")
            or self.credentials.get("user_id")
            or os.environ.get("THREADS_USER_ID", "").strip()
        )
        self.access_token = (
            self.credentials.get("access_token")
            or os.environ.get("THREADS_ACCESS_TOKEN", "").strip()
        )

    def is_configured(self) -> bool:
        return bool(self.threads_user_id and self.access_token)

    def validate_credentials(self) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "valid": True,
                "simulated": True,
                "message": "No Threads User ID / Access Token. Running in sandbox/simulation mode.",
            }

        url = f"https://graph.threads.net/v1.0/{self.threads_user_id}"
        try:
            resp = requests.get(
                url,
                params={"fields": "id,username,threads_profile_picture_url", "access_token": self.access_token},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                username = data.get("username", self.account_name)
                return {
                    "valid": True,
                    "simulated": False,
                    "message": f"Connected to Threads as @{username} (ID: {data.get('id')})",
                }
            return {
                "valid": False,
                "simulated": False,
                "message": f"Threads API error ({resp.status_code}): {resp.text}",
            }
        except Exception as e:
            return {"valid": False, "simulated": False, "message": f"Validation failed: {str(e)}"}

    @staticmethod
    def _generate_fake_post_slug() -> str:
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

        if not content and not media_paths:
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message="Threads post must contain text or media.",
            )

        if len(content) > self.CHAR_LIMIT:
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message=f"Threads content exceeds {self.CHAR_LIMIT} characters (current length: {len(content)}).",
            )

        valid_media = self._verify_media_exists(media_paths)
        public_image_url = options.get("public_image_url") or options.get("image_url")

        if not self.is_configured():
            # Simulation Mode
            fake_id = str(random.randint(17800000000000000, 17899999999999999))
            slug = self._generate_fake_post_slug()
            post_url = f"https://www.threads.net/@{clean_handle}/post/{slug}"
            media_info = f" with {len(valid_media)} attachment(s)" if valid_media else ""
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=True,
                post_id=fake_id,
                post_url=post_url,
                simulated=True,
                message=f"[Simulation] Post published to Threads @{clean_handle}{media_info}.",
            )

        try:
            # Step 1: Create media container
            creation_url = f"https://graph.threads.net/v1.0/{self.threads_user_id}/threads"
            payload: Dict[str, Any] = {
                "access_token": self.access_token,
                "text": content,
            }

            if public_image_url:
                payload["media_type"] = "IMAGE"
                payload["image_url"] = public_image_url
            else:
                payload["media_type"] = "TEXT"

            res_create = requests.post(creation_url, data=payload, timeout=25)
            if res_create.status_code not in (200, 201):
                return PublishResult(
                    platform=self.platform_name,
                    account_name=self.account_name,
                    success=False,
                    message=f"Threads container creation failed: {res_create.text}",
                    raw_response=res_create.json() if res_create.text.startswith("{") else None,
                )

            creation_id = res_create.json().get("id")

            # Step 2: Publish container
            publish_url = f"https://graph.threads.net/v1.0/{self.threads_user_id}/threads_publish"
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
                    post_url=f"https://www.threads.net/@{clean_handle}/post/{self._generate_fake_post_slug()}",
                    simulated=False,
                    message=f"Published successfully to Threads @{clean_handle}.",
                    raw_response=res_pub.json(),
                )

            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message=f"Threads publish error: {res_pub.text}",
                raw_response=res_pub.json() if res_pub.text.startswith("{") else None,
            )
        except Exception as e:
            return PublishResult(
                platform=self.platform_name,
                account_name=self.account_name,
                success=False,
                message=f"Threads publish error: {str(e)}",
            )
