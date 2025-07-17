import hashlib
import io
from typing import Optional, Tuple

import imagehash
from PIL import Image


class ImageHashService:
    """图像哈希处理服务"""

    @staticmethod
    def calculate_md5_hash(image_content: bytes) -> str:
        """计算图像内容的MD5哈希值"""
        return hashlib.md5(image_content).hexdigest()

    @staticmethod
    def calculate_perceptual_hash(image_content: bytes) -> str:
        """计算图像的感知哈希值（用于检测相似图像）"""
        try:
            image = Image.open(io.BytesIO(image_content))
            # 使用平均哈希算法
            phash = imagehash.average_hash(image)
            return str(phash)
        except Exception as e:
            print(f"计算感知哈希失败: {e}")
            return None

    @staticmethod
    def calculate_combined_hash(image_content: bytes) -> Tuple[str, Optional[str]]:
        """计算组合哈希值：MD5（精确匹配）+ 感知哈希（相似检测）"""
        md5_hash = ImageHashService.calculate_md5_hash(image_content)
        perceptual_hash = ImageHashService.calculate_perceptual_hash(image_content)
        return md5_hash, perceptual_hash

    @staticmethod
    def hamming_distance(hash1: str, hash2: str) -> int:
        """计算两个哈希值的汉明距离（用于相似度检测）"""
        try:
            return bin(int(hash1, 16) ^ int(hash2, 16)).count("1")
        except:
            return float("inf")

    @staticmethod
    def is_similar_image(hash1: str, hash2: str, threshold: int = 5) -> bool:
        """判断两个图像是否相似（基于感知哈希）"""
        if not hash1 or not hash2:
            return False
        distance = ImageHashService.hamming_distance(hash1, hash2)
        return distance <= threshold


# 创建全局实例
hash_service = ImageHashService()
