"""
Lightweight Visualization Generation Service
Creates simple visualizations without matplotlib/seaborn to reduce image size.
Uses Pillow for basic image generation.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Optional, Tuple
import io
import base64


class VisualizationGenerator:
    """
    Lightweight visualization generator using Pillow instead of matplotlib.
    """
    
    def __init__(self, dpi: int = 100, figsize: Tuple[int, int] = (12, 8)):
        """
        Initialize the VisualizationGenerator.
        
        Args:
            dpi: Resolution of output images (unused, kept for compatibility)
            figsize: Figure size in inches (width, height)
        """
        self.width = figsize[0] * 100  # Convert to pixels
        self.height = figsize[1] * 100
        
    def generate_all_visualizations(self, comparison_result: Dict,
                                   output_dir: Optional[str] = None) -> Dict[str, Dict]:
        """
        Generate simplified visualizations for a comparison result.
        
        Args:
            comparison_result: Dictionary containing comparison results
            output_dir: Optional directory to save images (not used)
            
        Returns:
            Dictionary mapping visualization names to their data
        """
        visualizations = {}
        
        # Create a simple summary visualization
        try:
            summary_img = self._create_summary_image(comparison_result)
            visualizations['summary_dashboard'] = {
                'bytes': summary_img,
                'format': 'png'
            }
        except Exception as e:
            print(f"Warning: Could not generate summary visualization: {e}")
        
        return visualizations
    
    def _create_summary_image(self, comparison_result: Dict) -> bytes:
        """
        Create a simple summary image with key metrics.
        """
        # Create image
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to load a font, fallback to default
        try:
            title_font = ImageFont.truetype("arial.ttf", 24)
            text_font = ImageFont.truetype("arial.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
        
        # Draw title
        title = "Music Similarity Analysis"
        draw.text((20, 20), title, fill='black', font=title_font)
        
        # Extract and draw key metrics
        overall = comparison_result.get('overall_similarity', {})
        similarity_pct = overall.get('similarity_percentage', 0)
        level = overall.get('similarity_level', 'Unknown')
        verdict = overall.get('verdict', 'No data')
        
        y_pos = 80
        metrics = [
            f"Overall Similarity: {similarity_pct:.1f}%",
            f"Level: {level}",
            f"Verdict: {verdict}",
            "",
            "Component Scores:",
        ]
        
        for metric in metrics:
            draw.text((20, y_pos), metric, fill='black', font=text_font)
            y_pos += 30
        
        # Component scores
        components = overall.get('component_scores', {})
        for key, value in components.items():
            text = f"  - {key.replace('_', ' ').title()}: {value*100:.1f}%"
            draw.text((20, y_pos), text, fill='navy', font=text_font)
            y_pos += 25
        
        # Add tempo info
        tempo_analysis = comparison_result.get('tempo_analysis', {})
        if tempo_analysis:
            y_pos += 20
            draw.text((20, y_pos), "Tempo Analysis:", fill='black', font=text_font)
            y_pos += 25
            t1 = tempo_analysis.get('track1_tempo', 0)
            t2 = tempo_analysis.get('track2_tempo', 0)
            draw.text((20, y_pos), f"  Track 1: {t1:.1f} BPM", fill='navy', font=text_font)
            y_pos += 25
            draw.text((20, y_pos), f"  Track 2: {t2:.1f} BPM", fill='navy', font=text_font)
        
        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()
        buffer.close()
        
        return img_bytes


# Maintain backward compatibility
def generate_visualizations(comparison_result: Dict) -> Dict[str, Dict]:
    """
    Convenience function to generate visualizations.
    """
    generator = VisualizationGenerator()
    return generator.generate_all_visualizations(comparison_result)
