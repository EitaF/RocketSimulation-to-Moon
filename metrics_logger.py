"""
Metrics Logger for Monte Carlo Simulation Campaign
Logs detailed mission metrics for statistical analysis
"""

import csv
import json
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from datetime import datetime

# Optional plotting dependencies
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    from scipy import stats
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False


@dataclass
class MissionMetrics:
    """Container for mission performance metrics"""
    run_id: int
    mission_success: bool
    final_phase: str
    mission_duration: float  # seconds
    
    # Landing metrics
    landing_latitude: Optional[float] = None  # degrees
    landing_longitude: Optional[float] = None  # degrees
    final_velocity: Optional[float] = None  # m/s
    landing_accuracy: Optional[float] = None  # km from target
    
    # Propellant metrics
    propellant_margin_stage1: float = 0.0  # kg
    propellant_margin_stage2: float = 0.0  # kg
    propellant_margin_stage3: float = 0.0  # kg
    total_propellant_used: float = 0.0  # kg
    
    # Performance metrics
    max_altitude: float = 0.0  # m
    max_velocity: float = 0.0  # m/s
    total_delta_v: float = 0.0  # m/s
    max_dynamic_pressure: float = 0.0  # Pa
    
    # Orbital elements at LEO insertion
    leo_apoapsis: Optional[float] = None  # m
    leo_periapsis: Optional[float] = None  # m
    leo_eccentricity: Optional[float] = None
    leo_insertion_time: Optional[float] = None  # seconds
    
    # TLI and lunar trajectory metrics
    tli_delta_v: Optional[float] = None  # m/s
    coast_duration: Optional[float] = None  # seconds
    loi_delta_v: Optional[float] = None  # m/s
    
    # Abort/failure information
    abort_reason: Optional[str] = None
    abort_time: Optional[float] = None  # seconds


class MetricsLogger:
    """Handles logging and aggregation of mission metrics"""
    
    def __init__(self, output_dir: str = "mc_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self.metrics_list: List[MissionMetrics] = []
        
        # CSV file for individual run metrics
        self.csv_path = self.output_dir / "run_metrics.csv"
        self.csv_file = None
        self.csv_writer = None
        
        self._initialize_csv()
    
    def _initialize_csv(self):
        """Initialize CSV file with headers"""
        self.csv_file = open(self.csv_path, 'w', newline='')
        fieldnames = [field.name for field in MissionMetrics.__dataclass_fields__.values()]
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        self.csv_writer.writeheader()
    
    def log_mission_metrics(self, metrics: MissionMetrics):
        """Log metrics for a single mission run"""
        self.metrics_list.append(metrics)
        
        # Write to CSV
        if self.csv_writer:
            self.csv_writer.writerow(asdict(metrics))
            self.csv_file.flush()
        
        # Log summary for this run
        self.logger.info(
            f"Run {metrics.run_id:04d}: "
            f"Success={metrics.mission_success}, "
            f"Phase={metrics.final_phase}, "
            f"Duration={metrics.mission_duration/3600:.1f}h, "
            f"ΔV={metrics.total_delta_v:.0f}m/s"
        )
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate comprehensive statistics from all runs"""
        if not self.metrics_list:
            return {}
        
        # Success rate calculation
        successful_runs = [m for m in self.metrics_list if m.mission_success]
        success_rate = len(successful_runs) / len(self.metrics_list)
        
        # Confidence interval for success rate (Wilson score interval)
        n = len(self.metrics_list)
        p = success_rate
        z = 1.96  # 95% confidence
        
        if n > 0:
            ci_center = (p + z**2/(2*n)) / (1 + z**2/n)
            ci_width = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2)) / (1 + z**2/n)
            ci_lower = max(0, ci_center - ci_width)
            ci_upper = min(1, ci_center + ci_width)
            ci_width_actual = ci_upper - ci_lower
        else:
            ci_lower = ci_upper = ci_width_actual = 0
        
        # Performance statistics (successful runs only)
        if successful_runs:
            delta_v_values = [m.total_delta_v for m in successful_runs]
            mission_durations = [m.mission_duration for m in successful_runs]
            
            performance_stats = {
                "delta_v_mean": np.mean(delta_v_values),
                "delta_v_std": np.std(delta_v_values),
                "delta_v_min": np.min(delta_v_values),
                "delta_v_max": np.max(delta_v_values),
                "duration_mean": np.mean(mission_durations),
                "duration_std": np.std(mission_durations)
            }
        else:
            performance_stats = {}
        
        # Failure analysis
        failed_runs = [m for m in self.metrics_list if not m.mission_success]
        failure_reasons = {}
        for run in failed_runs:
            reason = run.abort_reason or run.final_phase
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        
        # Landing accuracy (for successful lunar missions)
        lunar_landings = [m for m in successful_runs if m.landing_latitude is not None]
        if lunar_landings:
            landing_accuracies = [m.landing_accuracy for m in lunar_landings if m.landing_accuracy is not None]
            landing_stats = {
                "landing_accuracy_mean": np.mean(landing_accuracies) if landing_accuracies else None,
                "landing_accuracy_std": np.std(landing_accuracies) if landing_accuracies else None,
                "successful_landings": len(lunar_landings)
            }
        else:
            landing_stats = {"successful_landings": 0}
        
        return {
            "total_runs": len(self.metrics_list),
            "successful_runs": len(successful_runs),
            "success_rate": success_rate,
            "confidence_interval": {
                "lower": ci_lower,
                "upper": ci_upper, 
                "width": ci_width_actual,
                "meets_target": ci_width_actual <= 0.03  # 3% target
            },
            "performance_stats": performance_stats,
            "failure_analysis": failure_reasons,
            "landing_stats": landing_stats,
            "meets_success_criteria": success_rate >= 0.90 and ci_width_actual <= 0.03
        }
    
    def save_summary_report(self) -> str:
        """Generate and save Monte Carlo summary report"""
        stats = self.calculate_statistics()
        
        # Generate markdown report
        report_path = self.output_dir / "montecarlo_summary.md"
        
        with open(report_path, 'w') as f:
            f.write("# Monte Carlo Simulation Campaign Results\n\n")
            f.write(f"**Campaign Date:** {Path().resolve().name}\n")
            f.write(f"**Total Runs:** {stats['total_runs']}\n")
            f.write(f"**Successful Missions:** {stats['successful_runs']}\n\n")
            
            f.write("## Success Rate Analysis\n\n")
            f.write(f"- **Success Rate:** {stats['success_rate']:.1%}\n")
            f.write(f"- **95% Confidence Interval:** [{stats['confidence_interval']['lower']:.1%}, {stats['confidence_interval']['upper']:.1%}]\n")
            f.write(f"- **CI Width:** {stats['confidence_interval']['width']:.1%}\n")
            f.write(f"- **Meets Target (≥90%):** {'✅' if stats['success_rate'] >= 0.90 else '❌'}\n")
            f.write(f"- **Meets CI Width (≤3%):** {'✅' if stats['confidence_interval']['width'] <= 0.03 else '❌'}\n\n")
            
            if stats['performance_stats']:
                f.write("## Performance Statistics (Successful Missions)\n\n")
                ps = stats['performance_stats']
                f.write(f"- **Total ΔV:** {ps['delta_v_mean']:.0f} ± {ps['delta_v_std']:.0f} m/s\n")
                f.write(f"- **ΔV Range:** {ps['delta_v_min']:.0f} - {ps['delta_v_max']:.0f} m/s\n")
                f.write(f"- **Mission Duration:** {ps['duration_mean']/3600:.1f} ± {ps['duration_std']/3600:.1f} hours\n\n")
            
            if stats['failure_analysis']:
                f.write("## Failure Analysis\n\n")
                for reason, count in stats['failure_analysis'].items():
                    percentage = (count / stats['total_runs']) * 100
                    f.write(f"- **{reason}:** {count} runs ({percentage:.1f}%)\n")
                f.write("\n")
            
            f.write("## Success Criteria Assessment\n\n")
            f.write(f"- **Target Success Rate (≥90%):** {'✅ PASS' if stats['success_rate'] >= 0.90 else '❌ FAIL'}\n")
            f.write(f"- **Target CI Width (≤3%):** {'✅ PASS' if stats['confidence_interval']['width'] <= 0.03 else '❌ FAIL'}\n")
            f.write(f"- **Overall Campaign:** {'✅ SUCCESS' if stats['meets_success_criteria'] else '❌ REQUIRES IMPROVEMENT'}\n\n")
            
            if not stats['meets_success_criteria']:
                f.write("## Recommendations\n\n")
                if stats['success_rate'] < 0.90:
                    f.write("- Investigate dominant failure modes and improve vehicle design\n")
                    f.write("- Consider guidance algorithm improvements\n")
                    f.write("- Review abort criteria and recovery procedures\n")
                if stats['confidence_interval']['width'] > 0.03:
                    f.write("- Increase sample size for narrower confidence interval\n")
                    f.write("- Consider variance reduction techniques\n")
        
        self.logger.info(f"Monte Carlo summary report saved to {report_path}")
        return str(report_path)
    
    def close(self):
        """Close CSV file and cleanup"""
        if self.csv_file:
            self.csv_file.close()
    
    def __del__(self):
        self.close()


def extract_metrics_from_mission_results(run_id: int, results: Dict, config: Dict) -> MissionMetrics:
    """Extract metrics from mission simulation results"""
    
    # Basic mission info
    metrics = MissionMetrics(
        run_id=run_id,
        mission_success=results.get('mission_success', False),
        final_phase=results.get('final_phase', 'unknown'),
        mission_duration=results.get('mission_duration', 0.0)
    )
    
    # Performance metrics
    metrics.max_altitude = results.get('max_altitude', 0.0)
    metrics.max_velocity = results.get('max_velocity', 0.0)
    metrics.total_delta_v = results.get('total_delta_v', 0.0)
    metrics.total_propellant_used = results.get('propellant_used', 0.0)
    
    # Landing metrics (if available)
    if 'landing_position' in results:
        pos = results['landing_position']
        metrics.landing_latitude = pos.get('latitude')
        metrics.landing_longitude = pos.get('longitude')
        metrics.landing_accuracy = pos.get('accuracy_km')
    
    metrics.final_velocity = results.get('final_velocity')
    
    # LEO orbital elements (if achieved)
    if 'leo_elements' in results:
        leo = results['leo_elements']
        metrics.leo_apoapsis = leo.get('apoapsis')
        metrics.leo_periapsis = leo.get('periapsis')
        metrics.leo_eccentricity = leo.get('eccentricity')
        metrics.leo_insertion_time = leo.get('insertion_time')
    
    # Abort information
    if not metrics.mission_success:
        metrics.abort_reason = results.get('abort_reason', metrics.final_phase)
        metrics.abort_time = results.get('abort_time')
    
    return metrics


class AdvancedMetricsAnalyzer:
    """Advanced analysis and visualization for Monte Carlo results"""
    
    def __init__(self, metrics_logger: MetricsLogger):
        self.metrics_logger = metrics_logger
        self.output_dir = metrics_logger.output_dir
        self.logger = logging.getLogger(__name__)
        
        if not PLOTTING_AVAILABLE:
            self.logger.warning("Plotting dependencies not available. Install matplotlib and seaborn for visualization.")
            return
        
        # Set up plotting style
        plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
        sns.set_palette("husl")
    
    def generate_performance_plots(self) -> List[str]:
        """Generate comprehensive performance visualization plots"""
        plot_files = []
        
        if not PLOTTING_AVAILABLE:
            self.logger.warning("Plotting functionality requires matplotlib and seaborn")
            return plot_files
        
        metrics = self.metrics_logger.metrics_list
        
        if not metrics:
            self.logger.warning("No metrics available for plotting")
            return plot_files
        
        # 1. Success rate vs run number (convergence plot)
        plot_files.append(self._plot_success_convergence(metrics))
        
        # 2. Delta-V distribution
        plot_files.append(self._plot_delta_v_distribution(metrics))
        
        # 3. Mission duration vs success
        plot_files.append(self._plot_duration_analysis(metrics))
        
        # 4. Failure mode analysis
        plot_files.append(self._plot_failure_modes(metrics))
        
        # 5. Orbital performance scatter plot
        plot_files.append(self._plot_orbital_performance(metrics))
        
        # 6. Propellant margins analysis
        plot_files.append(self._plot_propellant_analysis(metrics))
        
        return plot_files
    
    def _plot_success_convergence(self, metrics: List[MissionMetrics]) -> str:
        """Plot success rate convergence"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Running success rate
        successes = np.array([1 if m.mission_success else 0 for m in metrics])
        running_success = np.cumsum(successes) / np.arange(1, len(successes) + 1)
        runs = np.arange(1, len(metrics) + 1)
        
        ax1.plot(runs, running_success * 100, 'b-', linewidth=2)
        ax1.axhline(y=90, color='r', linestyle='--', label='90% Target')
        ax1.set_xlabel('Run Number')
        ax1.set_ylabel('Running Success Rate (%)')
        ax1.set_title('Monte Carlo Success Rate Convergence')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Confidence interval width
        ci_widths = []
        for i in range(10, len(metrics) + 1):  # Start from run 10
            n = i
            p = running_success[i-1]
            z = 1.96
            if n > 0:
                ci_center = (p + z**2/(2*n)) / (1 + z**2/n)
                ci_width = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2)) / (1 + z**2/n)
                ci_widths.append(ci_width * 2 * 100)  # Total width in percentage
            else:
                ci_widths.append(0)
        
        ax2.plot(runs[9:], ci_widths, 'g-', linewidth=2)
        ax2.axhline(y=3, color='r', linestyle='--', label='3% Target')
        ax2.set_xlabel('Run Number')
        ax2.set_ylabel('95% CI Width (%)')
        ax2.set_title('Confidence Interval Width Convergence')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = self.output_dir / 'success_convergence.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(plot_path)
    
    def _plot_delta_v_distribution(self, metrics: List[MissionMetrics]) -> str:
        """Plot Delta-V distribution for successful missions"""
        successful_metrics = [m for m in metrics if m.mission_success]
        
        if not successful_metrics:
            return ""
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        delta_vs = [m.total_delta_v for m in successful_metrics]
        
        # Histogram
        ax1.hist(delta_vs, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        ax1.axvline(np.mean(delta_vs), color='red', linestyle='--', 
                   label=f'Mean: {np.mean(delta_vs):.0f} m/s')
        ax1.set_xlabel('Total ΔV (m/s)')
        ax1.set_ylabel('Frequency')
        ax1.set_title('ΔV Distribution (Successful Missions)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Box plot by mission phase
        phases = list(set(m.final_phase for m in successful_metrics))
        phase_data = {}
        for phase in phases:
            phase_data[phase] = [m.total_delta_v for m in successful_metrics if m.final_phase == phase]
        
        ax2.boxplot(phase_data.values(), labels=phase_data.keys())
        ax2.set_ylabel('Total ΔV (m/s)')
        ax2.set_title('ΔV by Final Mission Phase')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = self.output_dir / 'delta_v_distribution.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(plot_path)
    
    def _plot_duration_analysis(self, metrics: List[MissionMetrics]) -> str:
        """Plot mission duration analysis"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Success vs failure duration comparison
        successful_durations = [m.mission_duration/3600 for m in metrics if m.mission_success]
        failed_durations = [m.mission_duration/3600 for m in metrics if not m.mission_success]
        
        ax1.hist([successful_durations, failed_durations], 
                label=['Successful', 'Failed'], alpha=0.7, bins=15)
        ax1.set_xlabel('Mission Duration (hours)')
        ax1.set_ylabel('Frequency')
        ax1.set_title('Mission Duration by Outcome')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Duration vs Delta-V scatter
        if successful_durations:
            successful_metrics = [m for m in metrics if m.mission_success]
            durations = [m.mission_duration/3600 for m in successful_metrics]
            delta_vs = [m.total_delta_v for m in successful_metrics]
            
            ax2.scatter(durations, delta_vs, alpha=0.6, c='blue')
            # Fit trend line
            if len(durations) > 1:
                z = np.polyfit(durations, delta_vs, 1)
                p = np.poly1d(z)
                ax2.plot(durations, p(durations), "r--", alpha=0.8)
            
            ax2.set_xlabel('Mission Duration (hours)')
            ax2.set_ylabel('Total ΔV (m/s)')
            ax2.set_title('Duration vs ΔV (Successful Missions)')
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = self.output_dir / 'duration_analysis.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(plot_path)
    
    def _plot_failure_modes(self, metrics: List[MissionMetrics]) -> str:
        """Plot failure mode analysis"""
        failed_metrics = [m for m in metrics if not m.mission_success]
        
        if not failed_metrics:
            return ""
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Failure reasons pie chart
        failure_reasons = {}
        for m in failed_metrics:
            reason = m.abort_reason or m.final_phase
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        
        ax1.pie(failure_reasons.values(), labels=failure_reasons.keys(), autopct='%1.1f%%')
        ax1.set_title('Failure Mode Distribution')
        
        # Failure time distribution
        failure_times = [m.abort_time/60 for m in failed_metrics if m.abort_time is not None]
        if failure_times:
            ax2.hist(failure_times, bins=15, alpha=0.7, color='red', edgecolor='black')
            ax2.set_xlabel('Failure Time (minutes)')
            ax2.set_ylabel('Frequency')
            ax2.set_title('Failure Time Distribution')
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = self.output_dir / 'failure_analysis.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(plot_path)
    
    def _plot_orbital_performance(self, metrics: List[MissionMetrics]) -> str:
        """Plot orbital performance metrics"""
        orbital_metrics = [m for m in metrics if m.leo_apoapsis is not None and m.leo_periapsis is not None]
        
        if not orbital_metrics:
            return ""
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Apoapsis vs Periapsis
        apoapses = [m.leo_apoapsis/1000 for m in orbital_metrics]  # Convert to km
        periapses = [m.leo_periapsis/1000 for m in orbital_metrics]
        colors = ['green' if m.mission_success else 'red' for m in orbital_metrics]
        
        ax1.scatter(periapses, apoapses, c=colors, alpha=0.6)
        ax1.plot([150, 250], [150, 250], 'k--', alpha=0.5, label='Circular orbit')
        ax1.set_xlabel('Periapsis (km)')
        ax1.set_ylabel('Apoapsis (km)')
        ax1.set_title('LEO Orbital Elements')
        ax1.legend(['Circular', 'Successful', 'Failed'])
        ax1.grid(True, alpha=0.3)
        
        # Eccentricity distribution
        eccentricities = [m.leo_eccentricity for m in orbital_metrics if m.leo_eccentricity is not None]
        if eccentricities:
            ax2.hist(eccentricities, bins=15, alpha=0.7, color='purple', edgecolor='black')
            ax2.set_xlabel('Eccentricity')
            ax2.set_ylabel('Frequency')
            ax2.set_title('LEO Orbit Eccentricity Distribution')
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = self.output_dir / 'orbital_performance.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(plot_path)
    
    def _plot_propellant_analysis(self, metrics: List[MissionMetrics]) -> str:
        """Plot propellant margin analysis"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        successful_metrics = [m for m in metrics if m.mission_success]
        
        if not successful_metrics:
            return ""
        
        # Stage 1 propellant margins
        stage1_margins = [m.propellant_margin_stage1 for m in successful_metrics]
        ax1.hist(stage1_margins, bins=15, alpha=0.7, color='blue', edgecolor='black')
        ax1.set_xlabel('Stage 1 Propellant Margin (kg)')
        ax1.set_ylabel('Frequency')
        ax1.set_title('Stage 1 Propellant Margins')
        ax1.grid(True, alpha=0.3)
        
        # Stage 2 propellant margins
        stage2_margins = [m.propellant_margin_stage2 for m in successful_metrics]
        ax2.hist(stage2_margins, bins=15, alpha=0.7, color='orange', edgecolor='black')
        ax2.set_xlabel('Stage 2 Propellant Margin (kg)')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Stage 2 Propellant Margins')
        ax2.grid(True, alpha=0.3)
        
        # Stage 3 propellant margins
        stage3_margins = [m.propellant_margin_stage3 for m in successful_metrics]
        ax3.hist(stage3_margins, bins=15, alpha=0.7, color='green', edgecolor='black')
        ax3.set_xlabel('Stage 3 Propellant Margin (kg)')
        ax3.set_ylabel('Frequency')
        ax3.set_title('Stage 3 Propellant Margins')
        ax3.grid(True, alpha=0.3)
        
        # Total propellant used
        total_propellant = [m.total_propellant_used/1000 for m in successful_metrics]  # Convert to tonnes
        ax4.hist(total_propellant, bins=15, alpha=0.7, color='red', edgecolor='black')
        ax4.set_xlabel('Total Propellant Used (tonnes)')
        ax4.set_ylabel('Frequency')
        ax4.set_title('Total Propellant Consumption')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = self.output_dir / 'propellant_analysis.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(plot_path)
    
    def perform_statistical_analysis(self) -> Dict[str, Any]:
        """Perform advanced statistical analysis"""
        metrics = self.metrics_logger.metrics_list
        successful_metrics = [m for m in metrics if m.mission_success]
        
        if not successful_metrics:
            return {}
        
        analysis_results = {}
        
        # Delta-V statistical tests (if scipy available)
        if PLOTTING_AVAILABLE:
            delta_vs = [m.total_delta_v for m in successful_metrics]
            analysis_results['delta_v_normality'] = {
                'shapiro_stat': stats.shapiro(delta_vs)[0],
                'shapiro_pvalue': stats.shapiro(delta_vs)[1],
                'is_normal': stats.shapiro(delta_vs)[1] > 0.05
            }
            
            # Mission duration correlation with success
            all_durations = [m.mission_duration for m in metrics]
            all_successes = [1 if m.mission_success else 0 for m in metrics]
            
            if len(set(all_successes)) > 1:  # If we have both successes and failures
                correlation, p_value = stats.pointbiserialr(all_successes, all_durations)
                analysis_results['duration_success_correlation'] = {
                    'correlation': correlation,
                    'p_value': p_value,
                    'significant': p_value < 0.05
                }
        
        # Propellant margin analysis
        stage1_margins = [m.propellant_margin_stage1 for m in successful_metrics]
        stage2_margins = [m.propellant_margin_stage2 for m in successful_metrics]
        stage3_margins = [m.propellant_margin_stage3 for m in successful_metrics]
        
        analysis_results['propellant_margins'] = {
            'stage1': {
                'mean': np.mean(stage1_margins),
                'std': np.std(stage1_margins),
                'min': np.min(stage1_margins),
                'negative_margin_risk': sum(1 for x in stage1_margins if x < 0) / len(stage1_margins)
            },
            'stage2': {
                'mean': np.mean(stage2_margins),
                'std': np.std(stage2_margins),
                'min': np.min(stage2_margins),
                'negative_margin_risk': sum(1 for x in stage2_margins if x < 0) / len(stage2_margins)
            },
            'stage3': {
                'mean': np.mean(stage3_margins),
                'std': np.std(stage3_margins),
                'min': np.min(stage3_margins),
                'negative_margin_risk': sum(1 for x in stage3_margins if x < 0) / len(stage3_margins)
            }
        }
        
        return analysis_results
    
    def generate_executive_summary(self) -> str:
        """Generate executive summary report with key insights"""
        stats = self.metrics_logger.calculate_statistics()
        analysis = self.perform_statistical_analysis()
        
        summary_path = self.output_dir / 'executive_summary.md'
        
        with open(summary_path, 'w') as f:
            f.write("# Monte Carlo Campaign Executive Summary\n\n")
            f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Campaign Size:** {stats['total_runs']} simulation runs\n\n")
            
            # Key Performance Indicators
            f.write("## Key Performance Indicators\n\n")
            f.write(f"| Metric | Value | Target | Status |\n")
            f.write(f"|--------|-------|--------|--------|\n")
            f.write(f"| Success Rate | {stats['success_rate']:.1%} | ≥90% | {'✅ PASS' if stats['success_rate'] >= 0.90 else '❌ FAIL'} |\n")
            f.write(f"| CI Width | {stats['confidence_interval']['width']:.1%} | ≤3% | {'✅ PASS' if stats['confidence_interval']['width'] <= 0.03 else '❌ FAIL'} |\n")
            
            if stats['performance_stats']:
                ps = stats['performance_stats']
                f.write(f"| Mean ΔV | {ps['delta_v_mean']:.0f} m/s | TBD | ℹ️ INFO |\n")
                f.write(f"| Mission Duration | {ps['duration_mean']/3600:.1f}h | TBD | ℹ️ INFO |\n")
            f.write("\n")
            
            # Risk Assessment
            f.write("## Risk Assessment\n\n")
            if stats['failure_analysis']:
                f.write("**Top Failure Modes:**\n")
                sorted_failures = sorted(stats['failure_analysis'].items(), key=lambda x: x[1], reverse=True)
                for i, (reason, count) in enumerate(sorted_failures[:3]):
                    risk_level = count / stats['total_runs']
                    f.write(f"{i+1}. {reason}: {risk_level:.1%} risk\n")
                f.write("\n")
            
            # Propellant Margin Assessment
            if 'propellant_margins' in analysis:
                f.write("## Propellant Margin Assessment\n\n")
                pm = analysis['propellant_margins']
                for stage in ['stage1', 'stage2', 'stage3']:
                    if stage in pm:
                        margin_data = pm[stage]
                        risk = margin_data['negative_margin_risk']
                        f.write(f"**{stage.upper()}:** Mean margin {margin_data['mean']:.0f}kg, ")
                        f.write(f"Depletion risk: {risk:.1%}\n")
                f.write("\n")
            
            # Recommendations
            f.write("## Recommendations\n\n")
            if not stats['meets_success_criteria']:
                if stats['success_rate'] < 0.90:
                    f.write("**HIGH PRIORITY:**\n")
                    f.write("- Investigate and mitigate dominant failure modes\n")
                    f.write("- Consider design improvements or operational changes\n")
                    f.write("- Review abort criteria and recovery procedures\n\n")
                
                if stats['confidence_interval']['width'] > 0.03:
                    f.write("**MEDIUM PRIORITY:**\n")
                    f.write("- Increase sample size for statistical confidence\n")
                    f.write("- Consider variance reduction techniques\n\n")
            else:
                f.write("- Mission design meets reliability requirements\n")
                f.write("- Consider optimization for performance improvements\n")
                f.write("- Monitor performance in operational environment\n\n")
            
            # Statistical Notes
            if 'delta_v_normality' in analysis:
                f.write("## Statistical Notes\n\n")
                norm = analysis['delta_v_normality']
                f.write(f"- ΔV distribution normality: {'Normal' if norm['is_normal'] else 'Non-normal'} ")
                f.write(f"(p={norm['shapiro_pvalue']:.3f})\n")
                
                if 'duration_success_correlation' in analysis:
                    corr = analysis['duration_success_correlation']
                    f.write(f"- Duration-success correlation: {corr['correlation']:.3f} ")
                    f.write(f"({'significant' if corr['significant'] else 'not significant'})\n")
        
        self.logger.info(f"Executive summary saved to {summary_path}")
        return str(summary_path)


def main():
    """Test the enhanced metrics logging system"""
    print("Enhanced Metrics Logging System Test")
    print("=" * 50)
    
    # Create metrics logger
    logger = MetricsLogger("test_mc_results")
    
    # Generate sample data
    print("Generating sample Monte Carlo data...")
    np.random.seed(42)  # For reproducible results
    
    for run_id in range(100):
        # Simulate mission outcome
        success_prob = 0.85 + 0.1 * np.random.random()  # 85-95% success rate
        mission_success = np.random.random() < success_prob
        
        # Generate metrics based on success
        if mission_success:
            final_phase = np.random.choice(["lunar_landing", "lunar_orbit", "leo_orbit"], p=[0.6, 0.3, 0.1])
            duration = np.random.normal(259200, 21600)  # 3 days ± 6 hours
            total_delta_v = np.random.normal(11500, 800)  # Typical lunar mission ΔV
            max_altitude = 384400000 if final_phase == "lunar_landing" else np.random.uniform(200000, 400000)
        else:
            final_phase = np.random.choice(["launch_failure", "ascent_failure", "tli_failure"], p=[0.4, 0.4, 0.2])
            duration = np.random.uniform(60, 14400)  # 1 minute to 4 hours
            total_delta_v = np.random.uniform(1000, 8000)
            max_altitude = np.random.uniform(1000, 150000)
        
        # Create metrics object
        metrics = MissionMetrics(
            run_id=run_id,
            mission_success=mission_success,
            final_phase=final_phase,
            mission_duration=duration,
            max_altitude=max_altitude,
            total_delta_v=total_delta_v,
            total_propellant_used=np.random.uniform(400000, 600000),
            propellant_margin_stage1=np.random.normal(5000, 2000),
            propellant_margin_stage2=np.random.normal(3000, 1500),
            propellant_margin_stage3=np.random.normal(1000, 800)
        )
        
        if mission_success and final_phase == "lunar_landing":
            metrics.landing_latitude = np.random.uniform(-10, 10)
            metrics.landing_longitude = np.random.uniform(-10, 10)
            metrics.landing_accuracy = np.random.exponential(5)  # km
        
        if mission_success and final_phase != "launch_failure":
            metrics.leo_apoapsis = np.random.uniform(190000, 220000)
            metrics.leo_periapsis = np.random.uniform(180000, 200000)
            metrics.leo_eccentricity = abs(metrics.leo_apoapsis - metrics.leo_periapsis) / (metrics.leo_apoapsis + metrics.leo_periapsis)
        
        if not mission_success:
            metrics.abort_reason = final_phase
            metrics.abort_time = duration * 0.8  # Abort partway through
        
        logger.log_mission_metrics(metrics)
    
    # Generate analysis
    print("\nGenerating analysis and reports...")
    
    # Basic statistics
    stats = logger.calculate_statistics()
    print(f"Success rate: {stats['success_rate']:.1%}")
    print(f"CI width: {stats['confidence_interval']['width']:.1%}")
    print(f"Meets criteria: {stats['meets_success_criteria']}")
    
    # Generate reports
    summary_report = logger.save_summary_report()
    print(f"Summary report: {summary_report}")
    
    # Advanced analysis
    analyzer = AdvancedMetricsAnalyzer(logger)
    
    try:
        plot_files = analyzer.generate_performance_plots()
        print(f"Generated {len(plot_files)} plots")
        
        statistical_analysis = analyzer.perform_statistical_analysis()
        print(f"Statistical analysis completed")
        
        executive_summary = analyzer.generate_executive_summary()
        print(f"Executive summary: {executive_summary}")
        
        print("\n✅ Enhanced metrics logging system test completed successfully!")
        
    except ImportError as e:
        print(f"⚠️ Plotting functionality requires matplotlib/seaborn: {e}")
        print("Basic metrics logging functionality works correctly")
    
    logger.close()


if __name__ == "__main__":
    main()