import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ChartVisualizer:
    def generate_comparison_charts(self, symbols_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes the screened dictionary metrics and generates Plotly JSON specs.
        Returns a list of plotly figure dictionaries that can be rendered by react-plotly.js.
        """
        charts = []
        if not symbols_data:
            return charts
            
        # Get all numeric keys to chart (skip strings/booleans)
        first_row = symbols_data[0]
        numeric_keys = [k for k in first_row.keys() if k != "nse_symbol" and isinstance(first_row[k], (int, float))]
        
        symbols = [row.get("nse_symbol", "Unknown") for row in symbols_data]
        
        for key in numeric_keys:
            try:
                values = [row.get(key, 0) for row in symbols_data]
                
                fig = px.bar(
                    x=symbols, 
                    y=values,
                    title=f"Comparison: {key.replace('_', ' ').title()}",
                    labels={"x": "Stock", "y": key.replace('_', ' ').title()},
                    template="plotly_dark",
                    color=values,
                    color_continuous_scale="Blues"
                )
                
                fig.update_layout(
                    margin=dict(l=40, r=20, t=50, b=40),
                    paper_bgcolor="rgba(0,0,0,0)", # Transparent background
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white")
                )
                
                # Convert to dict for JSON serialization using Plotly's built-in JSON encoder 
                # to avoid numpy array serialization errors with Pydantic
                import json
                charts.append(json.loads(fig.to_json()))
            except Exception as e:
                logger.error(f"Failed to generate chart for {key}: {e}")
                
        return charts

visualizer = ChartVisualizer()
