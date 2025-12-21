"""
Similarity Comparison Service
Compares two audio tracks for melody and harmony similarity.
Implements transposition search and segment-level analysis.
"""
import numpy as np
from typing import Dict, List, Tuple
from .melody_analyzer import MelodyAnalyzer
import librosa


class SimilarityComparator:
    """
    Compares two audio tracks to detect plagiarism or cover songs.
    """
    
    def __init__(self, sample_rate: int = 22050):
        """
        Initialize the SimilarityComparator.
        
        Args:
            sample_rate: Target sample rate for audio processing
        """
        self.sample_rate = sample_rate
        self.analyzer = MelodyAnalyzer(sample_rate=sample_rate)
        
    def load_and_extract_features(self, audio_path: str) -> Dict:
        """
        Load audio and extract all relevant features.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary of extracted features
        """
        return self.analyzer.extract_all_melody_features(audio_path)
    
    def compare_chroma_with_transposition(self, chroma1: np.ndarray, 
                                         chroma2: np.ndarray) -> Dict:
        """
        Compare two chroma sequences with optimal transposition.
        
        Args:
            chroma1: First chroma sequence (12 x n_frames)
            chroma2: Second chroma sequence (12 x n_frames)
            
        Returns:
            Dictionary with transposition info and similarity
        """
        # Find best transposition
        best_shift, best_similarity = self.analyzer.find_best_transposition(chroma1, chroma2)
        
        # Apply best transposition
        chroma2_aligned = self.analyzer.transpose_chroma(chroma2, best_shift)
        
        # Compute DTW with aligned chroma
        dtw_distance, cost_matrix, dtw_path = self.analyzer.compute_dtw_alignment(
            chroma1, chroma2_aligned, metric='cosine'
        )
        
        return {
            'best_transposition_semitones': int(best_shift),
            'similarity_score': float(best_similarity),
            'dtw_distance': float(dtw_distance),
            'cost_matrix': cost_matrix.tolist(),
            'dtw_path': dtw_path.tolist(),
            'chroma2_aligned': chroma2_aligned.tolist()
        }
    
    def compare_melody_contours(self, f0_1: np.ndarray, f0_2: np.ndarray,
                               voiced_1: np.ndarray, voiced_2: np.ndarray) -> Dict:
        """
        Compare two melody contours (F0 trajectories).
        
        Args:
            f0_1: First F0 contour
            f0_2: Second F0 contour
            voiced_1: Voiced flags for first track
            voiced_2: Voiced flags for second track
            
        Returns:
            Dictionary with melody similarity metrics
        """
        # Convert to MIDI for comparison (semitone-based)
        midi_1 = self.analyzer.convert_f0_to_midi(f0_1)
        midi_2 = self.analyzer.convert_f0_to_midi(f0_2)
        
        # Normalize to relative pitch (remove absolute pitch, keep intervals)
        def normalize_melody(midi, voiced):
            voiced_midi = midi[voiced]
            if len(voiced_midi) > 0:
                # Subtract median to get relative pitch
                median_pitch = np.median(voiced_midi)
                normalized = midi - median_pitch
                normalized[~voiced] = 0  # Keep silent frames as 0
                return normalized
            return midi
        
        midi_1_norm = normalize_melody(midi_1, voiced_1)
        midi_2_norm = normalize_melody(midi_2, voiced_2)
        
        # Reshape for DTW (add feature dimension)
        midi_1_features = midi_1_norm.reshape(1, -1)
        midi_2_features = midi_2_norm.reshape(1, -1)
        
        # Compute DTW on melody contours
        dtw_distance, cost_matrix, dtw_path = self.analyzer.compute_dtw_alignment(
            midi_1_features, midi_2_features, metric='euclidean'
        )
        
        # Calculate melody similarity (0-1 scale)
        melody_similarity = 1.0 / (1.0 + dtw_distance)
        
        return {
            'melody_similarity': float(melody_similarity),
            'melody_dtw_distance': float(dtw_distance),
            'melody_cost_matrix': cost_matrix.tolist(),
            'melody_dtw_path': dtw_path.tolist()
        }
    
    def find_similar_segments(self, cost_matrix: np.ndarray, 
                             hop_length: int, sample_rate: int,
                             window_frames: int = 50,
                             threshold: float = 0.7) -> List[Dict]:
        """
        Find locally similar segments between two tracks.
        
        Args:
            cost_matrix: DTW cost matrix
            hop_length: Hop length used in feature extraction
            sample_rate: Sample rate
            window_frames: Window size in frames
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of similar segments with time ranges
        """
        # Find local similar regions
        local_regions = self.analyzer.compute_local_alignment(cost_matrix, window_size=window_frames)
        
        # Convert frame indices to time
        for region in local_regions:
            # Track 1 times
            region['track1_start_time'] = librosa.frames_to_time(
                region['track1_start_frame'], sr=sample_rate, hop_length=hop_length
            )
            region['track1_end_time'] = librosa.frames_to_time(
                region['track1_end_frame'], sr=sample_rate, hop_length=hop_length
            )
            
            # Track 2 times
            region['track2_start_time'] = librosa.frames_to_time(
                region['track2_start_frame'], sr=sample_rate, hop_length=hop_length
            )
            region['track2_end_time'] = librosa.frames_to_time(
                region['track2_end_frame'], sr=sample_rate, hop_length=hop_length
            )
            
            # Convert to float for JSON serialization
            region['track1_start_time'] = float(region['track1_start_time'])
            region['track1_end_time'] = float(region['track1_end_time'])
            region['track2_start_time'] = float(region['track2_start_time'])
            region['track2_end_time'] = float(region['track2_end_time'])
        
        # Filter by threshold
        filtered_regions = [r for r in local_regions if r['similarity_score'] >= threshold]
        
        return filtered_regions
    
    def compute_overall_similarity(self, chroma_similarity: float,
                                   melody_similarity: float,
                                   tempo_ratio: float) -> Dict:
        """
        Compute overall similarity score from multiple metrics.
        
        Args:
            chroma_similarity: Harmony similarity (0-1)
            melody_similarity: Melody similarity (0-1)
            tempo_ratio: Ratio of tempos (should be close to 1 for similar songs)
            
        Returns:
            Dictionary with overall scores
        """
        # Weight different components
        CHROMA_WEIGHT = 0.5
        MELODY_WEIGHT = 0.4
        TEMPO_WEIGHT = 0.1
        
        # Tempo similarity (penalize large differences)
        tempo_similarity = 1.0 / (1.0 + abs(tempo_ratio - 1.0))
        
        # Weighted average
        overall_score = (
            CHROMA_WEIGHT * chroma_similarity +
            MELODY_WEIGHT * melody_similarity +
            TEMPO_WEIGHT * tempo_similarity
        )
        
        # Convert to percentage
        similarity_percentage = overall_score * 100
        
        # Determine similarity level
        if similarity_percentage >= 80:
            level = "Very High"
            verdict = "Highly similar - possible plagiarism or cover"
        elif similarity_percentage >= 60:
            level = "High"
            verdict = "Significant similarity detected"
        elif similarity_percentage >= 40:
            level = "Moderate"
            verdict = "Some similarities found"
        elif similarity_percentage >= 20:
            level = "Low"
            verdict = "Minor similarities only"
        else:
            level = "Very Low"
            verdict = "No significant similarity"
        
        return {
            'overall_similarity_score': float(overall_score),
            'similarity_percentage': float(similarity_percentage),
            'similarity_level': level,
            'verdict': verdict,
            'component_scores': {
                'chroma_harmony': float(chroma_similarity),
                'melody_contour': float(melody_similarity),
                'tempo': float(tempo_similarity)
            },
            'weights': {
                'chroma_harmony': CHROMA_WEIGHT,
                'melody_contour': MELODY_WEIGHT,
                'tempo': TEMPO_WEIGHT
            }
        }
    
    def compare_tracks(self, audio_path1: str, audio_path2: str,
                      track1_title: str = "Track 1",
                      track2_title: str = "Track 2") -> Dict:
        """
        Comprehensive comparison of two audio tracks.
        
        Args:
            audio_path1: Path to first audio file
            audio_path2: Path to second audio file
            track1_title: Title of first track
            track2_title: Title of second track
            
        Returns:
            Complete comparison results
        """
        print(f"Extracting features from {track1_title}...")
        features1 = self.load_and_extract_features(audio_path1)
        
        print(f"Extracting features from {track2_title}...")
        features2 = self.load_and_extract_features(audio_path2)
        
        # Convert lists back to numpy arrays for processing
        chroma1 = np.array(features1['chroma_cqt'])
        chroma2 = np.array(features2['chroma_cqt'])
        f0_1 = np.array(features1['f0_smoothed'])
        f0_2 = np.array(features2['f0_smoothed'])
        voiced_1 = np.array(features1['voiced_flag'])
        voiced_2 = np.array(features2['voiced_flag'])
        
        print("Comparing chroma features with transposition search...")
        chroma_result = self.compare_chroma_with_transposition(chroma1, chroma2)
        
        print("Comparing melody contours...")
        melody_result = self.compare_melody_contours(f0_1, f0_2, voiced_1, voiced_2)
        
        print("Finding similar segments...")
        similar_segments = self.find_similar_segments(
            np.array(chroma_result['cost_matrix']),
            self.analyzer.hop_length,
            self.sample_rate,
            window_frames=50,
            threshold=0.65
        )
        
        # Compute tempo ratio
        tempo_ratio = features1['tempo'] / features2['tempo'] if features2['tempo'] > 0 else 1.0
        
        print("Computing overall similarity...")
        overall_result = self.compute_overall_similarity(
            chroma_result['similarity_score'],
            melody_result['melody_similarity'],
            tempo_ratio
        )
        
        # Generate human-readable summary
        summary_text = self._generate_summary(
            track1_title, track2_title, overall_result, 
            chroma_result, features1, features2, similar_segments
        )
        
        return {
            'track1': {
                'title': track1_title,
                'duration': features1['duration'],
                'tempo': features1['tempo']
            },
            'track2': {
                'title': track2_title,
                'duration': features2['duration'],
                'tempo': features2['tempo']
            },
            'overall_similarity': overall_result,
            'chroma_analysis': {
                'transposition_semitones': chroma_result['best_transposition_semitones'],
                'similarity_score': chroma_result['similarity_score'],
                'dtw_distance': chroma_result['dtw_distance']
            },
            'melody_analysis': {
                'similarity_score': melody_result['melody_similarity'],
                'dtw_distance': melody_result['melody_dtw_distance']
            },
            'similar_segments': similar_segments,
            'tempo_analysis': {
                'track1_tempo': features1['tempo'],
                'track2_tempo': features2['tempo'],
                'tempo_ratio': float(tempo_ratio)
            },
            'summary': summary_text,
            'raw_data': {
                'chroma_cost_matrix': chroma_result['cost_matrix'],
                'chroma_dtw_path': chroma_result['dtw_path'],
                'melody_cost_matrix': melody_result['melody_cost_matrix'],
                'melody_dtw_path': melody_result['melody_dtw_path'],
                'features1': features1,
                'features2': features2
            }
        }
    
    def _generate_summary(self, track1_title: str, track2_title: str,
                         overall_result: Dict, chroma_result: Dict,
                         features1: Dict, features2: Dict,
                         similar_segments: List[Dict]) -> str:
        """
        Generate human-readable summary of comparison.
        
        Args:
            track1_title: Title of first track
            track2_title: Title of second track
            overall_result: Overall similarity results
            chroma_result: Chroma comparison results
            features1: Features of first track
            features2: Features of second track
            similar_segments: List of similar segments
            
        Returns:
            Summary text
        """
        lines = []
        lines.append(f"=== Similarity Analysis: {track1_title} vs {track2_title} ===\n")
        
        # Overall verdict
        lines.append(f"Overall Similarity: {overall_result['similarity_percentage']:.1f}%")
        lines.append(f"Level: {overall_result['similarity_level']}")
        lines.append(f"Verdict: {overall_result['verdict']}\n")
        
        # Component scores
        lines.append("Component Analysis:")
        lines.append(f"  - Harmony/Chroma: {overall_result['component_scores']['chroma_harmony']*100:.1f}%")
        lines.append(f"  - Melody Contour: {overall_result['component_scores']['melody_contour']*100:.1f}%")
        lines.append(f"  - Tempo Match: {overall_result['component_scores']['tempo']*100:.1f}%\n")
        
        # Key transposition
        semitones = chroma_result['best_transposition_semitones']
        if semitones == 0:
            lines.append("Key Analysis: Same key")
        else:
            direction = "up" if semitones > 0 else "down"
            lines.append(f"Key Analysis: Track 2 is {abs(semitones)} semitones {direction} from Track 1")
        
        # Tempo
        lines.append(f"Tempo: {features1['tempo']:.1f} BPM vs {features2['tempo']:.1f} BPM\n")
        
        # Similar segments
        if similar_segments:
            lines.append(f"Found {len(similar_segments)} similar segments:")
            for i, seg in enumerate(similar_segments[:5], 1):  # Show top 5
                lines.append(
                    f"  {i}. {track1_title} [{seg['track1_start_time']:.1f}s - {seg['track1_end_time']:.1f}s] "
                    f"↔ {track2_title} [{seg['track2_start_time']:.1f}s - {seg['track2_end_time']:.1f}s] "
                    f"(similarity: {seg['similarity_score']*100:.1f}%)"
                )
        else:
            lines.append("No highly similar segments found.")
        
        return "\n".join(lines)


def compare_audio_tracks(audio_path1: str, audio_path2: str,
                        track1_title: str = "Track 1",
                        track2_title: str = "Track 2",
                        sample_rate: int = 22050) -> Dict:
    """
    Convenience function to compare two audio tracks.
    
    Args:
        audio_path1: Path to first audio file
        audio_path2: Path to second audio file
        track1_title: Title of first track
        track2_title: Title of second track
        sample_rate: Target sample rate
        
    Returns:
        Comparison results dictionary
    """
    comparator = SimilarityComparator(sample_rate=sample_rate)
    return comparator.compare_tracks(audio_path1, audio_path2, track1_title, track2_title)
