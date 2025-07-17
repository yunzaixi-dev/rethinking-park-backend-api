import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from google.cloud import vision
from google.cloud.exceptions import GoogleCloudError
from PIL import Image

from models.image import (
    ColorInfo,
    NaturalElementCategory,
    NaturalElementsResult,
    SeasonalAnalysis,
    VegetationHealthMetrics,
)

logger = logging.getLogger(__name__)


class NaturalElementAnalyzer:
    """
    Service for analyzing natural elements in park images using Google Vision labels
    Provides label-based detection, vegetation health assessment, and coverage estimation
    """

    def __init__(self):
        self.natural_element_categories = {
            "vegetation": {
                "keywords": [
                    "tree",
                    "plant",
                    "grass",
                    "flower",
                    "leaf",
                    "vegetation",
                    "forest",
                    "garden",
                    "shrub",
                    "bush",
                    "fern",
                    "moss",
                    "vine",
                    "branch",
                    "trunk",
                    "foliage",
                    "greenery",
                    "flora",
                    "botanical",
                    "herb",
                    "weed",
                    "bamboo",
                ],
                "weight": 1.0,
            },
            "sky": {
                "keywords": [
                    "sky",
                    "cloud",
                    "atmosphere",
                    "horizon",
                    "sunset",
                    "sunrise",
                    "weather",
                    "blue sky",
                    "overcast",
                    "cumulus",
                    "cirrus",
                ],
                "weight": 0.8,
            },
            "water": {
                "keywords": [
                    "water",
                    "lake",
                    "river",
                    "pond",
                    "stream",
                    "fountain",
                    "pool",
                    "waterfall",
                    "creek",
                    "brook",
                    "canal",
                    "reservoir",
                    "wetland",
                ],
                "weight": 1.0,
            },
            "terrain": {
                "keywords": [
                    "ground",
                    "soil",
                    "rock",
                    "stone",
                    "path",
                    "trail",
                    "dirt",
                    "sand",
                    "gravel",
                    "pavement",
                    "earth",
                    "mud",
                    "cliff",
                    "hill",
                ],
                "weight": 0.6,
            },
            "built_environment": {
                "keywords": [
                    "building",
                    "structure",
                    "bench",
                    "fence",
                    "road",
                    "sidewalk",
                    "bridge",
                    "wall",
                    "gate",
                    "pavilion",
                    "gazebo",
                    "playground",
                    "statue",
                    "monument",
                    "sign",
                    "lamp",
                    "post",
                ],
                "weight": 0.7,
            },
        }

        # Seasonal indicators mapping
        self.seasonal_indicators = {
            "spring": ["bud", "bloom", "blossom", "fresh", "new growth", "sprout"],
            "summer": ["lush", "dense", "full", "vibrant", "bright green"],
            "autumn": [
                "fall",
                "yellow",
                "orange",
                "red leaves",
                "colorful",
                "changing",
            ],
            "winter": ["bare", "dormant", "snow", "frost", "leafless", "brown"],
        }

        # Vegetation health indicators
        self.health_indicators = {
            "healthy": ["green", "lush", "vibrant", "dense", "thriving"],
            "moderate": ["mixed", "partial", "some", "scattered"],
            "poor": ["brown", "dry", "sparse", "wilted", "dead", "bare"],
        }

    async def analyze_natural_elements(
        self,
        image_content: bytes,
        vision_client: vision.ImageAnnotatorClient,
        analysis_depth: str = "comprehensive",
    ) -> NaturalElementsResult:
        """
        Analyze natural elements in park images using Google Vision labels

        Args:
            image_content: Raw image bytes
            vision_client: Google Vision API client
            analysis_depth: "basic" or "comprehensive"

        Returns:
            NaturalElementsResult with coverage statistics and health assessment
        """
        start_time = datetime.now()

        try:
            # Get labels from Google Vision API
            image = vision.Image(content=image_content)
            labels_response = vision_client.label_detection(image=image)

            if labels_response.error.message:
                raise Exception(f"Vision API error: {labels_response.error.message}")

            # Convert labels to our format
            labels = [
                {
                    "name": label.description,
                    "confidence": float(label.score),
                    "topicality": float(label.topicality),
                }
                for label in labels_response.label_annotations
                if label.score >= 0.3  # Filter low confidence labels
            ]

            # Categorize natural elements
            categorized_elements = self._categorize_labels_by_natural_elements(labels)

            # Calculate coverage percentages
            coverage_stats = self._calculate_coverage_percentages(categorized_elements)

            # Analyze image colors for vegetation health
            color_analysis = self._analyze_image_colors(image_content)

            # Calculate vegetation health metrics
            vegetation_health_metrics = None
            vegetation_health_score = None
            if categorized_elements.get("vegetation"):
                vegetation_health_metrics = self._calculate_detailed_vegetation_health(
                    categorized_elements, color_analysis, labels
                )
                vegetation_health_score = vegetation_health_metrics.overall_score

            # Detect seasonal indicators and create seasonal analysis
            seasonal_indicators = []
            seasonal_analysis = None
            if analysis_depth == "comprehensive":
                seasonal_analysis = self._create_seasonal_analysis(labels)
                seasonal_indicators = seasonal_analysis.detected_seasons

            # Extract dominant colors with enhanced information
            dominant_colors = self._extract_enhanced_dominant_colors(color_analysis)

            # Calculate color diversity score
            color_diversity_score = self._calculate_color_diversity(color_analysis)

            # Create detailed element categories
            element_categories = self._create_element_categories(categorized_elements)

            # Generate overall assessment and recommendations
            overall_assessment = self._generate_overall_assessment(
                coverage_stats, vegetation_health_score
            )
            recommendations = self._generate_recommendations(
                coverage_stats, vegetation_health_score, seasonal_analysis
            )

            return NaturalElementsResult(
                # Basic coverage statistics
                vegetation_coverage=coverage_stats["vegetation_coverage"],
                sky_coverage=coverage_stats["sky_coverage"],
                water_coverage=coverage_stats["water_coverage"],
                built_environment_coverage=coverage_stats["built_environment_coverage"],
                # Enhanced vegetation health analysis
                vegetation_health_score=vegetation_health_score,
                vegetation_health_metrics=vegetation_health_metrics,
                # Color analysis
                dominant_colors=dominant_colors,
                color_diversity_score=color_diversity_score,
                # Seasonal analysis
                seasonal_indicators=seasonal_indicators,
                seasonal_analysis=seasonal_analysis,
                # Detailed category breakdown
                element_categories=element_categories,
                # Analysis metadata
                analysis_time=datetime.now(),
                analysis_depth=analysis_depth,
                total_labels_analyzed=len(labels),
                # Summary and recommendations
                overall_assessment=overall_assessment,
                recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"Natural elements analysis failed: {e}")
            # Return empty result on error
            return NaturalElementsResult(
                vegetation_coverage=0.0,
                sky_coverage=0.0,
                water_coverage=0.0,
                built_environment_coverage=0.0,
                vegetation_health_score=None,
                vegetation_health_metrics=None,
                dominant_colors=[],
                color_diversity_score=0.0,
                seasonal_indicators=[],
                seasonal_analysis=None,
                element_categories=[],
                analysis_time=datetime.now(),
                analysis_depth=analysis_depth,
                total_labels_analyzed=0,
                overall_assessment="error",
                recommendations=["Analysis failed - please try again"],
            )

    def _categorize_labels_by_natural_elements(
        self, labels: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorize Google Vision labels into natural element categories

        Args:
            labels: List of label detection results

        Returns:
            Dictionary with categorized labels
        """
        categorized = {
            category: [] for category in self.natural_element_categories.keys()
        }

        for label in labels:
            label_name = label["name"].lower()
            confidence = label["confidence"]

            # Check each category for keyword matches
            for category, config in self.natural_element_categories.items():
                keywords = config["keywords"]

                # Check if any keyword matches the label
                if any(keyword in label_name for keyword in keywords):
                    # Apply category weight to confidence
                    weighted_confidence = confidence * config["weight"]

                    categorized_label = {
                        **label,
                        "weighted_confidence": weighted_confidence,
                        "category_weight": config["weight"],
                    }
                    categorized[category].append(categorized_label)
                    break  # Only assign to first matching category

        return categorized

    def _calculate_coverage_percentages(
        self, categorized_elements: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, float]:
        """
        Calculate coverage percentages for each natural element category

        Args:
            categorized_elements: Categorized labels with confidence scores

        Returns:
            Dictionary with coverage percentages
        """
        coverage_stats = {
            "vegetation_coverage": 0.0,
            "sky_coverage": 0.0,
            "water_coverage": 0.0,
            "built_environment_coverage": 0.0,
        }

        # Calculate weighted confidence sums for each category
        category_scores = {}
        for category, labels in categorized_elements.items():
            if labels:
                # Sum weighted confidences, but cap individual contributions
                total_weighted_confidence = sum(
                    min(label["weighted_confidence"], 0.9) for label in labels
                )
                category_scores[category] = total_weighted_confidence
            else:
                category_scores[category] = 0.0

        # Map categories to coverage stats
        category_mapping = {
            "vegetation": "vegetation_coverage",
            "sky": "sky_coverage",
            "water": "water_coverage",
            "built_environment": "built_environment_coverage",
        }

        # Calculate total score for normalization
        total_score = sum(category_scores.values())

        if total_score > 0:
            # Normalize to percentages, but allow for realistic coverage
            for category, coverage_key in category_mapping.items():
                raw_percentage = (category_scores[category] / total_score) * 100
                # Apply realistic scaling - some elements naturally have higher coverage
                if category == "sky":
                    # Sky can dominate images
                    coverage_stats[coverage_key] = min(80.0, raw_percentage * 1.2)
                elif category == "vegetation":
                    # Vegetation is often prominent in park images
                    coverage_stats[coverage_key] = min(90.0, raw_percentage * 1.1)
                else:
                    coverage_stats[coverage_key] = min(60.0, raw_percentage)

        return coverage_stats

    def _analyze_image_colors(self, image_content: bytes) -> Dict[str, Any]:
        """
        Analyze dominant colors in the image for vegetation health assessment

        Args:
            image_content: Raw image bytes

        Returns:
            Dictionary with color analysis results
        """
        try:
            # Load and resize image for faster processing
            pil_image = Image.open(io.BytesIO(image_content))
            img_small = pil_image.resize((150, 150))
            img_array = np.array(img_small)

            # Handle different image formats
            if len(img_array.shape) == 2:  # Grayscale
                img_array = np.stack([img_array] * 3, axis=-1)
            elif img_array.shape[2] == 4:  # RGBA
                img_array = img_array[:, :, :3]  # Remove alpha channel

            # Calculate color statistics
            mean_colors = np.mean(img_array, axis=(0, 1))
            std_colors = np.std(img_array, axis=(0, 1))

            # Calculate color ratios for health assessment
            total_intensity = np.sum(mean_colors)
            if total_intensity > 0:
                green_ratio = mean_colors[1] / total_intensity
                red_ratio = mean_colors[0] / total_intensity
                blue_ratio = mean_colors[2] / total_intensity
            else:
                green_ratio = red_ratio = blue_ratio = 0.0

            # Calculate brightness and saturation indicators
            brightness = float(np.mean(mean_colors))
            color_variance = float(np.mean(std_colors))

            # Calculate vegetation-specific color metrics
            vegetation_green_threshold = (
                100  # Minimum green value for healthy vegetation
            )
            healthy_green_ratio = max(
                0.0, (mean_colors[1] - vegetation_green_threshold) / 155.0
            )

            return {
                "mean_colors": {
                    "red": float(mean_colors[0]),
                    "green": float(mean_colors[1]),
                    "blue": float(mean_colors[2]),
                },
                "color_ratios": {
                    "green_ratio": float(green_ratio),
                    "red_ratio": float(red_ratio),
                    "blue_ratio": float(blue_ratio),
                },
                "brightness": brightness,
                "color_variance": color_variance,
                "healthy_green_ratio": float(healthy_green_ratio),
            }

        except Exception as e:
            logger.error(f"Color analysis failed: {e}")
            return {
                "mean_colors": {"red": 0.0, "green": 0.0, "blue": 0.0},
                "color_ratios": {
                    "green_ratio": 0.0,
                    "red_ratio": 0.0,
                    "blue_ratio": 0.0,
                },
                "brightness": 0.0,
                "color_variance": 0.0,
                "healthy_green_ratio": 0.0,
            }

    def _calculate_vegetation_health_score(
        self,
        categorized_elements: Dict[str, List[Dict[str, Any]]],
        color_analysis: Dict[str, Any],
        labels: List[Dict[str, Any]],
    ) -> Optional[float]:
        """
        Calculate vegetation health score based on labels, coverage, and color analysis

        Args:
            categorized_elements: Categorized natural elements
            color_analysis: Color analysis results
            labels: Original labels for health indicator detection

        Returns:
            Health score (0-100) or None if no vegetation detected
        """
        try:
            vegetation_labels = categorized_elements.get("vegetation", [])

            if not vegetation_labels:
                return None

            # Factor 1: Vegetation coverage and confidence (40% weight)
            vegetation_confidence = np.mean(
                [label["confidence"] for label in vegetation_labels]
            )
            vegetation_count = len(vegetation_labels)
            coverage_score = min(
                100.0, (vegetation_confidence * 50) + (vegetation_count * 10)
            )

            # Factor 2: Color-based health assessment (35% weight)
            green_ratio = color_analysis["color_ratios"]["green_ratio"]
            healthy_green_ratio = color_analysis["healthy_green_ratio"]
            brightness = color_analysis["brightness"]

            # Healthy vegetation should have good green ratio and moderate brightness
            color_health = (
                (green_ratio * 40)  # Green dominance
                + (healthy_green_ratio * 35)  # Healthy green levels
                + (min(1.0, brightness / 150) * 25)  # Appropriate brightness
            )

            # Factor 3: Health indicators from labels (25% weight)
            health_indicator_score = self._assess_health_from_labels(labels)

            # Combine factors with weights
            final_score = (
                (coverage_score * 0.40)
                + (color_health * 0.35)
                + (health_indicator_score * 0.25)
            )

            # Ensure score is within valid range
            return max(0.0, min(100.0, final_score))

        except Exception as e:
            logger.error(f"Vegetation health calculation failed: {e}")
            return None

    def _assess_health_from_labels(self, labels: List[Dict[str, Any]]) -> float:
        """
        Assess vegetation health based on label keywords

        Args:
            labels: List of detected labels

        Returns:
            Health score based on label analysis (0-100)
        """
        health_score = 50.0  # Neutral baseline

        for label in labels:
            label_name = label["name"].lower()
            confidence = label["confidence"]

            # Check for health indicators
            for health_level, keywords in self.health_indicators.items():
                if any(keyword in label_name for keyword in keywords):
                    if health_level == "healthy":
                        health_score += confidence * 30
                    elif health_level == "moderate":
                        health_score += confidence * 10
                    elif health_level == "poor":
                        health_score -= confidence * 25
                    break

        return max(0.0, min(100.0, health_score))

    def _detect_seasonal_indicators(self, labels: List[Dict[str, Any]]) -> List[str]:
        """
        Detect seasonal indicators from labels

        Args:
            labels: List of detected labels

        Returns:
            List of detected seasonal indicators
        """
        detected_seasons = []
        season_scores = {season: 0.0 for season in self.seasonal_indicators.keys()}

        for label in labels:
            label_name = label["name"].lower()
            confidence = label["confidence"]

            # Check for seasonal keywords
            for season, keywords in self.seasonal_indicators.items():
                if any(keyword in label_name for keyword in keywords):
                    season_scores[season] += confidence

        # Return seasons with significant indicators
        for season, score in season_scores.items():
            if score >= 0.3:  # Threshold for seasonal detection
                detected_seasons.append(season)

        # If no specific season detected, try to infer from color analysis
        if not detected_seasons:
            # This could be enhanced with more sophisticated seasonal detection
            detected_seasons.append("unspecified")

        return detected_seasons

    def _extract_dominant_colors(
        self, color_analysis: Dict[str, Any]
    ) -> List[ColorInfo]:
        """
        Extract dominant colors from color analysis

        Args:
            color_analysis: Color analysis results

        Returns:
            List of ColorInfo objects representing dominant colors
        """
        try:
            mean_colors = color_analysis["mean_colors"]

            # Create primary color info
            dominant_color = ColorInfo(
                red=mean_colors["red"],
                green=mean_colors["green"],
                blue=mean_colors["blue"],
                hex_code=self._rgb_to_hex(
                    int(mean_colors["red"]),
                    int(mean_colors["green"]),
                    int(mean_colors["blue"]),
                ),
            )

            return [dominant_color]

        except Exception as e:
            logger.error(f"Dominant color extraction failed: {e}")
            return []

    def _rgb_to_hex(self, r: int, g: int, b: int) -> str:
        """Convert RGB values to hex color code"""
        return f"#{r:02x}{g:02x}{b:02x}"

    def _calculate_detailed_vegetation_health(
        self,
        categorized_elements: Dict[str, List[Dict[str, Any]]],
        color_analysis: Dict[str, Any],
        labels: List[Dict[str, Any]],
    ) -> VegetationHealthMetrics:
        """
        Calculate detailed vegetation health metrics

        Args:
            categorized_elements: Categorized natural elements
            color_analysis: Color analysis results
            labels: Original labels for health indicator detection

        Returns:
            VegetationHealthMetrics with detailed health assessment
        """
        try:
            vegetation_labels = categorized_elements.get("vegetation", [])

            # Calculate individual health scores
            coverage_health_score = self._calculate_coverage_health_score(
                vegetation_labels
            )
            color_health_score = self._calculate_color_health_score(color_analysis)
            label_health_score = self._assess_health_from_labels(labels)

            # Calculate overall score with weights
            overall_score = (
                (coverage_health_score * 0.40)
                + (color_health_score * 0.35)
                + (label_health_score * 0.25)
            )

            # Determine health status
            if overall_score >= 75:
                health_status = "healthy"
            elif overall_score >= 50:
                health_status = "moderate"
            elif overall_score >= 25:
                health_status = "poor"
            else:
                health_status = "unknown"

            # Generate recommendations
            recommendations = self._generate_health_recommendations(
                overall_score,
                coverage_health_score,
                color_health_score,
                label_health_score,
            )

            return VegetationHealthMetrics(
                overall_score=max(0.0, min(100.0, overall_score)),
                color_health_score=max(0.0, min(100.0, color_health_score)),
                coverage_health_score=max(0.0, min(100.0, coverage_health_score)),
                label_health_score=max(0.0, min(100.0, label_health_score)),
                green_ratio=color_analysis["color_ratios"]["green_ratio"],
                health_status=health_status,
                recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"Detailed vegetation health calculation failed: {e}")
            return VegetationHealthMetrics(
                overall_score=0.0,
                color_health_score=0.0,
                coverage_health_score=0.0,
                label_health_score=0.0,
                green_ratio=0.0,
                health_status="unknown",
                recommendations=["Health assessment failed"],
            )

    def _calculate_coverage_health_score(
        self, vegetation_labels: List[Dict[str, Any]]
    ) -> float:
        """Calculate health score based on vegetation coverage and confidence"""
        if not vegetation_labels:
            return 0.0

        # Factor in both confidence and count of vegetation labels
        avg_confidence = np.mean([label["confidence"] for label in vegetation_labels])
        label_count = len(vegetation_labels)

        # Higher confidence and more diverse vegetation labels = better health
        coverage_score = (avg_confidence * 60) + min(40, label_count * 8)
        return max(0.0, min(100.0, coverage_score))

    def _calculate_color_health_score(self, color_analysis: Dict[str, Any]) -> float:
        """Calculate health score based on color analysis"""
        green_ratio = color_analysis["color_ratios"]["green_ratio"]
        healthy_green_ratio = color_analysis["healthy_green_ratio"]
        brightness = color_analysis["brightness"]

        # Optimal green ratio for healthy vegetation
        green_score = green_ratio * 40

        # Healthy green levels (above threshold)
        healthy_green_score = healthy_green_ratio * 35

        # Appropriate brightness (not too dark, not too bright)
        optimal_brightness = 120  # Target brightness for healthy vegetation
        brightness_score = max(0, 25 - abs(brightness - optimal_brightness) / 5)

        total_score = green_score + healthy_green_score + brightness_score
        return max(0.0, min(100.0, total_score))

    def _generate_health_recommendations(
        self,
        overall_score: float,
        coverage_score: float,
        color_score: float,
        label_score: float,
    ) -> List[str]:
        """Generate health improvement recommendations"""
        recommendations = []

        if overall_score < 50:
            recommendations.append("Vegetation health appears to need attention")

        if coverage_score < 40:
            recommendations.append(
                "Low vegetation coverage detected - consider increasing plant density"
            )

        if color_score < 40:
            recommendations.append(
                "Color analysis suggests vegetation may be stressed - check watering and nutrients"
            )

        if label_score < 40:
            recommendations.append("Labels indicate potential vegetation health issues")

        if overall_score >= 75:
            recommendations.append("Vegetation appears healthy and thriving")

        return recommendations

    def _create_seasonal_analysis(
        self, labels: List[Dict[str, Any]]
    ) -> SeasonalAnalysis:
        """
        Create comprehensive seasonal analysis from labels

        Args:
            labels: List of detected labels

        Returns:
            SeasonalAnalysis with detailed seasonal information
        """
        try:
            season_scores = {season: 0.0 for season in self.seasonal_indicators.keys()}
            seasonal_features = []

            # Analyze labels for seasonal indicators
            for label in labels:
                label_name = label["name"].lower()
                confidence = label["confidence"]

                # Check for seasonal keywords
                for season, keywords in self.seasonal_indicators.items():
                    for keyword in keywords:
                        if keyword in label_name:
                            season_scores[season] += confidence
                            seasonal_features.append(f"{season}: {label_name}")
                            break

            # Determine detected seasons (threshold-based)
            detected_seasons = [
                season for season, score in season_scores.items() if score >= 0.3
            ]

            # Determine primary season
            primary_season = None
            if season_scores:
                max_season = max(season_scores.items(), key=lambda x: x[1])
                if max_season[1] >= 0.3:
                    primary_season = max_season[0]

            # If no clear seasonal indicators, add generic seasonal features
            if not seasonal_features:
                seasonal_features = ["General outdoor environment"]

            return SeasonalAnalysis(
                detected_seasons=detected_seasons,
                confidence_scores=season_scores,
                primary_season=primary_season,
                seasonal_features=list(set(seasonal_features)),  # Remove duplicates
            )

        except Exception as e:
            logger.error(f"Seasonal analysis failed: {e}")
            return SeasonalAnalysis(
                detected_seasons=[],
                confidence_scores={},
                primary_season=None,
                seasonal_features=[],
            )

    def _extract_enhanced_dominant_colors(
        self, color_analysis: Dict[str, Any]
    ) -> List[ColorInfo]:
        """
        Extract enhanced dominant colors with additional information

        Args:
            color_analysis: Color analysis results

        Returns:
            List of enhanced ColorInfo objects
        """
        try:
            mean_colors = color_analysis["mean_colors"]
            color_ratios = color_analysis["color_ratios"]

            # Create enhanced color info with percentages and names
            colors = []

            # Primary dominant color
            dominant_color = ColorInfo(
                red=mean_colors["red"],
                green=mean_colors["green"],
                blue=mean_colors["blue"],
                hex_code=self._rgb_to_hex(
                    int(mean_colors["red"]),
                    int(mean_colors["green"]),
                    int(mean_colors["blue"]),
                ),
                color_name=self._get_color_name(mean_colors),
                percentage=100.0,  # Primary color gets 100%
            )
            colors.append(dominant_color)

            # Add secondary colors based on ratios if they're significant
            if color_ratios["green_ratio"] > 0.4:
                green_color = ColorInfo(
                    red=0.0,
                    green=255.0,
                    blue=0.0,
                    hex_code="#00FF00",
                    color_name="Green (Vegetation)",
                    percentage=color_ratios["green_ratio"] * 100,
                )
                colors.append(green_color)

            return colors

        except Exception as e:
            logger.error(f"Enhanced dominant color extraction failed: {e}")
            return []

    def _get_color_name(self, mean_colors: Dict[str, float]) -> str:
        """Get a descriptive name for the dominant color"""
        r, g, b = mean_colors["red"], mean_colors["green"], mean_colors["blue"]

        # Simple color naming based on dominant channel
        if g > r and g > b:
            if g > 150:
                return "Bright Green"
            elif g > 100:
                return "Green"
            else:
                return "Dark Green"
        elif r > g and r > b:
            if r > 150:
                return "Bright Red"
            elif r > 100:
                return "Red"
            else:
                return "Dark Red"
        elif b > r and b > g:
            if b > 150:
                return "Bright Blue"
            elif b > 100:
                return "Blue"
            else:
                return "Dark Blue"
        else:
            # Mixed colors
            brightness = (r + g + b) / 3
            if brightness > 200:
                return "Light"
            elif brightness > 100:
                return "Medium"
            else:
                return "Dark"

    def _calculate_color_diversity(self, color_analysis: Dict[str, Any]) -> float:
        """
        Calculate color diversity score based on color variance

        Args:
            color_analysis: Color analysis results

        Returns:
            Color diversity score (0-100)
        """
        try:
            color_variance = color_analysis.get("color_variance", 0.0)

            # Higher variance indicates more color diversity
            # Normalize variance to 0-100 scale
            diversity_score = min(100.0, (color_variance / 50.0) * 100)

            return max(0.0, diversity_score)

        except Exception as e:
            logger.error(f"Color diversity calculation failed: {e}")
            return 0.0

    def _create_element_categories(
        self, categorized_elements: Dict[str, List[Dict[str, Any]]]
    ) -> List[NaturalElementCategory]:
        """
        Create detailed element category breakdown

        Args:
            categorized_elements: Categorized natural elements

        Returns:
            List of NaturalElementCategory objects
        """
        categories = []

        try:
            for category_name, labels in categorized_elements.items():
                if labels:  # Only include categories with detected elements
                    # Calculate average confidence
                    avg_confidence = np.mean([label["confidence"] for label in labels])

                    # Calculate coverage percentage (simplified)
                    total_weighted_confidence = sum(
                        label["weighted_confidence"] for label in labels
                    )
                    coverage_percentage = min(
                        100.0, total_weighted_confidence * 50
                    )  # Scale to percentage

                    # Extract label names
                    detected_labels = [label["name"] for label in labels]

                    category = NaturalElementCategory(
                        category_name=category_name.replace("_", " ").title(),
                        coverage_percentage=coverage_percentage,
                        confidence_score=avg_confidence,
                        detected_labels=detected_labels,
                        element_count=len(labels),
                    )
                    categories.append(category)

            return categories

        except Exception as e:
            logger.error(f"Element category creation failed: {e}")
            return []

    def _generate_overall_assessment(
        self, coverage_stats: Dict[str, float], vegetation_health_score: Optional[float]
    ) -> str:
        """Generate overall assessment of the natural environment"""
        vegetation_coverage = coverage_stats["vegetation_coverage"]
        built_coverage = coverage_stats["built_environment_coverage"]
        water_coverage = coverage_stats["water_coverage"]

        if vegetation_coverage > 60:
            if vegetation_health_score and vegetation_health_score > 75:
                return "thriving_natural_environment"
            else:
                return "nature_dominant"
        elif vegetation_coverage > 30:
            if water_coverage > 20:
                return "balanced_environment_with_water"
            else:
                return "balanced_environment"
        elif built_coverage > 50:
            return "urban_environment"
        elif water_coverage > 40:
            return "water_dominant_environment"
        else:
            return "mixed_landscape"

    def _generate_recommendations(
        self,
        coverage_stats: Dict[str, float],
        vegetation_health_score: Optional[float],
        seasonal_analysis: Optional[SeasonalAnalysis],
    ) -> List[str]:
        """Generate recommendations based on analysis results"""
        recommendations = []

        vegetation_coverage = coverage_stats["vegetation_coverage"]

        # Vegetation-based recommendations
        if vegetation_coverage < 20:
            recommendations.append(
                "Consider increasing vegetation coverage for better environmental balance"
            )
        elif vegetation_coverage > 80:
            recommendations.append(
                "Excellent vegetation coverage - maintain current green space management"
            )

        # Health-based recommendations
        if vegetation_health_score:
            if vegetation_health_score < 50:
                recommendations.append(
                    "Vegetation health needs attention - consider soil and water management"
                )
            elif vegetation_health_score > 80:
                recommendations.append(
                    "Vegetation appears very healthy - continue current maintenance practices"
                )

        # Water feature recommendations
        if coverage_stats["water_coverage"] > 30:
            recommendations.append(
                "Significant water features detected - monitor water quality and ecosystem health"
            )

        # Seasonal recommendations
        if seasonal_analysis and seasonal_analysis.primary_season:
            season = seasonal_analysis.primary_season
            if season == "winter":
                recommendations.append(
                    "Winter conditions detected - consider seasonal maintenance needs"
                )
            elif season == "spring":
                recommendations.append(
                    "Spring growth period - optimal time for planting and maintenance"
                )
            elif season == "summer":
                recommendations.append(
                    "Summer conditions - ensure adequate watering and shade"
                )
            elif season == "autumn":
                recommendations.append(
                    "Autumn season - prepare for seasonal changes and leaf management"
                )

        # Built environment balance
        if coverage_stats["built_environment_coverage"] > 60:
            recommendations.append(
                "High built environment coverage - consider adding more green spaces"
            )

        return recommendations

    def get_analysis_summary(self, result: NaturalElementsResult) -> Dict[str, Any]:
        """
        Generate a human-readable summary of the natural elements analysis

        Args:
            result: NaturalElementsResult object

        Returns:
            Dictionary with analysis summary
        """
        summary = {
            "overall_assessment": "unknown",
            "dominant_elements": [],
            "vegetation_status": "unknown",
            "recommendations": [],
        }

        try:
            # Determine dominant elements
            coverage_data = [
                ("vegetation", result.vegetation_coverage),
                ("sky", result.sky_coverage),
                ("water", result.water_coverage),
                ("built_environment", result.built_environment_coverage),
            ]

            # Sort by coverage percentage
            sorted_coverage = sorted(coverage_data, key=lambda x: x[1], reverse=True)
            summary["dominant_elements"] = [
                {"element": element, "coverage": coverage}
                for element, coverage in sorted_coverage
                if coverage > 5.0  # Only include significant elements
            ]

            # Overall assessment
            vegetation_coverage = result.vegetation_coverage
            if vegetation_coverage > 60:
                summary["overall_assessment"] = "nature_dominant"
            elif vegetation_coverage > 30:
                summary["overall_assessment"] = "balanced_environment"
            elif result.built_environment_coverage > 50:
                summary["overall_assessment"] = "urban_environment"
            else:
                summary["overall_assessment"] = "mixed_landscape"

            # Vegetation status
            if result.vegetation_health_score is not None:
                if result.vegetation_health_score >= 75:
                    summary["vegetation_status"] = "healthy"
                elif result.vegetation_health_score >= 50:
                    summary["vegetation_status"] = "moderate"
                else:
                    summary["vegetation_status"] = "needs_attention"

            # Generate recommendations
            if result.vegetation_health_score and result.vegetation_health_score < 60:
                summary["recommendations"].append(
                    "Consider vegetation health assessment"
                )

            if result.vegetation_coverage < 20:
                summary["recommendations"].append("Low vegetation coverage detected")

            if result.water_coverage > 20:
                summary["recommendations"].append("Significant water features present")

        except Exception as e:
            logger.error(f"Analysis summary generation failed: {e}")

        return summary


# Global natural element analyzer instance
natural_element_analyzer = NaturalElementAnalyzer()
