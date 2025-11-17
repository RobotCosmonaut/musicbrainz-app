#!/usr/bin/env python3
"""
Flake8 Metrics Visualization - DEBUGGED VERSION
This version includes extensive error checking and UTF-8 encoding fixes

Author: Ron Denny
Course: CS 8314 - Software Engineering Research
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime
import sys
import traceback

METRICS_DIR = Path(__file__).parent / "metrics_data"

class MetricsVisualizer:
    """Visualizes software quality metrics trends over time"""
    
    def __init__(self):
        self.summary_file = METRICS_DIR / "daily_summary.csv"
        self.df = None
    
    def load_data(self):
        """Load metrics data from CSV"""
        if not self.summary_file.exists():
            print(f"ERROR: No metrics data found at {self.summary_file}")
            print("   Run collect_metrics.py first to collect data")
            return False
        
        try:
            self.df = pd.read_csv(self.summary_file)
            print(f"SUCCESS: Loaded CSV with {len(self.df)} rows")
            print(f"Columns: {list(self.df.columns)}")
            
            self.df['Date'] = pd.to_datetime(self.df['Date'])
            self.df = self.df.sort_values('Date')
            
            print(f"SUCCESS: Loaded {len(self.df)} days of metrics data")
            print(f"\nData preview:")
            print(self.df.to_string())
            
            return True
        except Exception as e:
            print(f"ERROR loading data: {e}")
            traceback.print_exc()
            return False
    
    def create_defect_density_chart(self):
        """Create defect density trend chart"""
        print("\n  Creating defect density chart...")
        try:
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=self.df['Date'],
                y=self.df['Defect_Density'],
                mode='lines+markers',
                name='Defect Density',
                line=dict(color='#EF4444', width=3),
                marker=dict(size=8)
            ))
            
            # Add trend line
            if len(self.df) > 1:
                z = np.polyfit(range(len(self.df)), self.df['Defect_Density'], 1)
                p = np.poly1d(z)
                fig.add_trace(go.Scatter(
                    x=self.df['Date'],
                    y=p(range(len(self.df))),
                    mode='lines',
                    name='Trend',
                    line=dict(color='#6366F1', dash='dash', width=2)
                ))
            
            fig.update_layout(
                title='Defect Density Over Time (Violations per 1000 LOC)',
                xaxis_title='Date',
                yaxis_title='Defect Density',
                height=400,
                template='plotly_white'
            )
            
            print("    SUCCESS: Defect density chart created")
            return fig
        except Exception as e:
            print(f"    ERROR creating defect density chart: {e}")
            traceback.print_exc()
            return None
    
    def create_violations_chart(self):
        """Create violations trend chart"""
        print("\n  Creating violations chart...")
        try:
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=self.df['Date'],
                y=self.df['Total_Violations'],
                name='Total Violations',
                marker_color='#F97316'
            ))
            
            fig.update_layout(
                title='Total Code Violations Over Time',
                xaxis_title='Date',
                yaxis_title='Number of Violations',
                height=400,
                template='plotly_white'
            )
            
            print("    SUCCESS: Violations chart created")
            return fig
        except Exception as e:
            print(f"    ERROR creating violations chart: {e}")
            traceback.print_exc()
            return None
    
    def create_complexity_chart(self):
        """Create complexity trend chart"""
        print("\n  Creating complexity chart...")
        try:
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Average Complexity', 'Maximum Complexity'),
                vertical_spacing=0.15
            )
            
            fig.add_trace(go.Scatter(
                x=self.df['Date'],
                y=self.df['Avg_Complexity'],
                mode='lines+markers',
                name='Avg Complexity',
                line=dict(color='#6366F1', width=3),
                marker=dict(size=8)
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=self.df['Date'],
                y=self.df['Max_Complexity'],
                mode='lines+markers',
                name='Max Complexity',
                line=dict(color='#EF4444', width=3),
                marker=dict(size=8)
            ), row=2, col=1)
            
            # Add threshold line at 8
            fig.add_hline(y=8, line_dash="dot", line_color="gray", 
                         annotation_text="Configured Max (8)", row=2, col=1)
            
            fig.update_layout(
                height=600,
                template='plotly_white',
                showlegend=False
            )
            
            fig.update_xaxes(title_text="Date", row=2, col=1)
            fig.update_yaxes(title_text="Complexity", row=1, col=1)
            fig.update_yaxes(title_text="Complexity", row=2, col=1)
            
            print("    SUCCESS: Complexity chart created")
            return fig
        except Exception as e:
            print(f"    ERROR creating complexity chart: {e}")
            traceback.print_exc()
            return None
    
    def create_error_breakdown_chart(self):
        """Create error type breakdown chart"""
        print("\n  Creating error breakdown chart...")
        try:
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=self.df['Date'],
                y=self.df['E_Errors'],
                mode='lines+markers',
                name='Errors (E)',
                stackgroup='one',
                fillcolor='#EF4444'
            ))
            
            fig.add_trace(go.Scatter(
                x=self.df['Date'],
                y=self.df['W_Warnings'],
                mode='lines+markers',
                name='Warnings (W)',
                stackgroup='one',
                fillcolor='#F97316'
            ))
            
            fig.add_trace(go.Scatter(
                x=self.df['Date'],
                y=self.df['F_Errors'],
                mode='lines+markers',
                name='Fatal Errors (F)',
                stackgroup='one',
                fillcolor='#DC2626'
            ))
            
            fig.update_layout(
                title='Error Type Breakdown Over Time',
                xaxis_title='Date',
                yaxis_title='Count',
                height=400,
                template='plotly_white'
            )
            
            print("    SUCCESS: Error breakdown chart created")
            return fig
        except Exception as e:
            print(f"    ERROR creating error breakdown chart: {e}")
            traceback.print_exc()
            return None
    
    def create_code_growth_chart(self):
        """Create code growth chart"""
        print("\n  Creating code growth chart...")
        try:
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=self.df['Date'],
                y=self.df['Total_Lines'],
                mode='lines+markers',
                name='Lines of Code',
                line=dict(color='#22C55E', width=3),
                marker=dict(size=8)
            ))
            
            fig.update_layout(
                title='Codebase Size Over Time',
                xaxis_title='Date',
                yaxis_title='Lines of Code',
                height=400,
                template='plotly_white'
            )
            
            print("    SUCCESS: Code growth chart created")
            return fig
        except Exception as e:
            print(f"    ERROR creating code growth chart: {e}")
            traceback.print_exc()
            return None
    
    def generate_summary_stats(self):
        """Generate summary statistics"""
        if len(self.df) == 0:
            return
        
        latest = self.df.iloc[-1]
        
        print("\n" + "="*60)
        print("METRICS SUMMARY STATISTICS")
        print("="*60)
        print(f"Data Range: {self.df['Date'].min().strftime('%Y-%m-%d')} to {self.df['Date'].max().strftime('%Y-%m-%d')}")
        print(f"Total Days: {len(self.df)}")
        
        print(f"\nLatest Metrics ({latest['Date'].strftime('%Y-%m-%d')}):")
        print(f"  Total Violations: {latest['Total_Violations']}")
        print(f"  Defect Density: {latest['Defect_Density']:.2f} violations/KLOC")
        print(f"  Average Complexity: {latest['Avg_Complexity']:.2f}")
        print(f"  Maximum Complexity: {latest['Max_Complexity']}")
        print(f"  Lines of Code: {latest['Total_Lines']}")
        
        print(f"\nTrend Analysis:")
        
        # Calculate trends
        if len(self.df) > 1:
            first = self.df.iloc[0]
            
            defect_change = ((latest['Defect_Density'] - first['Defect_Density']) / 
                           first['Defect_Density'] * 100 if first['Defect_Density'] > 0 else 0)
            
            complexity_change = ((latest['Avg_Complexity'] - first['Avg_Complexity']) / 
                               first['Avg_Complexity'] * 100 if first['Avg_Complexity'] > 0 else 0)
            
            violations_change = ((latest['Total_Violations'] - first['Total_Violations']) / 
                               first['Total_Violations'] * 100 if first['Total_Violations'] > 0 else 0)
            
            print(f"  Defect Density: {defect_change:+.1f}%")
            print(f"  Average Complexity: {complexity_change:+.1f}%")
            print(f"  Total Violations: {violations_change:+.1f}%")
        
        print(f"\nOverall Statistics:")
        print(f"  Mean Defect Density: {self.df['Defect_Density'].mean():.2f}")
        print(f"  Mean Complexity: {self.df['Avg_Complexity'].mean():.2f}")
        print(f"  Mean Violations: {self.df['Total_Violations'].mean():.0f}")
        print("="*60 + "\n")
    
    def save_all_charts(self):
        """Save all charts to HTML file - DEBUGGED VERSION"""
        output_file = METRICS_DIR / "metrics_dashboard.html"
        
        print("\n" + "="*60)
        print("CREATING VISUALIZATIONS")
        print("="*60)
        
        charts = []
        
        # Create charts with individual error handling
        chart_creators = [
            ("Defect Density", self.create_defect_density_chart),
            ("Violations", self.create_violations_chart),
            ("Complexity", self.create_complexity_chart),
            ("Error Breakdown", self.create_error_breakdown_chart),
            ("Code Growth", self.create_code_growth_chart)
        ]
        
        for name, creator in chart_creators:
            chart = creator()
            if chart is not None:
                charts.append(chart)
            else:
                print(f"  WARNING: {name} chart was not created")
        
        if not charts:
            print("\nERROR: No charts could be created!")
            print("Check the errors above for details.")
            return
        
        print(f"\nSUCCESS: Created {len(charts)} out of {len(chart_creators)} charts")
        
        # Create HTML with proper encoding
        print("\nGenerating HTML file...")
        
        latest = self.df.iloc[-1]
        
        # Generate chart HTML strings first
        chart_html_list = []
        for i, chart in enumerate(charts):
            chart_html = chart.to_html(full_html=False, include_plotlyjs=False, div_id=f"chart_{i}")
            chart_html_list.append(f'<div class="chart">{chart_html}</div>')
        
        charts_combined = "\n".join(chart_html_list)
        
        # Build HTML - no .format() needed, use direct string concatenation
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Orchestr8r - Software Quality Metrics Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{ 
            color: #333; 
            text-align: center;
        }}
        .chart {{ 
            margin: 30px auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            max-width: 1200px;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            color: #666;
        }}
        .stats {{
            background: white;
            padding: 20px;
            margin: 20px auto;
            max-width: 1200px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .debug {{
            background: #fff3cd;
            padding: 10px;
            margin: 10px auto;
            max-width: 1200px;
            border-radius: 4px;
            border: 1px solid #ffc107;
        }}
    </style>
</head>
<body>
    <h1>Orchestr8r - Software Quality Metrics Dashboard</h1>
    <div class="debug">
        <strong>Debug Info:</strong> Generated {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | Charts created: {len(charts)}/{len(chart_creators)}
    </div>
    <div class="stats">
        <h2>Latest Metrics Summary</h2>
        <p><strong>Date:</strong> {latest['Date'].strftime('%Y-%m-%d')}</p>
        <p><strong>Total Violations:</strong> {int(latest['Total_Violations'])}</p>
        <p><strong>Defect Density:</strong> {float(latest['Defect_Density']):.2f} violations per 1000 LOC</p>
        <p><strong>Average Complexity:</strong> {float(latest['Avg_Complexity']):.2f}</p>
        <p><strong>Maximum Complexity:</strong> {int(latest['Max_Complexity'])}</p>
        <p><strong>Total Lines of Code:</strong> {int(latest['Total_Lines']):,}</p>
    </div>
    {charts_combined}
    <div class="footer">
        <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>
        Course: CS 8314 - Software Engineering Research<br>
        Data collected using Flake8 static analysis</p>
    </div>
</body>
</html>
"""
        
        # Write with explicit UTF-8 encoding
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"\nSUCCESS: Dashboard saved to: {output_file}")
            print(f"  File size: {output_file.stat().st_size:,} bytes")
            print(f"  Open in browser: file://{output_file.absolute()}")
            print(f"  Created {len(charts)} charts successfully!")
        except Exception as e:
            print(f"\nERROR writing HTML file: {e}")
            traceback.print_exc()

def main():
    """Main execution function"""
    
    print("="*60)
    print("FLAKE8 METRICS VISUALIZATION - DEBUG MODE")
    print("="*60)
    
    visualizer = MetricsVisualizer()
    
    if not visualizer.load_data():
        print("\nFAILED: Could not load data")
        return
    
    # Generate summary statistics
    visualizer.generate_summary_stats()
    
    # Create and save visualizations
    visualizer.save_all_charts()
    
    print("\n" + "="*60)
    print("VISUALIZATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
