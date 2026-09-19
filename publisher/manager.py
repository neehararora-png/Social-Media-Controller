import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from publisher.base import BasePublisher, PublishResult
from publisher.facebook_publisher import FacebookPublisher
from publisher.instagram_publisher import InstagramPublisher
from publisher.threads_publisher import ThreadsPublisher
from publisher.tiktok_publisher import TikTokPublisher
from publisher.x_publisher import XPublisher


def load_env_file(env_path: str = ".env") -> None:
    """Safely load key-value pairs from .env without external dependencies."""
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


class PublisherManager:
    """
    Central Buffer-like publisher manager handling multi-platform dispatching,
    credentials, history tracking, drafts, and scheduled posts.
    """

    HISTORY_FILE = os.path.join("output", "posts_history.json")

    def __init__(self, history_file: Optional[str] = None):
        load_env_file()
        if history_file:
            self.history_file = history_file
        else:
            self.history_file = self.HISTORY_FILE
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)

    @staticmethod
    def normalize_platform_name(platform: str) -> str:
        p = (platform or "").lower().replace(" ", "").replace("-", "").replace("_", "")
        if "twitter" in p or p == "x" or "x(" in p:
            return "X (Twitter)"
        if "instagram" in p or p == "ig":
            return "Instagram"
        if "threads" in p:
            return "Threads"
        if "facebook" in p or p == "fb":
            return "Facebook"
        if "tiktok" in p:
            return "TikTok"
        if "youtube" in p:
            return "YouTube"
        if "snapchat" in p:
            return "Snapchat"
        return platform

    def create_publisher(self, platform: str, account_name: str, credentials: Optional[Dict] = None) -> BasePublisher:
        norm = self.normalize_platform_name(platform)
        creds = credentials or {}

        if norm == "X (Twitter)":
            return XPublisher(account_name=account_name, credentials=creds)
        elif norm == "Instagram":
            return InstagramPublisher(account_name=account_name, credentials=creds)
        elif norm == "Threads":
            return ThreadsPublisher(account_name=account_name, credentials=creds)
        elif norm == "Facebook":
            return FacebookPublisher(account_name=account_name, credentials=creds)
        elif norm == "TikTok":
            return TikTokPublisher(account_name=account_name, credentials=creds)
        else:
            # Generic fallback publisher for platforms like YouTube / Snapchat
            return _GenericPlatformPublisher(norm, account_name, creds)

    def validate_account(self, account: Dict[str, Any]) -> Dict[str, Any]:
        platform = account.get("platform", "")
        account_name = account.get("account_name", "")
        credentials = account.get("credentials") or {}
        publisher = self.create_publisher(platform, account_name, credentials)
        return publisher.validate_credentials()

    def _load_history(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_history(self, history: List[Dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def get_history(self, limit: int = 50, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        history = self._load_history()
        # Sort descending by created_at
        history.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        if status_filter:
            history = [h for h in history if h.get("status") == status_filter]
        return history[:limit]

    def publish_post(
        self,
        accounts: List[Dict[str, Any]],
        content: str,
        media_paths: Optional[List[str]] = None,
        platform_customizations: Optional[Dict[str, str]] = None,
        schedule_time: Optional[str] = None,
        is_draft: bool = False,
    ) -> Dict[str, Any]:
        """
        Buffer-like dispatcher: publishes across selected accounts simultaneously.
        """
        post_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        media_paths = media_paths or []
        platform_customizations = platform_customizations or {}

        # Handle Draft mode
        if is_draft:
            post_record = {
                "id": post_id,
                "created_at": created_at,
                "status": "draft",
                "content": content,
                "platform_customizations": platform_customizations,
                "media_files": [os.path.basename(p) for p in media_paths],
                "accounts": accounts,
                "results": {},
            }
            history = self._load_history()
            history.append(post_record)
            self._save_history(history)
            return {
                "success": True,
                "post_id": post_id,
                "status": "draft",
                "message": "Saved as draft.",
                "record": post_record,
            }

        # Handle Scheduled mode
        if schedule_time:
            post_record = {
                "id": post_id,
                "created_at": created_at,
                "schedule_time": schedule_time,
                "status": "scheduled",
                "content": content,
                "platform_customizations": platform_customizations,
                "media_files": [os.path.basename(p) for p in media_paths],
                "accounts": accounts,
                "results": {},
            }
            history = self._load_history()
            history.append(post_record)
            self._save_history(history)
            return {
                "success": True,
                "post_id": post_id,
                "status": "scheduled",
                "schedule_time": schedule_time,
                "message": f"Post scheduled for {schedule_time}.",
                "record": post_record,
            }

        # Immediate Publishing
        results: Dict[str, Dict[str, Any]] = {}
        all_passed = True
        any_passed = False

        for acc in accounts:
            platform = acc.get("platform", "Unknown")
            norm_platform = self.normalize_platform_name(platform)
            account_name = acc.get("account_name", "@user")
            credentials = acc.get("credentials") or {}

            # Account custom text if any, otherwise common content
            acc_content = platform_customizations.get(norm_platform) or platform_customizations.get(platform) or content

            publisher = self.create_publisher(norm_platform, account_name, credentials)
            result: PublishResult = publisher.publish(
                content=acc_content,
                media_paths=media_paths,
            )

            acc_key = f"{norm_platform} ({account_name})"
            results[acc_key] = result.to_dict()

            if result.success:
                any_passed = True
            else:
                all_passed = False

        overall_status = "published" if all_passed else ("partial_failure" if any_passed else "failed")

        post_record = {
            "id": post_id,
            "created_at": created_at,
            "status": overall_status,
            "content": content,
            "platform_customizations": platform_customizations,
            "media_files": [os.path.basename(p) for p in media_paths],
            "accounts": accounts,
            "results": results,
        }

        history = self._load_history()
        history.append(post_record)
        self._save_history(history)

        return {
            "success": any_passed,
            "post_id": post_id,
            "status": overall_status,
            "results": results,
            "record": post_record,
        }


class _GenericPlatformPublisher(BasePublisher):
    """Fallback publisher for non-primary platforms (e.g. Snapchat, YouTube)."""

    def validate_credentials(self) -> Dict[str, Any]:
        return {"valid": True, "simulated": True, "message": f"{self.platform_name} sandbox active"}

    def publish(
        self,
        content: str,
        media_paths: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> PublishResult:
        valid_media = self._verify_media_exists(media_paths)
        fake_id = f"sim_{uuid.uuid4().hex[:12]}"
        return PublishResult(
            platform=self.platform_name,
            account_name=self.account_name,
            success=True,
            post_id=fake_id,
            post_url=None,
            simulated=True,
            message=f"[Simulation] Published to {self.platform_name} ({self.account_name}) with {len(valid_media)} attachment(s).",
        )
