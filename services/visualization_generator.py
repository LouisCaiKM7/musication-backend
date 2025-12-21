"""
Visualization Generation Service
Creates visualizations for music similarity analysis including heatmaps,
DTW path plots, and melody contour comparisons.
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server
import matplotlib.pyplot as plt
import seaborn as sns
import librosa
import librosa.display
from typing import Dict, Optional, Tuple
import io
import base64
from matplotlib.patches import Rectangle


class VisualizationGenerator:
    """
    Generates visualizations for music similarity analysis.
    """
    
    def __init__(self, dpi: int = 100, figsize: Tuple[int, int] = (12, 8)):
        """
        Initialize the VisualizationGenerator.
        
        Args:
            dpi: Resolution of output images
            figsize: Figure size in inches (width, height)
        """
        self.dpi = dpi
        self.figsize = figsize
        
        # Set style
        sns.set_style("whitegrid")
        plt.rcParams['figure.dpi'] = dpi
        
    def plot_chroma_heatmap(self, chroma1: np.ndarray, chroma2: np.ndarray,
                           track1_title: str = "Track 1",
                           track2_title: str = "Track 2",
                           hop_length: int = 512,
                           sample_rate: int = 22050) -> Tuple[bytes, str]:
        """
        Create side-by-side chroma heatmaps for two tracks.
        
        Args:
            chroma1: First chroma features (12 x n_frames)
            chroma2: Second chroma features (12 x n_frames)
            track1_title: Title of first track
            track2_title: Title of second track
            hop_length: Hop length used in feature extraction
            sample_rate: Sample rate
            
        Returns:
            Tuple of (image_bytes, base64_string)
        """
        fig, axes = plt.subplots(2, 1, figsize=(14, 8))
        
        # Plot first track
        img1 = librosa.display.specshow(
            chroma1,
            y_axis='chroma',
            x_axis='time',
            hop_length=hop_length,
            sr=sample_rate,
            ax=axes[0],
            cmap='coolwarm'
        )
        axes[0].set_title(f'Chroma Features: {track1_title}', fontsize=14, fontweight='bold')
        axes[0].set_ylabel('Pitch Class', fontsize=12)
        fig.colorbar(img1, ax=axes[0], format='%0.2f')
        
        # Plot second track
        img2 = librosa.display.specshow(
            chroma2,
            y_axis='chroma',
            x_axis='time',
            hop_length=hop_length,
            sr=sample_rate,
            ax=axes[1],
            cmap='coolwarm'
        )
        axes[1].set_title(f'Chroma Features: {track2_title}', fontsize=14, fontweight='bold')
        axes[1].set_ylabel('Pitch Class', fontsize=12)
        axes[1].set_xlabel('Time (s)', fontsize=12)
        fig.colorbar(img2, ax=axes[1], format='%0.2f')
        
        plt.tight_layout()
        
        # Convert to bytes
        img_bytes, img_base64 = self._fig_to_bytes(fig)
        plt.close(fig)
        
        return img_bytes, img_base64
    
    def plot_dtw_alignment_heatmap(self, cost_matrix: np.ndarray,
                                   dtw_path: np.ndarray,
                                   track1_title: str = "Track 1",
                                   track2_title: str = "Track 2",
                                   hop_length: int = 512,
                                   sample_rate: int = 22050) -> Tuple[bytes, str]:
        """
        Create DTW cost matrix heatmap with optimal path overlay.
        
        Args:
            cost_matrix: DTW cost matrix
            dtw_path: Optimal alignment path (list of [i, j] indices)
            track1_title: Title of first track
            track2_title: Title of second track
            hop_length: Hop length used in feature extraction
            sample_rate: Sample rate
            
        Returns:
            Tuple of (image_bytes, base64_string)
        """
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Convert cost to similarity for better visualization
        similarity_matrix = 1.0 / (1.0 + cost_matrix)
        
        # Plot heatmap
        im = ax.imshow(
            similarity_matrix.T,
            aspect='auto',
            origin='lower',
            cmap='YlOrRd',
            interpolation='nearest'
        )
        
        # Plot DTW path
        path = np.array(dtw_path)
        ax.plot(path[:, 0], path[:, 1], 'b-', linewidth=2, label='DTW Alignment Path', alpha=0.7)
        ax.plot(path[:, 0], path[:, 1], 'b.', markersize=3)
        
        # Convert frame indices to time
        n_frames1, n_frames2 = cost_matrix.shape
        time1 = librosa.frames_to_time(np.arange(n_frames1), sr=sample_rate, hop_length=hop_length)
        time2 = librosa.frames_to_time(np.arange(n_frames2), sr=sample_rate, hop_length=hop_length)
        
        # Set tick labels
        n_ticks = 10
        tick_indices_x = np.linspace(0, n_frames1-1, n_ticks, dtype=int)
        tick_indices_y = np.linspace(0, n_frames2-1, n_ticks, dtype=int)
        ax.set_xticks(tick_indices_x)
        ax.set_xticklabels([f'{time1[i]:.1f}' for i in tick_indices_x])
        ax.set_yticks(tick_indices_y)
        ax.set_yticklabels([f'{time2[i]:.1f}' for i in tick_indices_y])
        
        ax.set_xlabel(f'{track1_title} (time in seconds)', fontsize=12)
        ax.set_ylabel(f'{track2_title} (time in seconds)', fontsize=12)
        ax.set_title('Cross-Similarity Matrix with DTW Alignment Path\n(Brighter = More Similar)', 
                    fontsize=14, fontweight='bold')
        
        # Add colorbar
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label('Similarity Score', fontsize=11)
        
        # Add legend
        ax.legend(loc='upper left', fontsize=10)
        
        plt.tight_layout()
        
        # Convert to bytes
        img_bytes, img_base64 = self._fig_to_bytes(fig)
        plt.close(fig)
        
        return img_bytes, img_base64
    
    def plot_melody_contours(self, f0_1: np.ndarray, f0_2: np.ndarray,
                            voiced_1: np.ndarray, voiced_2: np.ndarray,
                            track1_title: str = "Track 1",
                            track2_title: str = "Track 2",
                            hop_length: int = 512,
                            sample_rate: int = 22050,
                            dtw_path: Optional[np.ndarray] = None) -> Tuple[bytes, str]:
        """
        Create melody contour comparison plot.
        
        Args:
            f0_1: First F0 contour (Hz)
            f0_2: Second F0 contour (Hz)
            voiced_1: Voiced flags for first track
            voiced_2: Voiced flags for second track
            track1_title: Title of first track
            track2_title: Title of second track
            hop_length: Hop length used in feature extraction
            sample_rate: Sample rate
            dtw_path: Optional DTW alignment path
            
        Returns:
            Tuple of (image_bytes, base64_string)
        """
        fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=False)
        
        # Convert to time and MIDI
        time1 = librosa.frames_to_time(np.arange(len(f0_1)), sr=sample_rate, hop_length=hop_length)
        time2 = librosa.frames_to_time(np.arange(len(f0_2)), sr=sample_rate, hop_length=hop_length)
        
        # Convert Hz to MIDI notes for better visualization
        midi_1 = librosa.hz_to_midi(np.maximum(f0_1, 1e-10))
        midi_2 = librosa.hz_to_midi(np.maximum(f0_2, 1e-10))
        
        # Set unvoiced to NaN for gaps in plot
        midi_1[~voiced_1] = np.nan
        midi_2[~voiced_2] = np.nan
        
        # Plot first track
        axes[0].plot(time1, midi_1, 'b-', linewidth=1.5, label='Melody Contour')
        axes[0].fill_between(time1, 0, 127, where=voiced_1, alpha=0.1, color='blue', label='Voiced Regions')
        axes[0].set_ylabel('MIDI Note Number', fontsize=12)
        axes[0].set_title(f'Melody Contour: {track1_title}', fontsize=14, fontweight='bold')
        axes[0].set_ylim([40, 90])
        axes[0].grid(True, alpha=0.3)
        axes[0].legend(loc='upper right')
        
        # Add note labels
        note_labels = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        note_ticks = [48, 60, 72, 84]  # C3, C4, C5, C6
        axes[0].set_yticks(note_ticks)
        axes[0].set_yticklabels([f'{note_labels[n%12]}{n//12}' for n in note_ticks])
        
        # Plot second track
        axes[1].plot(time2, midi_2, 'r-', linewidth=1.5, label='Melody Contour')
        axes[1].fill_between(time2, 0, 127, where=voiced_2, alpha=0.1, color='red', label='Voiced Regions')
        axes[1].set_ylabel('MIDI Note Number', fontsize=12)
        axes[1].set_xlabel('Time (seconds)', fontsize=12)
        axes[1].set_title(f'Melody Contour: {track2_title}', fontsize=14, fontweight='bold')
        axes[1].set_ylim([40, 90])
        axes[1].grid(True, alpha=0.3)
        axes[1].legend(loc='upper right')
        
        axes[1].set_yticks(note_ticks)
        axes[1].set_yticklabels([f'{note_labels[n%12]}{n//12}' for n in note_ticks])
        
        plt.tight_layout()
        
        # Convert to bytes
        img_bytes, img_base64 = self._fig_to_bytes(fig)
        plt.close(fig)
        
        return img_bytes, img_base64
    
    def plot_similarity_segments(self, similar_segments: list,
                                duration1: float, duration2: float,
                                track1_title: str = "Track 1",
                                track2_title: str = "Track 2") -> Tuple[bytes, str]:
        """
        Visualize similar segments between two tracks.
        
        Args:
            similar_segments: List of similar segment dictionaries
            duration1: Duration of first track
            duration2: Duration of second track
            track1_title: Title of first track
            track2_title: Title of second track
            
        Returns:
            Tuple of (image_bytes, base64_string)
        """
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # Draw timeline bars
        bar_height = 0.8
        track1_y = 2
        track2_y = 1
        
        # Draw track timelines
        ax.barh(track1_y, duration1, height=bar_height, left=0, color='lightblue', 
                edgecolor='black', linewidth=2, label=track1_title)
        ax.barh(track2_y, duration2, height=bar_height, left=0, color='lightcoral', 
                edgecolor='black', linewidth=2, label=track2_title)
        
        # Draw similar segments
        colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(similar_segments)))
        
        for i, seg in enumerate(similar_segments[:10]):  # Show top 10
            # Segment on track 1
            start1 = seg['track1_start_time']
            width1 = seg['track1_end_time'] - start1
            rect1 = Rectangle((start1, track1_y - bar_height/2), width1, bar_height,
                             facecolor=colors[i], edgecolor='darkgreen', 
                             linewidth=2, alpha=0.7)
            ax.add_patch(rect1)
            
            # Segment on track 2
            start2 = seg['track2_start_time']
            width2 = seg['track2_end_time'] - start2
            rect2 = Rectangle((start2, track2_y - bar_height/2), width2, bar_height,
                             facecolor=colors[i], edgecolor='darkgreen', 
                             linewidth=2, alpha=0.7)
            ax.add_patch(rect2)
            
            # Draw connection line
            mid1_x = start1 + width1/2
            mid2_x = start2 + width2/2
            ax.plot([mid1_x, mid2_x], [track1_y - bar_height/2, track2_y + bar_height/2],
                   'g--', linewidth=1.5, alpha=0.5)
            
            # Add similarity label
            mid_y = (track1_y + track2_y) / 2
            ax.text(max(mid1_x, mid2_x) + 1, mid_y, 
                   f'{seg["similarity_score"]*100:.0f}%',
                   fontsize=9, ha='left', va='center',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
        
        # Formatting
        ax.set_ylim([0.5, 2.5])
        ax.set_xlim([0, max(duration1, duration2) * 1.1])
        ax.set_yticks([track2_y, track1_y])
        ax.set_yticklabels([track2_title, track1_title], fontsize=12)
        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_title('Similar Segments Timeline\n(Connected regions show matching sections)', 
                    fontsize=14, fontweight='bold')
        ax.grid(True, axis='x', alpha=0.3)
        
        plt.tight_layout()
        
        # Convert to bytes
        img_bytes, img_base64 = self._fig_to_bytes(fig)
        plt.close(fig)
        
        return img_bytes, img_base64
    
    def plot_similarity_summary(self, comparison_result: Dict) -> Tuple[bytes, str]:
        """
        Create a summary visualization with multiple metrics.
        
        Args:
            comparison_result: Complete comparison result dictionary
            
        Returns:
            Tuple of (image_bytes, base64_string)
        """
        fig = plt.figure(figsize=(14, 10))
        gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
        
        overall = comparison_result['overall_similarity']
        components = overall['component_scores']
        
        # 1. Overall similarity gauge
        ax1 = fig.add_subplot(gs[0, :])
        self._plot_similarity_gauge(ax1, overall['similarity_percentage'])
        
        # 2. Component scores bar chart
        ax2 = fig.add_subplot(gs[1, 0])
        comp_names = ['Harmony\n(Chroma)', 'Melody\n(Contour)', 'Tempo\n(Match)']
        comp_values = [components['chroma_harmony'] * 100,
                      components['melody_contour'] * 100,
                      components['tempo'] * 100]
        colors_bar = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        bars = ax2.bar(comp_names, comp_values, color=colors_bar, edgecolor='black', linewidth=2)
        ax2.set_ylabel('Score (%)', fontsize=12)
        ax2.set_title('Component Scores', fontsize=13, fontweight='bold')
        ax2.set_ylim([0, 100])
        ax2.axhline(y=50, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax2.grid(True, axis='y', alpha=0.3)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 2,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        # 3. Key/Tempo info
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.axis('off')
        
        info_text = []
        info_text.append(f"Track 1: {comparison_result['track1']['title']}")
        info_text.append(f"Duration: {comparison_result['track1']['duration']:.1f}s")
        info_text.append(f"Tempo: {comparison_result['track1']['tempo']:.1f} BPM\n")
        
        info_text.append(f"Track 2: {comparison_result['track2']['title']}")
        info_text.append(f"Duration: {comparison_result['track2']['duration']:.1f}s")
        info_text.append(f"Tempo: {comparison_result['track2']['tempo']:.1f} BPM\n")
        
        transposition = comparison_result['chroma_analysis']['transposition_semitones']
        if transposition == 0:
            info_text.append("Key: Same key")
        else:
            direction = "higher" if transposition > 0 else "lower"
            info_text.append(f"Key: Track 2 is {abs(transposition)} semitones {direction}")
        
        ax3.text(0.1, 0.9, '\n'.join(info_text), transform=ax3.transAxes,
                fontsize=11, verticalalignment='top', family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # 4. Similar segments summary
        ax4 = fig.add_subplot(gs[2, :])
        similar_segs = comparison_result.get('similar_segments', [])
        
        if similar_segs:
            ax4.axis('off')
            seg_text = [f"Found {len(similar_segs)} similar segments:\n"]
            for i, seg in enumerate(similar_segs[:5], 1):
                seg_text.append(
                    f"{i}. [{seg['track1_start_time']:.1f}s - {seg['track1_end_time']:.1f}s] "
                    f"↔ [{seg['track2_start_time']:.1f}s - {seg['track2_end_time']:.1f}s] "
                    f"({seg['similarity_score']*100:.0f}% match)"
                )
            ax4.text(0.05, 0.95, '\n'.join(seg_text), transform=ax4.transAxes,
                    fontsize=10, verticalalignment='top', family='monospace',
                    bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))
        else:
            ax4.text(0.5, 0.5, 'No highly similar segments detected',
                    transform=ax4.transAxes, ha='center', va='center',
                    fontsize=12, style='italic', color='gray')
        
        # Convert to bytes
        img_bytes, img_base64 = self._fig_to_bytes(fig)
        plt.close(fig)
        
        return img_bytes, img_base64
    
    def _plot_similarity_gauge(self, ax, percentage: float):
        """
        Plot a gauge showing overall similarity percentage.
        
        Args:
            ax: Matplotlib axis
            percentage: Similarity percentage (0-100)
        """
        # Determine color based on percentage
        if percentage >= 80:
            color = '#FF4444'
            label = 'Very High Similarity'
        elif percentage >= 60:
            color = '#FF8C00'
            label = 'High Similarity'
        elif percentage >= 40:
            color = '#FFD700'
            label = 'Moderate Similarity'
        elif percentage >= 20:
            color = '#90EE90'
            label = 'Low Similarity'
        else:
            color = '#90EE90'
            label = 'Very Low Similarity'
        
        # Create gauge
        theta = np.linspace(0, np.pi, 100)
        r = 1
        
        # Background arc
        ax.plot(r * np.cos(theta), r * np.sin(theta), 'lightgray', linewidth=20, solid_capstyle='round')
        
        # Colored arc based on percentage
        theta_filled = np.linspace(0, np.pi * (percentage / 100), 100)
        ax.plot(r * np.cos(theta_filled), r * np.sin(theta_filled), color, linewidth=20, solid_capstyle='round')
        
        # Center text
        ax.text(0, -0.2, f'{percentage:.1f}%', ha='center', va='center',
               fontsize=40, fontweight='bold', color=color)
        ax.text(0, -0.5, label, ha='center', va='center',
               fontsize=14, fontweight='bold', color=color)
        
        ax.set_xlim([-1.3, 1.3])
        ax.set_ylim([-0.8, 1.3])
        ax.axis('off')
        ax.set_title('Overall Similarity Score', fontsize=16, fontweight='bold', pad=20)
    
    def _fig_to_bytes(self, fig) -> Tuple[bytes, str]:
        """
        Convert matplotlib figure to bytes and base64 string.
        
        Args:
            fig: Matplotlib figure
            
        Returns:
            Tuple of (image_bytes, base64_string)
        """
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=self.dpi, bbox_inches='tight')
        buf.seek(0)
        img_bytes = buf.read()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        buf.close()
        return img_bytes, img_base64
    
    def generate_all_visualizations(self, comparison_result: Dict,
                                   output_dir: Optional[str] = None) -> Dict[str, Dict]:
        """
        Generate all visualizations for a comparison result.
        
        Args:
            comparison_result: Complete comparison result from SimilarityComparator
            output_dir: Optional directory to save images to disk
            
        Returns:
            Dictionary mapping visualization names to {bytes, base64, path}
        """
        visualizations = {}
        
        # Extract data
        raw_data = comparison_result['raw_data']
        features1 = raw_data['features1']
        features2 = raw_data['features2']
        
        chroma1 = np.array(features1['chroma_cqt'])
        chroma2 = np.array(features2['chroma_cqt'])
        cost_matrix = np.array(raw_data['chroma_cost_matrix'])
        dtw_path = np.array(raw_data['chroma_dtw_path'])
        f0_1 = np.array(features1['f0_smoothed'])
        f0_2 = np.array(features2['f0_smoothed'])
        voiced_1 = np.array(features1['voiced_flag'])
        voiced_2 = np.array(features2['voiced_flag'])
        
        track1_title = comparison_result['track1']['title']
        track2_title = comparison_result['track2']['title']
        
        hop_length = features1['hop_length']
        sample_rate = features1['sample_rate']
        
        # 1. Chroma heatmaps
        print("Generating chroma heatmap...")
        img_bytes, img_base64 = self.plot_chroma_heatmap(
            chroma1, chroma2, track1_title, track2_title, hop_length, sample_rate
        )
        visualizations['chroma_heatmap'] = {
            'bytes': img_bytes,
            'base64': img_base64,
            'filename': 'chroma_comparison.png'
        }
        
        # 2. DTW alignment heatmap
        print("Generating DTW alignment heatmap...")
        img_bytes, img_base64 = self.plot_dtw_alignment_heatmap(
            cost_matrix, dtw_path, track1_title, track2_title, hop_length, sample_rate
        )
        visualizations['dtw_heatmap'] = {
            'bytes': img_bytes,
            'base64': img_base64,
            'filename': 'dtw_alignment.png'
        }
        
        # 3. Melody contours
        print("Generating melody contour plot...")
        img_bytes, img_base64 = self.plot_melody_contours(
            f0_1, f0_2, voiced_1, voiced_2, track1_title, track2_title,
            hop_length, sample_rate
        )
        visualizations['melody_contours'] = {
            'bytes': img_bytes,
            'base64': img_base64,
            'filename': 'melody_contours.png'
        }
        
        # 4. Similar segments timeline
        if comparison_result.get('similar_segments'):
            print("Generating similar segments timeline...")
            img_bytes, img_base64 = self.plot_similarity_segments(
                comparison_result['similar_segments'],
                comparison_result['track1']['duration'],
                comparison_result['track2']['duration'],
                track1_title, track2_title
            )
            visualizations['segments_timeline'] = {
                'bytes': img_bytes,
                'base64': img_base64,
                'filename': 'similar_segments.png'
            }
        
        # 5. Summary dashboard
        print("Generating summary dashboard...")
        img_bytes, img_base64 = self.plot_similarity_summary(comparison_result)
        visualizations['summary_dashboard'] = {
            'bytes': img_bytes,
            'base64': img_base64,
            'filename': 'summary_dashboard.png'
        }
        
        # Save to disk if output_dir provided
        if output_dir:
            import os
            os.makedirs(output_dir, exist_ok=True)
            for name, viz in visualizations.items():
                filepath = os.path.join(output_dir, viz['filename'])
                with open(filepath, 'wb') as f:
                    f.write(viz['bytes'])
                viz['path'] = filepath
        
        return visualizations
