import os
import uuid
from datetime import datetime
from typing import Tuple, Optional
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from PIL import Image
import io

from config import settings
from services.hash_service import hash_service

class GCSService:
    """Google Cloud Storage 服务"""
    
    def __init__(self):
        self.client = storage.Client(project=settings.GOOGLE_CLOUD_PROJECT_ID)
        self.bucket_name = settings.GOOGLE_CLOUD_STORAGE_BUCKET
        self.bucket = None
        
    async def initialize(self):
        """初始化存储桶"""
        try:
            self.bucket = self.client.bucket(self.bucket_name)
            # 检查存储桶是否存在，如果不存在则创建
            if not self.bucket.exists():
                self.bucket = self.client.create_bucket(self.bucket_name)
                print(f"创建存储桶: {self.bucket_name}")
            else:
                print(f"使用现有存储桶: {self.bucket_name}")
        except GoogleCloudError as e:
            print(f"初始化GCS失败: {e}")
            raise
    
    def validate_image(self, file_content: bytes, filename: str) -> Tuple[bool, str]:
        """验证图像文件"""
        try:
            # 检查文件扩展名
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
                return False, f"不支持的文件格式: {file_ext}"
            
            # 检查文件大小
            if len(file_content) > settings.MAX_UPLOAD_SIZE:
                return False, f"文件太大，最大支持 {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
            
            # 验证图像格式
            try:
                image = Image.open(io.BytesIO(file_content))
                image.verify()  # 验证图像完整性
                return True, "验证通过"
            except Exception as e:
                return False, f"图像格式无效: {str(e)}"
                
        except Exception as e:
            return False, f"验证失败: {str(e)}"
    
    async def upload_image(self, file_content: bytes, filename: str, content_type: str) -> Tuple[str, str, str, Optional[str]]:
        """
        上传图像到GCS
        返回: (image_id, image_hash, gcs_url, perceptual_hash)
        """
        try:
            # 计算图像哈希
            md5_hash, perceptual_hash = hash_service.calculate_combined_hash(file_content)
            
            # 使用哈希值作为文件名，保证相同图像只存储一次
            file_ext = os.path.splitext(filename)[1].lower()
            blob_name = f"images/{md5_hash}{file_ext}"
            
            # 检查文件是否已存在
            blob = self.bucket.blob(blob_name)
            if blob.exists():
                print(f"📋 图像已存在，返回现有链接: {md5_hash[:8]}...")
                return md5_hash, md5_hash, blob.public_url, perceptual_hash
            
            # 上传新文件
            blob.upload_from_string(
                file_content,
                content_type=content_type
            )
            
            # 设置元数据
            metadata = {
                'original_filename': filename,
                'upload_time': datetime.now().isoformat(),
                'md5_hash': md5_hash,
                'file_size': str(len(file_content))
            }
            if perceptual_hash:
                metadata['perceptual_hash'] = perceptual_hash
            
            blob.metadata = metadata
            blob.patch()
            
            # 设置公开访问权限（如果需要）
            # blob.make_public()
            
            print(f"✅ 图像上传成功: {md5_hash[:8]}... -> {blob_name}")
            return md5_hash, md5_hash, blob.public_url, perceptual_hash
            
        except GoogleCloudError as e:
            print(f"GCS上传失败: {e}")
            raise
        except Exception as e:
            print(f"上传过程出错: {e}")
            raise
    
    async def get_image_url(self, image_hash: str, file_extension: str = None) -> Optional[str]:
        """通过哈希值获取图像URL"""
        try:
            if file_extension:
                blob_name = f"images/{image_hash}{file_extension}"
            else:
                # 尝试常见的图像格式
                for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                    blob_name = f"images/{image_hash}{ext}"
                    blob = self.bucket.blob(blob_name)
                    if blob.exists():
                        return blob.public_url
                return None
            
            blob = self.bucket.blob(blob_name)
            if blob.exists():
                return blob.public_url
            return None
            
        except GoogleCloudError as e:
            print(f"获取图像URL失败: {e}")
            return None
    
    async def download_image(self, image_hash: str, file_extension: str = None) -> Optional[bytes]:
        """通过哈希值下载图像内容"""
        try:
            if file_extension:
                blob_name = f"images/{image_hash}{file_extension}"
                blob = self.bucket.blob(blob_name)
                if blob.exists():
                    return blob.download_as_bytes()
            else:
                # 尝试常见的图像格式
                for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                    blob_name = f"images/{image_hash}{ext}"
                    blob = self.bucket.blob(blob_name)
                    if blob.exists():
                        return blob.download_as_bytes()
            
            return None
            
        except GoogleCloudError as e:
            print(f"下载图像失败: {e}")
            return None
    
    async def delete_image(self, image_hash: str, file_extension: str = None) -> bool:
        """通过哈希值删除图像"""
        try:
            if file_extension:
                blob_name = f"images/{image_hash}{file_extension}"
                blob = self.bucket.blob(blob_name)
                if blob.exists():
                    blob.delete()
                    return True
            else:
                # 尝试删除所有可能的格式
                deleted = False
                for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                    blob_name = f"images/{image_hash}{ext}"
                    blob = self.bucket.blob(blob_name)
                    if blob.exists():
                        blob.delete()
                        deleted = True
                return deleted
            
            return False
            
        except GoogleCloudError as e:
            print(f"删除图像失败: {e}")
            return False
    
    async def check_image_exists(self, image_hash: str) -> Tuple[bool, Optional[str]]:
        """检查图像是否已存在于GCS中"""
        try:
            for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                blob_name = f"images/{image_hash}{ext}"
                blob = self.bucket.blob(blob_name)
                if blob.exists():
                    return True, ext
            return False, None
        except Exception as e:
            print(f"检查图像存在性失败: {e}")
            return False, None

# 创建全局实例
gcs_service = GCSService() 