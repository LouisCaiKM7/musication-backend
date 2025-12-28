"""
Melody and Harmony Analysis Service
Extracts melody contours, HPCP features, and performs DTW-based similarity analysis.
This module implements cover song identification techniques.
"""
import numpy as np
import librosa
import librosa.display
from typing import Dict, Tuple, Optional, List
from scipy.spatial.distance import cdist
from scipy.ndimage import median_filter
import warnings

warnings.filterwarnings('ignore')


class MelodyAnalyzer:
    """
    Advanced melody and harmony analyzer for plagiarism detection.
    Implements techniques from music information retrieval research.
    """
    
    def __init__(self, sample_rate: int = 22050, hop_length: int = 512, enable_melody: bool = True):
        """
        Initialize the MelodyAnalyzer.
        
        Args:
            sample_rate: Target sample rate for audio processing
            hop_length: Number of samples between successive frames
            enable_melody: Whether to enable CREPE melody analysis (memory intensive)
        """
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.n_fft = 2048
        self.enable_melody = enable_melody
        
    def load_audio(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """
        Load audio file and convert to mono at target sample rate.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple of (audio_data, sample_rate)
        """
        y, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)
        return y, sr
    
    def extract_hpcp(self, y: np.ndarray, sr: int, n_bins: int = 36) -> np.ndarray:
        """
        Extract Harmonic Pitch Class Profile (HPCP) features.
        HPCP is a refined version of chroma that better captures harmonic content.
        Uses higher resolution (36 bins = 3 bins per semitone).
        
        Args:
            y: Audio time series
            sr: Sample rate
            n_bins: Number of bins per octave (default 36 for 3 bins/semitone)
            
        Returns:
            HPCP features (n_bins x time_frames)
        """
        # Use CQT (Constant-Q Transform) for better pitch resolution
        C = np.abs(librosa.cqt(
            y=y,
            sr=sr,
            hop_length=self.hop_length,
            n_bins=n_bins * 7,  # 7 octaves
            bins_per_octave=n_bins
        ))
        
        # Fold to single octave (pitch class)
        hpcp = librosa.feature.chroma_cqt(
            C=C,
            sr=sr,
            hop_length=self.hop_length,
            n_chroma=n_bins,
            bins_per_octave=n_bins
        )
        
        return hpcp
    
    def extract_chroma_cqt(self, y: np.ndarray, sr: int) -> np.ndarray:
        """
        Extract standard 12-bin chroma features using CQT.
        More robust than STFT-based chroma for pitch tracking.
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Chroma features (12 x time_frames)
        """
        chroma = librosa.feature.chroma_cqt(
            y=y,
            sr=sr,
            hop_length=self.hop_length
        )
        return chroma
    
    def extract_melody_contour(self, y: np.ndarray, sr: int, 
                               method: str = 'pyin') -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract melody (F0) contour from audio.
        
        Args:
            y: Audio time series
            sr: Sample rate
            method: Method to use ('pyin' or 'piptrack')
            
        Returns:
            Tuple of (f0_hz, voiced_flag) where f0_hz is fundamental frequency
            and voiced_flag indicates voiced/unvoiced frames
        """
        if method == 'pyin':
            # pYIN is more robust for melody extraction
            f0, voiced_flag, voiced_probs = librosa.pyin(
                y,
                fmin=librosa.note_to_hz('C2'),  # ~65 Hz
                fmax=librosa.note_to_hz('C7'),  # ~2093 Hz
                sr=sr,
                hop_length=self.hop_length
            )
            # Replace NaN with 0 for unvoiced frames
            f0 = np.nan_to_num(f0, nan=0.0)
            return f0, voiced_flag
        
        else:  # piptrack fallback
            pitches, magnitudes = librosa.piptrack(
                y=y,
                sr=sr,
                hop_length=self.hop_length,
                fmin=librosa.note_to_hz('C2'),
                fmax=librosa.note_to_hz('C7')
            )
            
            # Select pitch with highest magnitude in each frame
            f0 = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                f0.append(pitch)
            
            f0 = np.array(f0)
            voiced_flag = f0 > 0
            return f0, voiced_flag
    
    def convert_f0_to_midi(self, f0_hz: np.ndarray) -> np.ndarray:
        """
        Convert F0 in Hz to MIDI note numbers.
        
        Args:
            f0_hz: Fundamental frequency in Hz
            
        Returns:
            MIDI note numbers
        """
        # Avoid log of zero
        f0_hz = np.maximum(f0_hz, 1e-10)
        midi = librosa.hz_to_midi(f0_hz)
        # Set silent frames to 0
        midi[f0_hz < 50] = 0
        return midi
    
    def smooth_melody(self, f0: np.ndarray, window_size: int = 5) -> np.ndarray:
        """
        Smooth melody contour using median filter to remove octave errors.
        
        Args:
            f0: Fundamental frequency contour
            window_size: Median filter window size
            
        Returns:
            Smoothed F0 contour
        """
        # Only smooth voiced regions
        voiced_mask = f0 > 0
        f0_smoothed = f0.copy()
        
        if np.sum(voiced_mask) > window_size:
            f0_voiced = f0[voiced_mask]
            f0_voiced_smoothed = median_filter(f0_voiced, size=window_size)
            f0_smoothed[voiced_mask] = f0_voiced_smoothed
        
        return f0_smoothed
    
    def beat_synchronize_features(self, features: np.ndarray, y: np.ndarray, 
                                  sr: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Synchronize features to beat positions for tempo-invariant comparison.
        
        Args:
            features: Time-varying features (n_features x n_frames)
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Tuple of (beat_sync_features, beat_times)
        """
        # Detect beats
        tempo, beat_frames = librosa.beat.beat_track(
            y=y,
            sr=sr,
            hop_length=self.hop_length
        )
        
        # Aggregate features at beat positions
        beat_features = librosa.util.sync(features, beat_frames, aggregate=np.median)
        
        # Convert beat frames to time
        beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=self.hop_length)
        
        return beat_features, beat_times
    
    def compute_dtw_alignment(self, features1: np.ndarray, features2: np.ndarray,
                             metric: str = 'cosine') -> Tuple[float, np.ndarray, np.ndarray]:
        """
        Compute Dynamic Time Warping alignment between two feature sequences.
        
        Args:
            features1: First feature sequence (n_features x n_frames1)
            features2: Second feature sequence (n_features x n_frames2)
            metric: Distance metric ('cosine', 'euclidean', etc.)
            
        Returns:
            Tuple of (dtw_distance, cost_matrix, alignment_path)
            where alignment_path is list of (i, j) frame alignments
        """
        # Transpose to (n_frames x n_features) for distance computation
        X = features1.T
        Y = features2.T
        
        # Compute frame-to-frame distance matrix
        C = cdist(X, Y, metric=metric)
        
        # Compute DTW
        D, wp = librosa.sequence.dtw(C=C, backtrack=True)
        
        # DTW distance (normalized)
        dtw_distance = D[-1, -1] / (len(wp))
        
        return dtw_distance, C, wp
    
    def compute_local_alignment(self, C: np.ndarray, 
                               window_size: int = 50) -> List[Dict]:
        """
        Find locally similar regions in the cost matrix.
        
        Args:
            C: Cost matrix from DTW
            window_size: Size of sliding window for local similarity
            
        Returns:
            List of dictionaries with local alignment regions
        """
        # Invert cost to similarity (lower cost = higher similarity)
        similarity = 1.0 / (1.0 + C)
        
        # Find local maxima
        local_regions = []
        
        n_frames1, n_frames2 = similarity.shape
        stride = window_size // 2
        
        for i in range(0, n_frames1 - window_size, stride):
            for j in range(0, n_frames2 - window_size, stride):
                window = similarity[i:i+window_size, j:j+window_size]
                mean_sim = np.mean(window)
                max_sim = np.max(window)
                
                if mean_sim > 0.7:  # Threshold for similarity
                    local_regions.append({
                        'track1_start_frame': i,
                        'track1_end_frame': i + window_size,
                        'track2_start_frame': j,
                        'track2_end_frame': j + window_size,
                        'similarity_score': float(mean_sim),
                        'max_similarity': float(max_sim)
                    })
        
        # Sort by similarity score
        local_regions = sorted(local_regions, key=lambda x: x['similarity_score'], reverse=True)
        
        return local_regions
    
    def transpose_chroma(self, chroma: np.ndarray, semitones: int) -> np.ndarray:
        """
        Transpose chroma features by a given number of semitones.
        Used for key-invariant comparison.
        
        Args:
            chroma: Chroma features (12 x n_frames)
            semitones: Number of semitones to transpose (-11 to +11)
            
        Returns:
            Transposed chroma features
        """
        # Circular shift along pitch class dimension
        return np.roll(chroma, semitones, axis=0)
    
    def find_best_transposition(self, chroma1: np.ndarray, 
                               chroma2: np.ndarray) -> Tuple[int, float]:
        """
        Find the best transposition between two chroma sequences.
        Tests all 12 possible transpositions.
        
        Args:
            chroma1: First chroma sequence (12 x n_frames)
            chroma2: Second chroma sequence (12 x n_frames)
            
        Returns:
            Tuple of (best_semitones, best_similarity)
        """
        best_semitones = 0
        best_similarity = -np.inf
        
        for shift in range(12):
            chroma2_shifted = self.transpose_chroma(chroma2, shift)
            
            # Compute DTW distance
            distance, _, _ = self.compute_dtw_alignment(chroma1, chroma2_shifted, metric='cosine')
            
            # Convert to similarity (lower distance = higher similarity)
            similarity = 1.0 / (1.0 + distance)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_semitones = shift
        
        return best_semitones, best_similarity
    
    def extract_all_melody_features(self, audio_path: str) -> Dict:
        """
        Extract comprehensive melody and harmony features from audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary containing all melody/harmony features
        """
        # Load audio
        y, sr = self.load_audio(audio_path)
        
        # Extract features
        chroma_cqt = self.extract_chroma_cqt(y, sr)
        hpcp = self.extract_hpcp(y, sr)
        
        # Only extract melody if enabled (memory intensive)
        if self.enable_melody:
            f0, voiced_flag = self.extract_melody_contour(y, sr, method='pyin')
            f0_smoothed = self.smooth_melody(f0)
            midi_notes = self.convert_f0_to_midi(f0_smoothed)
        else:
            # Placeholder values when melody analysis is disabled
            n_frames = chroma_cqt.shape[1]
            f0 = np.zeros(n_frames)
            f0_smoothed = np.zeros(n_frames)
            midi_notes = np.zeros(n_frames)
            voiced_flag = np.zeros(n_frames, dtype=bool)
        
        # Beat synchronization
        chroma_sync, beat_times = self.beat_synchronize_features(chroma_cqt, y, sr)
        
        # Get tempo
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=self.hop_length)
        if isinstance(tempo, np.ndarray):
            tempo = float(tempo)
        
        return {
            'chroma_cqt': chroma_cqt.tolist(),
            'chroma_beat_sync': chroma_sync.tolist(),
            'hpcp': hpcp.tolist(),
            'f0_contour': f0.tolist(),
            'f0_smoothed': f0_smoothed.tolist(),
            'midi_notes': midi_notes.tolist(),
            'voiced_flag': voiced_flag.tolist(),
            'beat_times': beat_times.tolist(),
            'tempo': tempo,
            'sample_rate': sr,
            'hop_length': self.hop_length,
            'duration': len(y) / sr
        }


def analyze_melody(audio_path: str, sample_rate: int = 22050) -> Dict:
    """
    Convenience function to analyze melody and harmony of an audio file.
    
    Args:
        audio_path: Path to audio file
        sample_rate: Target sample rate
        
    Returns:
        Dictionary of melody/harmony features
    """
    analyzer = MelodyAnalyzer(sample_rate=sample_rate)
    return analyzer.extract_all_melody_features(audio_path)
