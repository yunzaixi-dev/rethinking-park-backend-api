import os
import uuid
from datetime import datetime
from typing import Tuple, Optional
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from PIL import Image
import io

from config import settings

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
                return False, f"无效的图像文件: {str(e)}"
                
        except Exception as e:
            return False, f"验证失败: {str(e)}"
    
    async def upload_image(self, file_content: bytes, filename: str, content_type: str) -> Tuple[str, str]:
        """
        上传图像到GCS
        返回: (image_id, gcs_url)
        """
        try:
            if not self.bucket:
                await self.initialize()
            
            # 生成唯一的图像ID和文件名
            image_id = str(uuid.uuid4())
            file_ext = os.path.splitext(filename)[1].lower()
            gcs_filename = f"images/{datetime.now().strftime('%Y/%m/%d')}/{image_id}{file_ext}"
            
            # 创建blob并上传
            blob = self.bucket.blob(gcs_filename)
            blob.upload_from_string(
                file_content,
                content_type=content_type
            )
            
            # 设置blob为公开可读（可选）
            # blob.make_public()
            
            # 生成签名URL（有效期1小时）
            gcs_url = blob.generate_signed_url(
                expiration=datetime.now().timestamp() + 3600,
                method='GET'
            )
            
            return image_id, gcs_url
            
        except GoogleCloudError as e:
            raise Exception(f"上传到GCS失败: {str(e)}")
        except Exception as e:
            raise Exception(f"上传图像失败: {str(e)}")
    
    async def get_image_url(self, image_id: str) -> Optional[str]:
        """根据图像ID获取访问URL"""
        try:
            if not self.bucket:
                await self.initialize()
            
            # 查找对应的blob
            blobs = list(self.bucket.list_blobs(prefix=f"images/"))
            for blob in blobs:
                if image_id in blob.name:
                    return blob.generate_signed_url(
                        expiration=datetime.now().timestamp() + 3600,
                        method='GET'
                    )
            return None
            
        except Exception as e:
            print(f"获取图像URL失败: {e}")
            return None
    
    async def download_image(self, image_id: str) -> Optional[bytes]:
        """下载图像内容用于分析"""
        try:
            if not self.bucket:
                await self.initialize()
            
            # 查找对应的blob
            blobs = list(self.bucket.list_blobs(prefix=f"images/"))
            for blob in blobs:
                if image_id in blob.name:
                    return blob.download_as_bytes()
            return None
            
        except Exception as e:
            print(f"下载图像失败: {e}")
            return None
    
    async def delete_image(self, image_id: str) -> bool:
        """删除图像"""
        try:
            if not self.bucket:
                await self.initialize()
            
            # 查找并删除对应的blob
            blobs = list(self.bucket.list_blobs(prefix=f"images/"))
            for blob in blobs:
                if image_id in blob.name:
                    blob.delete()
                    return True
            return False
            
        except Exception as e:
            print(f"删除图像失败: {e}")
            return False

# 全局GCS服务实例
gcs_service = GCSService() 