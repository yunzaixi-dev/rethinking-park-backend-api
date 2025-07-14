import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from models.image import ImageInfo, DuplicateCheckResponse
from services.hash_service import hash_service
from config import settings

class StorageService:
    """图像元数据存储服务"""
    
    def __init__(self, storage_file: str = "image_metadata.json"):
        self.storage_file = storage_file
        self.hash_index_file = "hash_index.json"
        self.data = self._load_data()
        self.hash_index = self._load_hash_index()
    
    def _load_data(self) -> Dict[str, Dict[str, Any]]:
        """加载存储的数据"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def _load_hash_index(self) -> Dict[str, Dict[str, Any]]:
        """加载哈希索引"""
        if os.path.exists(self.hash_index_file):
            try:
                with open(self.hash_index_file, 'r', encoding='utf-8') as f:
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
    
    def _save_hash_index(self):
        """保存哈希索引"""
        try:
            with open(self.hash_index_file, 'w', encoding='utf-8') as f:
                json.dump(self.hash_index, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"保存哈希索引失败: {e}")
    
    async def check_duplicates(self, image_hash: str, perceptual_hash: Optional[str] = None) -> DuplicateCheckResponse:
        """检查重复图像"""
        exact_matches = []
        similar_images = []
        
        # 检查完全相同的图像（MD5哈希匹配）
        if image_hash in self.hash_index:
            exact_matches = [image_hash]
        
        # 检查相似图像（感知哈希匹配）
        if perceptual_hash and settings.ENABLE_DUPLICATE_DETECTION:
            for stored_hash, info in self.hash_index.items():
                stored_perceptual_hash = info.get('perceptual_hash')
                if stored_perceptual_hash and stored_hash != image_hash:
                    if hash_service.is_similar_image(
                        perceptual_hash, 
                        stored_perceptual_hash, 
                        settings.SIMILARITY_THRESHOLD
                    ):
                        similar_images.append({
                            'image_hash': stored_hash,
                            'similarity_score': hash_service.hamming_distance(perceptual_hash, stored_perceptual_hash),
                            'filename': info.get('filename', ''),
                            'upload_time': info.get('upload_time', '')
                        })
        
        is_duplicate = len(exact_matches) > 0
        
        return DuplicateCheckResponse(
            image_hash=image_hash,
            is_duplicate=is_duplicate,
            exact_matches=exact_matches,
            similar_images=similar_images
        )
    
    async def save_image_info(self, image_info: ImageInfo) -> bool:
        """保存图像信息"""
        try:
            # 保存主要信息
            self.data[image_info.image_id] = {
                "image_id": image_info.image_id,
                "image_hash": image_info.image_hash,
                "perceptual_hash": image_info.perceptual_hash,
                "filename": image_info.filename,
                "file_size": image_info.file_size,
                "content_type": image_info.content_type,
                "gcs_url": image_info.gcs_url,
                "upload_time": image_info.upload_time.isoformat(),
                "processed": image_info.processed,
                "analysis_results": image_info.analysis_results
            }
            
            # 更新哈希索引
            self.hash_index[image_info.image_hash] = {
                "image_id": image_info.image_id,
                "perceptual_hash": image_info.perceptual_hash,
                "filename": image_info.filename,
                "upload_time": image_info.upload_time.isoformat()
            }
            
            self._save_data()
            self._save_hash_index()
            return True
        except Exception as e:
            print(f"保存图像信息失败: {e}")
            return False
    
    async def get_image_info(self, image_id: str) -> Optional[ImageInfo]:
        """根据图像ID获取图像信息"""
        if image_id in self.data:
            data = self.data[image_id]
            return ImageInfo(
                image_id=data["image_id"],
                image_hash=data.get("image_hash", image_id),  # 向后兼容
                perceptual_hash=data.get("perceptual_hash"),
                filename=data["filename"],
                file_size=data["file_size"],
                content_type=data["content_type"],
                gcs_url=data["gcs_url"],
                upload_time=datetime.fromisoformat(data["upload_time"]),
                processed=data.get("processed", False),
                analysis_results=data.get("analysis_results")
            )
        return None
    
    async def get_image_info_by_hash(self, image_hash: str) -> Optional[ImageInfo]:
        """根据图像哈希获取图像信息"""
        # 首先检查哈希索引
        if image_hash in self.hash_index:
            image_id = self.hash_index[image_hash]["image_id"]
            return await self.get_image_info(image_id)
        
        # 如果索引中没有，搜索主数据
        for image_id, data in self.data.items():
            if data.get("image_hash") == image_hash:
                return ImageInfo(
                    image_id=data["image_id"],
                    image_hash=data.get("image_hash", image_id),
                    perceptual_hash=data.get("perceptual_hash"),
                    filename=data["filename"],
                    file_size=data["file_size"],
                    content_type=data["content_type"],
                    gcs_url=data["gcs_url"],
                    upload_time=datetime.fromisoformat(data["upload_time"]),
                    processed=data.get("processed", False),
                    analysis_results=data.get("analysis_results")
                )
        return None
    
    async def update_analysis_results(self, image_hash: str, analysis_results: Dict[str, Any]) -> bool:
        """更新分析结果（基于哈希）"""
        try:
            # 查找对应的图像ID
            image_info = await self.get_image_info_by_hash(image_hash)
            if not image_info:
                return False
            
            if image_info.image_id in self.data:
                self.data[image_info.image_id]["analysis_results"] = analysis_results
                self.data[image_info.image_id]["processed"] = True
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
                # 获取哈希值以删除索引
                image_hash = self.data[image_id].get("image_hash")
                
                # 删除主数据
                del self.data[image_id]
                
                # 删除哈希索引
                if image_hash and image_hash in self.hash_index:
                    del self.hash_index[image_hash]
                
                self._save_data()
                self._save_hash_index()
                return True
            return False
        except Exception as e:
            print(f"删除图像信息失败: {e}")
            return False
    
    async def delete_image_info_by_hash(self, image_hash: str) -> bool:
        """根据哈希删除图像信息"""
        image_info = await self.get_image_info_by_hash(image_hash)
        if image_info:
            return await self.delete_image_info(image_info.image_id)
        return False
    
    async def list_images(self, limit: int = 100, offset: int = 0) -> List[ImageInfo]:
        """列出图像信息"""
        try:
            items = list(self.data.items())[offset:offset + limit]
            images = []
            for image_id, data in items:
                images.append(ImageInfo(
                    image_id=data["image_id"],
                    image_hash=data.get("image_hash", image_id),
                    perceptual_hash=data.get("perceptual_hash"),
                    filename=data["filename"],
                    file_size=data["file_size"],
                    content_type=data["content_type"],
                    gcs_url=data["gcs_url"],
                    upload_time=datetime.fromisoformat(data["upload_time"]),
                    processed=data.get("processed", False),
                    analysis_results=data.get("analysis_results")
                ))
            return images
        except Exception as e:
            print(f"列出图像失败: {e}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_images = len(self.data)
        processed_images = sum(1 for data in self.data.values() if data.get("processed", False))
        total_size = sum(data.get("file_size", 0) for data in self.data.values())
        unique_hashes = len(self.hash_index)
        
        return {
            "total_images": total_images,
            "processed_images": processed_images,
            "unprocessed_images": total_images - processed_images,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "unique_images": unique_hashes,
            "duplicate_detection_enabled": settings.ENABLE_DUPLICATE_DETECTION
        }

# 创建全局实例
storage_service = StorageService() 