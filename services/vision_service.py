from google.cloud import vision
from google.cloud.exceptions import GoogleCloudError
from google.auth.exceptions import DefaultCredentialsError
from typing import Dict, Any, List, Optional
import io
import base64
import logging
from datetime import datetime

from config import settings

logger = logging.getLogger(__name__)

class VisionService:
    """Google Cloud Vision 分析服务"""
    
    def __init__(self):
        self.client = None
        self.enabled = False
        
        try:
            # 尝试初始化Google Cloud Vision客户端
            self.client = vision.ImageAnnotatorClient()
            self.enabled = True
            logger.info("Google Cloud Vision客户端初始化成功")
        except DefaultCredentialsError:
            logger.warning("Google Cloud凭据未找到，Vision分析功能将被禁用")
            self.enabled = False
        except Exception as e:
            logger.error(f"Google Cloud Vision初始化失败: {e}")
            self.enabled = False
    
    def is_enabled(self) -> bool:
        """检查Vision服务是否可用"""
        return self.enabled
    
    async def analyze_image(self, image_content: bytes, analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """
        分析图像内容
        analysis_type: comprehensive, objects, text, landmarks, faces
        """
        if not self.enabled:
            logger.warning("Vision服务未启用，返回模拟结果")
            return {
                "objects": [],
                "text": "",
                "landmarks": [],
                "labels": [],
                "faces": [],
                "error": "Vision服务未启用 - Google Cloud凭据未找到",
                "enabled": False
            }
            
        try:
            image = vision.Image(content=image_content)
            results = {"enabled": True}
            
            if analysis_type == "comprehensive" or analysis_type == "all":
                # 综合分析
                results.update(await self._detect_objects(image))
                results.update(await self._detect_text(image))
                results.update(await self._detect_landmarks(image))
                results.update(await self._detect_labels(image))
                results.update(await self._detect_faces(image))
                results.update(await self._analyze_safe_search(image))
                
            elif analysis_type == "objects":
                results.update(await self._detect_objects(image))
                
            elif analysis_type == "text":
                results.update(await self._detect_text(image))
                
            elif analysis_type == "landmarks":
                results.update(await self._detect_landmarks(image))
                
            elif analysis_type == "labels":
                results.update(await self._detect_labels(image))
                
            elif analysis_type == "faces":
                results.update(await self._detect_faces(image))
                
            elif analysis_type == "safety":
                results.update(await self._analyze_safe_search(image))
            
            results["analysis_time"] = datetime.now().isoformat()
            results["analysis_type"] = analysis_type
            
            return results
            
        except GoogleCloudError as e:
            raise Exception(f"Google Cloud Vision API错误: {str(e)}")
        except Exception as e:
            raise Exception(f"图像分析失败: {str(e)}")
    
    async def _detect_objects(self, image: vision.Image) -> Dict[str, Any]:
        """检测图像中的对象"""
        try:
            response = self.client.object_localization(image=image)
            objects = []
            
            for obj in response.localized_object_annotations:
                vertices = []
                for vertex in obj.bounding_poly.normalized_vertices:
                    vertices.append({"x": vertex.x, "y": vertex.y})
                
                objects.append({
                    "name": obj.name,
                    "confidence": obj.score,
                    "bounding_box": vertices
                })
            
            return {"objects": objects}
            
        except Exception as e:
            print(f"对象检测失败: {e}")
            return {"objects": []}
    
    async def _detect_text(self, image: vision.Image) -> Dict[str, Any]:
        """检测图像中的文本"""
        try:
            response = self.client.text_detection(image=image)
            texts = []
            
            if response.text_annotations:
                # 第一个结果是完整文本
                full_text = response.text_annotations[0].description
                
                # 其余是单个文字/词语
                for text in response.text_annotations[1:]:
                    vertices = []
                    for vertex in text.bounding_poly.vertices:
                        vertices.append({"x": vertex.x, "y": vertex.y})
                    
                    texts.append({
                        "text": text.description,
                        "bounding_box": vertices
                    })
                
                return {
                    "text_detection": {
                        "full_text": full_text,
                        "individual_texts": texts
                    }
                }
            
            return {"text_detection": {"full_text": "", "individual_texts": []}}
            
        except Exception as e:
            print(f"文本检测失败: {e}")
            return {"text_detection": {"full_text": "", "individual_texts": []}}
    
    async def _detect_landmarks(self, image: vision.Image) -> Dict[str, Any]:
        """检测图像中的地标"""
        try:
            response = self.client.landmark_detection(image=image)
            landmarks = []
            
            for landmark in response.landmark_annotations:
                locations = []
                for location in landmark.locations:
                    locations.append({
                        "latitude": location.lat_lng.latitude,
                        "longitude": location.lat_lng.longitude
                    })
                
                landmarks.append({
                    "name": landmark.description,
                    "confidence": landmark.score,
                    "locations": locations
                })
            
            return {"landmarks": landmarks}
            
        except Exception as e:
            print(f"地标检测失败: {e}")
            return {"landmarks": []}
    
    async def _detect_labels(self, image: vision.Image) -> Dict[str, Any]:
        """检测图像标签"""
        try:
            response = self.client.label_detection(image=image)
            labels = []
            
            for label in response.label_annotations:
                labels.append({
                    "name": label.description,
                    "confidence": label.score,
                    "topicality": label.topicality
                })
            
            return {"labels": labels}
            
        except Exception as e:
            print(f"标签检测失败: {e}")
            return {"labels": []}
    
    async def _detect_faces(self, image: vision.Image) -> Dict[str, Any]:
        """检测图像中的人脸"""
        try:
            response = self.client.face_detection(image=image)
            faces = []
            
            for face in response.face_annotations:
                vertices = []
                for vertex in face.bounding_poly.vertices:
                    vertices.append({"x": vertex.x, "y": vertex.y})
                
                faces.append({
                    "bounding_box": vertices,
                    "detection_confidence": face.detection_confidence,
                    "joy_likelihood": face.joy_likelihood.name,
                    "sorrow_likelihood": face.sorrow_likelihood.name,
                    "anger_likelihood": face.anger_likelihood.name,
                    "surprise_likelihood": face.surprise_likelihood.name
                })
            
            return {"faces": faces}
            
        except Exception as e:
            print(f"人脸检测失败: {e}")
            return {"faces": []}
    
    async def _analyze_safe_search(self, image: vision.Image) -> Dict[str, Any]:
        """安全搜索分析"""
        try:
            response = self.client.safe_search_detection(image=image)
            safe_search = response.safe_search_annotation
            
            return {
                "safe_search": {
                    "adult": safe_search.adult.name,
                    "spoof": safe_search.spoof.name,
                    "medical": safe_search.medical.name,
                    "violence": safe_search.violence.name,
                    "racy": safe_search.racy.name
                }
            }
            
        except Exception as e:
            print(f"安全搜索分析失败: {e}")
            return {"safe_search": {}}

# 全局Vision服务实例
vision_service = VisionService() 