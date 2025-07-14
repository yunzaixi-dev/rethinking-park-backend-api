import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from models.image import ImageInfo

class StorageService:
    """图像元数据存储服务"""
    
    def __init__(self, storage_file: str = "image_metadata.json"):
        self.storage_file = storage_file
        self.data = self._load_data()
    
    def _load_data(self) -> Dict[str, Dict[str, Any]]:
        """加载存储的数据"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def _save_data(self):
        """保存数据到文件"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"保存数据失败: {e}")
    
    async def save_image_info(self, image_info: ImageInfo) -> bool:
        """保存图像信息"""
        try:
            self.data[image_info.image_id] = {
                "image_id": image_info.image_id,
                "filename": image_info.filename,
                "file_size": image_info.file_size,
                "content_type": image_info.content_type,
                "gcs_url": image_info.gcs_url,
                "upload_time": image_info.upload_time.isoformat(),
                "processed": image_info.processed,
                "analysis_results": image_info.analysis_results
            }
            self._save_data()
            return True
        except Exception as e:
            print(f"保存图像信息失败: {e}")
            return False
    
    async def get_image_info(self, image_id: str) -> Optional[ImageInfo]:
        """获取图像信息"""
        try:
            if image_id in self.data:
                data = self.data[image_id]
                return ImageInfo(
                    image_id=data["image_id"],
                    filename=data["filename"],
                    file_size=data["file_size"],
                    content_type=data["content_type"],
                    gcs_url=data["gcs_url"],
                    upload_time=datetime.fromisoformat(data["upload_time"]),
                    processed=data.get("processed", False),
                    analysis_results=data.get("analysis_results")
                )
            return None
        except Exception as e:
            print(f"获取图像信息失败: {e}")
            return None
    
    async def update_analysis_results(self, image_id: str, analysis_results: Dict[str, Any]) -> bool:
        """更新图像分析结果"""
        try:
            if image_id in self.data:
                self.data[image_id]["analysis_results"] = analysis_results
                self.data[image_id]["processed"] = True
                self._save_data()
                return True
            return False
        except Exception as e:
            print(f"更新分析结果失败: {e}")
            return False
    
    async def delete_image_info(self, image_id: str) -> bool:
        """删除图像信息"""
        try:
            if image_id in self.data:
                del self.data[image_id]
                self._save_data()
                return True
            return False
        except Exception as e:
            print(f"删除图像信息失败: {e}")
            return False
    
    async def list_images(self, limit: int = 100, offset: int = 0) -> List[ImageInfo]:
        """列出图像信息"""
        try:
            images = []
            image_ids = list(self.data.keys())[offset:offset + limit]
            
            for image_id in image_ids:
                image_info = await self.get_image_info(image_id)
                if image_info:
                    images.append(image_info)
            
            return images
        except Exception as e:
            print(f"列出图像失败: {e}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            total_images = len(self.data)
            processed_images = sum(1 for item in self.data.values() if item.get("processed", False))
            total_size = sum(item.get("file_size", 0) for item in self.data.values())
            
            return {
                "total_images": total_images,
                "processed_images": processed_images,
                "unprocessed_images": total_images - processed_images,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2)
            }
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {}

# 全局存储服务实例
storage_service = StorageService() 