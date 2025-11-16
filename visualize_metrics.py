#!/usr/bin/env python3
"""
Flake8 Metrics Visualization and Trend Analysis
Generates charts and reports from collected metrics data

Author: Ron Denny
Course: CS 8314 - Software Metrics & Quality Engineering
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime
import sys

METRICS_DIR = Path(__file__).parent / "metrics_data"

class MetricsVisualizer:
    """Visualizes software quality metrics trends over time"""
    
    def __init__(self):
        self.summary_file = METRICS_DIR / "daily_summary.csv"
        self.df = None
    
    def load_data(self):
        """Load metrics data from CSV"""
        if not self.summary_file.exists():
            print(f"❌ No metrics data found at {self.summary_file}")
            print("   Run collect_metrics.py first to collect data")
            return False
        
        try:
            self.df = pd.read_csv(self.summary_file)
            self.df['Date'] = pd.to_datetime(self.df['Date'])
            self.df = self.df.sort_values('Date')
            print(f"✓ Loaded {len(self.df)} days of metrics data")
            return True
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False
    
    def create_defect_density_chart(self):
        """Create defect density trend chart"""
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
        
        return fig
    
    def create_violations_chart(self):
        """Create violations trend chart"""
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
        
        return fig
    
    def create_complexity_chart(self):
        """Create complexity trend chart"""
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
        
        # Add threshold line at 10 (recommended max complexity)
        fig.add_hline(y=10, line_dash="dot", line_color="gray", 
                     annotation_text="Recommended Max (10)", row=2, col=1)
        
        fig.update_layout(
            height=600,
            template='plotly_white',
            showlegend=False
        )
        
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Complexity", row=1, col=1)
        fig.update_yaxes(title_text="Complexity", row=2, col=1)
        
        return fig
    
    def create_error_breakdown_chart(self):
        """Create error type breakdown chart"""
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
        
        return fig
    
    def create_code_growth_chart(self):
        """Create code growth chart"""
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
        
        return fig
    
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
        """Save all charts to HTML file"""
        output_file = METRICS_DIR / "metrics_dashboard.html"
        
        charts = []
        charts.append(self.create_defect_density_chart())
        charts.append(self.create_violations_chart())
        charts.append(self.create_complexity_chart())
        charts.append(self.create_error_breakdown_chart())
        charts.append(self.create_code_growth_chart())
        
        # Create HTML with all charts
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Orchestr8r - Software Quality Metrics Dashboard</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
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
                }}
                .footer {{
                    text-align: center;
                    margin-top: 40px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <h1>Orchestr8r - Software Quality Metrics Dashboard</h1>
            <p style="text-align: center; color: #666;">
                Generated: {timestamp}<br>
                Course: CS 8314 - Software Engineering Research
            </p>
            {charts}
            <div class="footer">
                <p>Data collected using Flake8 static analysis</p>
            </div>
        </body>
        </html>
        """.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            charts="\n".join([f'<div class="chart">{chart.to_html(full_html=False, include_plotlyjs=False)}</div>' 
                             for chart in charts])
        )
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"✓ Dashboard saved to: {output_file}")
        print(f"  Open in browser: file://{output_file.absolute()}")

def main():
    """Main execution function"""
    import numpy as np  # Import here for trend line calculation
    
    visualizer = MetricsVisualizer()
    
    if not visualizer.load_data():
        return
    
    # Generate summary statistics
    visualizer.generate_summary_stats()
    
    # Create and save visualizations
    print("Generating visualizations...")
    visualizer.save_all_charts()
    
    print("\n✓ Visualization complete!")

if __name__ == "__main__":
    main()
