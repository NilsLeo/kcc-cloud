from abc import ABC, abstractmethod
from datetime import timedelta
from typing import List, Optional


class StorageProvider(ABC):
    @abstractmethod
    def upload_file(self, file_path: str, object_name: str) -> bool:
        """Upload a file to storage"""
        pass

    @abstractmethod
    def file_exists(self, object_name: str) -> bool:
        """Check if a file exists in storage"""
        pass

    @abstractmethod
    def download_file(self, object_name: str, file_path: str) -> bool:
        """Download a file from storage"""
        pass

    @abstractmethod
    def get_presigned_url(
        self, object_name: str, expires: timedelta = timedelta(hours=1)
    ) -> str:
        """Get a presigned URL for downloading a file"""
        pass

    @abstractmethod
    def delete_file(self, object_name: str) -> bool:
        """Delete a file from storage"""
        pass

    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """List files in storage with given prefix"""
        pass
