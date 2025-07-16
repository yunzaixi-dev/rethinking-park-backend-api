from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime
import numpy as np
from PIL import Image
import io

from models.image import NaturalElementsResult, ColorInfo

logger = logging.getLogger(__name__)

class LabelAnalysisService:
    """Service for analyzing Google Vision labels to categorize natural elements and estimate coverage"""
    
    def __init__(self):
        # Define category mappings for natural elements
        self.category_mappings = {
            "vegetation": {
                "keywords": [
                    "tree", "plant", "grass", "flower", "leaf", "vegetation", "forest", 
                    "shrub", "bush", "fern", "moss", "vine", "bamboo", "palm",
                    "oak", "pine", "maple", "willow", "cedar", "birch", "eucalyptus",
                    "rose", "tulip", "daisy", "sunflower", "lily", "orchid", "cactus",
                    "herb", "weed", "algae", "lichen", "fungi", "mushroom"
                ],
                "weight_multiplier": 1.0
            },
            "sky": {
                "keywords": [
                    "sky", "cloud", "atmosphere", "horizon", "sunset", "sunrise", 
                    "blue sky", "cloudy", "overcast", "clear sky", "storm cloud",
                    "cumulus", "stratus", "cirrus", "weather", "air"
                ],
                "weight_multiplier": 1.2
            },
            "water": {
                "keywords": [
                    "water", "lake", "river", "pond", "stream", "ocean", "sea",
                    "fountain", "waterfall", "creek", "brook", "canal", "reservoir",
                    "pool", "puddle", "rain", "wet", "reflection", "ripple"
                ],
                "weight_multiplier": 1.1
            },
            "terrain": {
                "keywords": [
                    "ground", "soil", "rock", "stone", "trail", "dirt",
                    "sand", "gravel", "mud", "cliff", "hill", "mountain", 
                    "valley", "slope", "boulder"
                ],
                "weight_multiplier": 0.8
            },
            "built_environment": {
                "keywords": [
                    "building", "structure", "bench", "fence", "road", "sidewalk",
                    "bridge", "wall", "gate", "sign", "lamp", "pole", "tower",
                    "house", "shed", "pavilion", "gazebo", "playground", "statue",
                    "monument", "architecture", "construction", "urban", "city",
                    "path", "pavement", "concrete", "asphalt"
                ],
                "weight_multiplier": 0.9
            }
        }
        
        # Confidence thresholds for different analysis types
        self.confidence_thresholds = {
            "high_confidence": 0.8,
            "medium_confidence": 0.5,
            "low_confidence": 0.3
        }
        
    def analyze_by_labels(
        self,
        labels: List[Dict[str, Any]],
        image_content: Optional[bytes] = None,
        analysis_depth: str = "basic",
        include_confidence: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze image based on Google Vision labels to categorize natural elements
        """
        try:
            # Categorize labels into natural element types
            categorized_elements = self._categorize_labels(labels)
            
            # Calculate coverage estimation from label confidence
            coverage_stats = self._estimate_coverage_from_labels(categorized_elements)
            
            # Perform color analysis if image content is provided
            color_analysis = None
            if image_content and analysis_depth in ["comprehensive", "detailed"]:
                color_analysis = self._analyze_image_colors_for_labels(image_content, categorized_elements)
            
            # Generate natural element insights
            insights = self._generate_natural_element_insights(categorized_elements, coverage_stats)
            
            # Create comprehensive analysis result
            analysis_result = {
                "categorized_elements": categorized_elements,
                "coverage_statistics": coverage_stats,
                "natural_element_insights": insights,
                "analysis_metadata": {
                    "total_labels": len(labels),
                    "analysis_depth": analysis_depth,
                    "analysis_time": datetime.now().isoformat(),
                    "confidence_included": include_confidence
                }
            }
            
            # Add color analysis if available
            if color_analysis:
                analysis_result["color_analysis"] = color_analysis
            
            # Add detailed confidence analysis if requested
            if include_confidence:
                analysis_result["confidence_analysis"] = self._analyze_label_confidence(labels)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Label-based analysis failed: {e}")
            return {
                "error": f"Analysis failed: {str(e)}",
                "categorized_elements": {},
                "coverage_statistics": {},
                "analysis_metadata": {
                    "total_labels": len(labels) if labels else 0,
                    "analysis_depth": analysis_depth,
                    "analysis_time": datetime.now().isoformat(),
                    "success": False
                }
            }
    
    def _categorize_labels(self, labels: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Categorize labels into natural element types based on keywords"""
        categories = {
            "vegetation": [],
            "sky": [],
            "water": [],
            "terrain": [],
            "built_environment": [],
            "other": []
        }
        
        for label in labels:
            label_name = label.get("name", "").lower()
            confidence = label.get("confidence", 0.0)
            topicality = label.get("topicality", confidence)
            
            # Find matching category with priority order (built_environment first to catch specific items)
            categorized = False
            category_order = ["built_environment", "water", "sky", "terrain", "vegetation"]
            
            for category in category_order:
                config = self.category_mappings[category]
                # Check for keyword matches
                for keyword in config["keywords"]:
                    if keyword in label_name:
                        categories[category].append({
                            "name": label.get("name", ""),
                            "confidence": confidence,
                            "topicality": topicality,
                            "weighted_score": confidence * config["weight_multiplier"]
                        })
                        categorized = True
                        break
                if categorized:
                    break
            
            # Add to 'other' if not categorized
            if not categorized:
                categories["other"].append({
                    "name": label.get("name", ""),
                    "confidence": confidence,
                    "topicality": topicality,
                    "weighted_score": confidence
                })
        
        return categories
    
    def _estimate_coverage_from_labels(self, categorized_elements: Dict[str, Any]) -> Dict[str, float]:
        """Estimate coverage percentages based on label confidence and weights"""
        coverage_stats = {
            "vegetation_coverage": 0.0,
            "sky_coverage": 0.0,
            "water_coverage": 0.0,
            "terrain_coverage": 0.0,
            "built_environment_coverage": 0.0,
            "other_coverage": 0.0
        }
        
        # Calculate weighted scores for each category
        category_scores = {}
        total_weighted_score = 0.0
        
        for category, labels in categorized_elements.items():
            if labels:
                # Sum weighted scores for the category
                category_score = sum(label.get("weighted_score", 0) for label in labels)
                # Apply diminishing returns for multiple labels in same category
                category_score = category_score * (1 - 0.1 * max(0, len(labels) - 1))
                category_scores[category] = category_score
                total_weighted_score += category_score
        
        # Convert to percentages
        if total_weighted_score > 0:
            for category, score in category_scores.items():
                coverage_key = f"{category}_coverage"
                if coverage_key in coverage_stats:
                    coverage_stats[coverage_key] = min(100.0, (score / total_weighted_score) * 100)
        
        return coverage_stats
    
    def _analyze_image_colors_for_labels(
        self, 
        image_content: bytes, 
        categorized_elements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze image colors to support label-based coverage estimation"""
        try:
            # Load and process image
            pil_image = Image.open(io.BytesIO(image_content))
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Resize for faster processing
            img_small = pil_image.resize((200, 200))
            img_array = np.array(img_small)
            
            # Calculate color statistics
            color_stats = self._calculate_color_statistics(img_array)
            
            # Correlate colors with detected categories
            color_correlations = self._correlate_colors_with_categories(
                color_stats, categorized_elements
            )
            
            return {
                "dominant_colors": color_stats["dominant_colors"],
                "color_distribution": color_stats["color_distribution"],
                "vegetation_indicators": color_correlations["vegetation_indicators"],
                "sky_indicators": color_correlations["sky_indicators"],
                "water_indicators": color_correlations["water_indicators"],
                "overall_brightness": color_stats["brightness"],
                "color_diversity": color_stats["diversity_score"]
            }
            
        except Exception as e:
            logger.error(f"Color analysis for labels failed: {e}")
            return {"error": f"Color analysis failed: {str(e)}"}
    
    def _calculate_color_statistics(self, img_array: np.ndarray) -> Dict[str, Any]:
        """Calculate comprehensive color statistics from image"""
        # Calculate mean colors
        mean_colors = np.mean(img_array, axis=(0, 1))
        
        # Calculate color distribution
        color_hist = {
            "red_distribution": np.histogram(img_array[:, :, 0], bins=10, range=(0, 255))[0].tolist(),
            "green_distribution": np.histogram(img_array[:, :, 1], bins=10, range=(0, 255))[0].tolist(),
            "blue_distribution": np.histogram(img_array[:, :, 2], bins=10, range=(0, 255))[0].tolist()
        }
        
        # Calculate color ratios
        total_intensity = np.sum(mean_colors)
        color_ratios = mean_colors / total_intensity if total_intensity > 0 else np.array([0, 0, 0])
        
        # Calculate brightness and diversity
        brightness = float(np.mean(mean_colors))
        diversity_score = float(np.std(img_array.reshape(-1, 3), axis=0).mean())
        
        return {
            "dominant_colors": [
                {"red": float(mean_colors[0]), "green": float(mean_colors[1]), "blue": float(mean_colors[2])}
            ],
            "color_distribution": color_hist,
            "color_ratios": {
                "red_ratio": float(color_ratios[0]),
                "green_ratio": float(color_ratios[1]),
                "blue_ratio": float(color_ratios[2])
            },
            "brightness": brightness,
            "diversity_score": diversity_score
        }
    
    def _correlate_colors_with_categories(
        self, 
        color_stats: Dict[str, Any], 
        categorized_elements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Correlate color analysis with detected label categories"""
        correlations = {
            "vegetation_indicators": {},
            "sky_indicators": {},
            "water_indicators": {}
        }
        
        color_ratios = color_stats.get("color_ratios", {})
        green_ratio = color_ratios.get("green_ratio", 0)
        blue_ratio = color_ratios.get("blue_ratio", 0)
        brightness = color_stats.get("brightness", 0)
        
        # Vegetation indicators
        vegetation_labels = categorized_elements.get("vegetation", [])
        if vegetation_labels:
            correlations["vegetation_indicators"] = {
                "green_dominance": green_ratio,
                "vegetation_health_estimate": min(100, green_ratio * 150),  # Scale green ratio
                "label_confidence": sum(label.get("confidence", 0) for label in vegetation_labels) / len(vegetation_labels)
            }
        
        # Sky indicators
        sky_labels = categorized_elements.get("sky", [])
        if sky_labels:
            correlations["sky_indicators"] = {
                "blue_dominance": blue_ratio,
                "sky_clarity_estimate": min(100, (blue_ratio * brightness) / 2.55),  # Combine blue and brightness
                "label_confidence": sum(label.get("confidence", 0) for label in sky_labels) / len(sky_labels)
            }
        
        # Water indicators
        water_labels = categorized_elements.get("water", [])
        if water_labels:
            correlations["water_indicators"] = {
                "blue_presence": blue_ratio,
                "water_clarity_estimate": min(100, blue_ratio * 120),
                "label_confidence": sum(label.get("confidence", 0) for label in water_labels) / len(water_labels)
            }
        
        return correlations
    
    def _generate_natural_element_insights(
        self, 
        categorized_elements: Dict[str, Any], 
        coverage_stats: Dict[str, float]
    ) -> Dict[str, Any]:
        """Generate insights about natural elements based on analysis"""
        insights = {
            "dominant_natural_element": None,
            "biodiversity_indicators": [],
            "environmental_health_score": 0.0,
            "seasonal_indicators": [],
            "recommendations": []
        }
        
        # Find dominant natural element
        natural_categories = ["vegetation", "sky", "water", "terrain"]
        max_coverage = 0
        for category in natural_categories:
            coverage_key = f"{category}_coverage"
            coverage = coverage_stats.get(coverage_key, 0)
            if coverage > max_coverage:
                max_coverage = coverage
                insights["dominant_natural_element"] = category
        
        # Biodiversity indicators
        vegetation_labels = categorized_elements.get("vegetation", [])
        if vegetation_labels:
            unique_vegetation_types = len(set(label.get("name", "").lower() for label in vegetation_labels))
            insights["biodiversity_indicators"] = [
                f"Detected {unique_vegetation_types} different vegetation types",
                f"Vegetation coverage: {coverage_stats.get('vegetation_coverage', 0):.1f}%"
            ]
        
        # Environmental health score
        vegetation_coverage = coverage_stats.get("vegetation_coverage", 0)
        sky_coverage = coverage_stats.get("sky_coverage", 0)
        water_coverage = coverage_stats.get("water_coverage", 0)
        built_coverage = coverage_stats.get("built_environment_coverage", 0)
        
        # Simple health score calculation
        health_score = (
            vegetation_coverage * 0.4 +
            sky_coverage * 0.2 +
            water_coverage * 0.2 -
            built_coverage * 0.1
        )
        insights["environmental_health_score"] = max(0, min(100, health_score))
        
        # Seasonal indicators
        seasonal_keywords = {
            "spring": ["flower", "bloom", "bud", "fresh", "green"],
            "summer": ["lush", "dense", "bright", "sunny"],
            "autumn": ["fall", "orange", "yellow", "brown", "leaf"],
            "winter": ["bare", "snow", "frost", "dormant"]
        }
        
        all_labels = []
        for category_labels in categorized_elements.values():
            all_labels.extend([label.get("name", "").lower() for label in category_labels])
        
        for season, keywords in seasonal_keywords.items():
            if any(keyword in " ".join(all_labels) for keyword in keywords):
                insights["seasonal_indicators"].append(season)
        
        # Generate recommendations
        if vegetation_coverage < 20:
            insights["recommendations"].append("Consider adding more vegetation for better environmental balance")
        if built_coverage > 60:
            insights["recommendations"].append("High built environment coverage detected - consider green spaces")
        if len(vegetation_labels) < 3:
            insights["recommendations"].append("Limited vegetation diversity - consider diverse plantings")
        
        return insights
    
    def _analyze_label_confidence(self, labels: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze confidence distribution of labels"""
        if not labels:
            return {"error": "No labels to analyze"}
        
        confidences = [label.get("confidence", 0) for label in labels]
        
        # Categorize by confidence levels
        high_conf = [c for c in confidences if c >= self.confidence_thresholds["high_confidence"]]
        medium_conf = [c for c in confidences if self.confidence_thresholds["medium_confidence"] <= c < self.confidence_thresholds["high_confidence"]]
        low_conf = [c for c in confidences if c < self.confidence_thresholds["medium_confidence"]]
        
        return {
            "total_labels": len(labels),
            "confidence_distribution": {
                "high_confidence": len(high_conf),
                "medium_confidence": len(medium_conf),
                "low_confidence": len(low_conf)
            },
            "confidence_statistics": {
                "mean": sum(confidences) / len(confidences),
                "min": min(confidences),
                "max": max(confidences),
                "median": sorted(confidences)[len(confidences) // 2]
            },
            "reliability_score": len(high_conf) / len(labels) * 100 if labels else 0
        }
    
    def create_natural_elements_result(
        self,
        coverage_stats: Dict[str, float],
        color_analysis: Optional[Dict[str, Any]] = None,
        insights: Optional[Dict[str, Any]] = None
    ) -> NaturalElementsResult:
        """Create a structured NaturalElementsResult from analysis data"""
        
        # Extract dominant colors
        dominant_colors = []
        if color_analysis and "dominant_colors" in color_analysis:
            for color_data in color_analysis["dominant_colors"]:
                color_info = ColorInfo(
                    red=color_data.get("red", 0),
                    green=color_data.get("green", 0),
                    blue=color_data.get("blue", 0)
                )
                dominant_colors.append(color_info)
        
        # Extract seasonal indicators
        seasonal_indicators = []
        if insights and "seasonal_indicators" in insights:
            seasonal_indicators = insights["seasonal_indicators"]
        
        # Calculate vegetation health score
        vegetation_health_score = None
        if color_analysis and "vegetation_indicators" in color_analysis:
            vegetation_health_score = color_analysis["vegetation_indicators"].get("vegetation_health_estimate")
        elif insights:
            vegetation_health_score = insights.get("environmental_health_score")
        
        return NaturalElementsResult(
            vegetation_coverage=coverage_stats.get("vegetation_coverage", 0.0),
            sky_coverage=coverage_stats.get("sky_coverage", 0.0),
            water_coverage=coverage_stats.get("water_coverage", 0.0),
            built_environment_coverage=coverage_stats.get("built_environment_coverage", 0.0),
            vegetation_health_score=vegetation_health_score,
            dominant_colors=dominant_colors,
            seasonal_indicators=seasonal_indicators
        )

# Global label analysis service instance
label_analysis_service = LabelAnalysisService()