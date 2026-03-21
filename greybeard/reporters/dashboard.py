"""Dashboard reporter for batch review analysis with D3.js visualization.

Generates an interactive HTML dashboard with:
  - Risk heatmap visualization
  - Findings trend analysis
  - Cross-review comparison
  - Responsive design with dark mode support
  - D3.js for interactive charts
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from greybeard.batch_analyzer import AggregatedFindings, BatchAnalyzer

D3_RISK_HEATMAP_SCRIPT = """
// Risk heatmap visualization
const heatmapData = {heatmap_data};
const margin = {{top: 20, right: 20, bottom: 100, left: 60}};
const width = 960 - margin.left - margin.right;
const height = 400 - margin.top - margin.bottom;

const svg = d3.select("#heatmap")
  .attr("width", width + margin.left + margin.right)
  .attr("height", height + margin.top + margin.bottom)
  .append("g")
  .attr("transform", `translate(${{margin.left}},${{margin.top}})`);

// Scale
const xScale = d3.scaleBand()
  .domain(Object.keys(heatmapData))
  .range([0, width])
  .padding(0.1);

const maxValue = Math.max(...Object.values(heatmapData));
const yScale = d3.scaleLinear()
  .domain([0, maxValue])
  .range([height, 0]);

const colorScale = d3.scaleLinear()
  .domain([0, maxValue / 2, maxValue])
  .range(["#90EE90", "#FFD700", "#FF4444"]);

// Bars
svg.selectAll(".bar")
  .data(Object.entries(heatmapData))
  .enter()
  .append("rect")
  .attr("class", "bar")
  .attr("x", d => xScale(d[0]))
  .attr("y", d => yScale(d[1]))
  .attr("width", xScale.bandwidth())
  .attr("height", d => height - yScale(d[1]))
  .attr("fill", d => colorScale(d[1]))
  .on("mouseover", function(d) {{
    d3.select(this).attr("fill-opacity", 0.7);
  }})
  .on("mouseout", function(d) {{
    d3.select(this).attr("fill-opacity", 1);
  }});

// X axis
svg.append("g")
  .attr("transform", `translate(0,${{height}})`)
  .call(d3.axisBottom(xScale))
  .selectAll("text")
  .attr("transform", "rotate(-45)")
  .style("text-anchor", "end");

// Y axis
svg.append("g")
  .call(d3.axisLeft(yScale));

// Labels
svg.append("text")
  .attr("x", width / 2)
  .attr("y", height + 60)
  .style("text-anchor", "middle")
  .text("Risk Category");

svg.append("text")
  .attr("transform", "rotate(-90)")
  .attr("y", 0 - margin.left)
  .attr("x", 0 - height / 2)
  .attr("dy", "1em")
  .style("text-anchor", "middle")
  .text("Risk Score");
"""

D3_RISK_DISTRIBUTION_SCRIPT = """
// Risk distribution pie chart
const riskData = {risk_data};
const pieWidth = 400;
const pieHeight = 300;
const pieMargin = 40;
const pieRadius = Math.min(pieWidth, pieHeight) / 2 - pieMargin;

const pieSvg = d3.select("#risk-distribution")
  .attr("width", pieWidth)
  .attr("height", pieHeight)
  .append("g")
  .attr("transform", `translate(${{pieWidth/2}},${{pieHeight/2}})`);

const pie = d3.pie()
  .value(d => d.value);

const arc = d3.arc()
  .innerRadius(0)
  .outerRadius(pieRadius);

const colors = {{
  critical: "#FF4444",
  high: "#FF8C00",
  medium: "#FFD700",
  low: "#90EE90",
  info: "#87CEEB"
}};

pieSvg.selectAll(".arc")
  .data(pie(riskData))
  .enter()
  .append("g")
  .attr("class", "arc")
  .append("path")
  .attr("d", arc)
  .attr("fill", d => colors[d.data.label])
  .on("mouseover", function() {{
    d3.select(this).attr("opacity", 0.7);
  }})
  .on("mouseout", function() {{
    d3.select(this).attr("opacity", 1);
  }});

// Labels
pieSvg.selectAll(".arc")
  .append("text")
  .attr("transform", d => `translate(${{arc.centroid(d)}})`)
  .attr("text-anchor", "middle")
  .text(d => `${{d.data.label}}: ${{d.data.value}}`);
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Batch Review Analysis Dashboard</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0f1419;
            color: #e0e0e0;
            line-height: 1.6;
        }}
        
        header {{
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a8c 100%);
            padding: 2rem;
            border-bottom: 2px solid #ff6b6b;
        }}
        
        h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}
        
        .subtitle {{
            color: #a0a0a0;
            font-size: 0.9rem;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }}
        
        .summary-card {{
            background: #1a1f2e;
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 4px solid #ff6b6b;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }}
        
        .summary-card.critical {{
            border-left-color: #ff4444;
        }}
        
        .summary-card.high {{
            border-left-color: #ff8c00;
        }}
        
        .summary-card.medium {{
            border-left-color: #ffd700;
        }}
        
        .summary-card.low {{
            border-left-color: #90ee90;
        }}
        
        .summary-card.info {{
            border-left-color: #87ceeb;
        }}
        
        .summary-label {{
            color: #a0a0a0;
            font-size: 0.85rem;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .summary-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #fff;
        }}
        
        .section {{
            background: #1a1f2e;
            padding: 2rem;
            border-radius: 8px;
            margin-bottom: 2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }}
        
        .section h2 {{
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #ff6b6b;
        }}
        
        .chart-container {{
            display: flex;
            justify-content: center;
            margin: 2rem 0;
            overflow-x: auto;
        }}
        
        svg {{
            background: #0f1419;
            border-radius: 4px;
        }}
        
        .findings-list {{
            list-style: none;
        }}
        
        .finding-item {{
            padding: 1rem;
            margin-bottom: 1rem;
            background: #0f1419;
            border-left: 4px solid #ff6b6b;
            border-radius: 4px;
            transition: all 0.2s ease;
        }}
        
        .finding-item:hover {{
            transform: translateX(4px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        }}
        
        .finding-item.critical {{ border-left-color: #ff4444; }}
        .finding-item.high {{ border-left-color: #ff8c00; }}
        .finding-item.medium {{ border-left-color: #ffd700; }}
        .finding-item.low {{ border-left-color: #90ee90; }}
        .finding-item.info {{ border-left-color: #87ceeb; }}
        
        .finding-title {{
            font-weight: bold;
            font-size: 1.1rem;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .finding-badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: bold;
            text-transform: uppercase;
        }}
        
        .finding-badge.critical {{ background: #ff4444; color: white; }}
        .finding-badge.high {{ background: #ff8c00; color: white; }}
        .finding-badge.medium {{ background: #ffd700; color: black; }}
        .finding-badge.low {{ background: #90ee90; color: black; }}
        .finding-badge.info {{ background: #87ceeb; color: black; }}
        
        .finding-desc {{
            color: #b0b0b0;
            font-size: 0.95rem;
            margin-bottom: 0.5rem;
        }}
        
        .finding-meta {{
            display: flex;
            gap: 1rem;
            font-size: 0.85rem;
            color: #808080;
        }}
        
        .trends-list {{
            list-style: none;
        }}
        
        .trend-item {{
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            background: #0f1419;
            border-left: 3px solid #87ceeb;
            border-radius: 4px;
            font-size: 0.95rem;
        }}
        
        .tabs {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid #333;
        }}
        
        .tab {{
            padding: 0.75rem 1.5rem;
            cursor: pointer;
            border: none;
            background: none;
            color: #a0a0a0;
            font-size: 1rem;
            border-bottom: 2px solid transparent;
            transition: all 0.2s ease;
        }}
        
        .tab:hover {{
            color: #fff;
        }}
        
        .tab.active {{
            color: #ff6b6b;
            border-bottom-color: #ff6b6b;
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        footer {{
            text-align: center;
            padding: 2rem;
            color: #606060;
            border-top: 1px solid #333;
            margin-top: 3rem;
        }}
        
        @media (prefers-color-scheme: light) {{
            body {{
                background: #f5f5f5;
                color: #333;
            }}
            
            .section {{
                background: #fff;
                border: 1px solid #ddd;
            }}
            
            .section h2 {{
                border-bottom-color: #ff6b6b;
            }}
            
            .finding-item {{
                background: #f9f9f9;
            }}
            
            .trend-item {{
                background: #f9f9f9;
            }}
            
            svg {{
                background: #f5f5f5;
            }}
            
            header {{
                background: linear-gradient(135deg, #4a7ba7 0%, #6fa3d1 100%);
            }}
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}
            
            .summary {{
                grid-template-columns: 1fr 1fr;
            }}
            
            .section {{
                padding: 1rem;
            }}
            
            svg {{
                max-width: 100%;
                height: auto;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>📊 Batch Review Analysis Dashboard</h1>
        <p class="subtitle">Generated on {timestamp}</p>
    </header>
    
    <div class="container">
        <!-- Summary Cards -->
        <div class="summary">
            <div class="summary-card critical">
                <div class="summary-label">Critical</div>
                <div class="summary-value">{critical}</div>
            </div>
            <div class="summary-card high">
                <div class="summary-label">High</div>
                <div class="summary-value">{high}</div>
            </div>
            <div class="summary-card medium">
                <div class="summary-label">Medium</div>
                <div class="summary-value">{medium}</div>
            </div>
            <div class="summary-card low">
                <div class="summary-label">Low</div>
                <div class="summary-value">{low}</div>
            </div>
            <div class="summary-card info">
                <div class="summary-label">Info</div>
                <div class="summary-value">{info}</div>
            </div>
            <div class="summary-card critical">
                <div class="summary-label">Total Reviews</div>
                <div class="summary-value">{total_reviews}</div>
            </div>
        </div>
        
        <!-- Risk Distribution -->
        <div class="section">
            <h2>Risk Distribution</h2>
            <div class="chart-container">
                <svg id="risk-distribution"></svg>
            </div>
        </div>
        
        <!-- Risk Heatmap -->
        {heatmap_section}
        
        <!-- Trends -->
        {trends_section}
        
        <!-- Findings -->
        <div class="section">
            <h2>All Findings</h2>
            <div class="tabs">
                <button class="tab active" onclick="switchTab(event, 'all-findings')">All ({total_findings})</button>
                <button class="tab" onclick="switchTab(event, 'recurring-findings')">Recurring ({recurring_count})</button>
            </div>
            
            <div id="all-findings" class="tab-content active">
                <ul class="findings-list">
                    {all_findings}
                </ul>
            </div>
            
            <div id="recurring-findings" class="tab-content">
                <ul class="findings-list">
                    {recurring_findings}
                </ul>
            </div>
        </div>
    </div>
    
    <footer>
        <p>Greybeard Batch Review Analysis &copy; {year}</p>
    </footer>
    
    <script>
        function switchTab(evt, tabName) {{
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) {{
                tabcontent[i].classList.remove("active");
            }}
            tablinks = document.getElementsByClassName("tab");
            for (i = 0; i < tablinks.length; i++) {{
                tablinks[i].classList.remove("active");
            }}
            document.getElementById(tabName).classList.add("active");
            evt.currentTarget.classList.add("active");
        }}
        
        {d3_scripts}
    </script>
</body>
</html>
"""


class DashboardReporter:
    """Generate interactive HTML dashboards from batch analysis results."""

    def __init__(self, aggregated: AggregatedFindings | BatchAnalyzer) -> None:
        """Initialize the dashboard reporter.

        Args:
            aggregated: AggregatedFindings or BatchAnalyzer instance.
        """
        if isinstance(aggregated, BatchAnalyzer):
            self.aggregated = aggregated.analyze()
        else:
            self.aggregated = aggregated

    def render_html(self) -> str:
        """Render the dashboard as HTML.

        Returns:
            Complete HTML document string.
        """
        from datetime import UTC, datetime

        timestamp = datetime.now(UTC).isoformat()
        year = datetime.now(UTC).year

        # Build heatmap section
        heatmap_section = ""
        if self.aggregated.risk_heatmap:
            heatmap_html = f"""
        <div class="section">
            <h2>Risk Heatmap by Category</h2>
            <div class="chart-container">
                <svg id="heatmap"></svg>
            </div>
        </div>
        """
            heatmap_section = heatmap_html

        # Build trends section
        trends_section = ""
        if self.aggregated.trends:
            trends_html = """
        <div class="section">
            <h2>Detected Trends</h2>
            <ul class="trends-list">
        """
            for trend in self.aggregated.trends:
                trends_html += f'            <li class="trend-item">{self._escape_html(trend)}</li>\n'
            trends_html += "            </ul>\n        </div>"
            trends_section = trends_html

        # Build findings list
        all_findings_html = ""
        for finding in self.aggregated.findings:
            all_findings_html += self._render_finding_item(finding)

        # Build recurring findings list
        recurring_findings_html = ""
        if self.aggregated.recurring_findings:
            for finding in self.aggregated.recurring_findings:
                recurring_findings_html += self._render_finding_item(finding, show_frequency=True)
        else:
            recurring_findings_html = '<li style="padding: 1rem; color: #808080;">No recurring findings</li>'

        # Prepare D3 scripts
        d3_scripts = self._build_d3_scripts()

        # Format risk data for pie chart
        risk_data = [
            {"label": "critical", "value": self.aggregated.critical_count},
            {"label": "high", "value": self.aggregated.high_count},
            {"label": "medium", "value": self.aggregated.medium_count},
            {"label": "low", "value": self.aggregated.low_count},
            {"label": "info", "value": self.aggregated.info_count},
        ]

        html = HTML_TEMPLATE.format(
            timestamp=timestamp,
            critical=self.aggregated.critical_count,
            high=self.aggregated.high_count,
            medium=self.aggregated.medium_count,
            low=self.aggregated.low_count,
            info=self.aggregated.info_count,
            total_reviews=self.aggregated.total_reviews,
            total_findings=self.aggregated.total_findings,
            recurring_count=len(self.aggregated.recurring_findings),
            heatmap_section=heatmap_section,
            trends_section=trends_section,
            all_findings=all_findings_html,
            recurring_findings=recurring_findings_html,
            year=year,
            d3_scripts=d3_scripts,
        )

        # Inject risk data
        risk_data_json = json.dumps(risk_data)
        html = html.replace('const riskData = {risk_data};', f'const riskData = {risk_data_json};')

        # Inject heatmap data if present
        if self.aggregated.risk_heatmap:
            heatmap_data_json = json.dumps(self.aggregated.risk_heatmap)
            html = html.replace(
                'const heatmapData = {heatmap_data};',
                f'const heatmapData = {heatmap_data_json};',
            )

        return html

    def _render_finding_item(self, finding: Any, show_frequency: bool = False) -> str:
        """Render a single finding as HTML."""
        sources = ", ".join(finding.sources[:2])
        if len(finding.sources) > 2:
            sources += f", +{len(finding.sources) - 2} more"

        freq_text = ""
        if show_frequency:
            freq_text = f' <span style="font-size: 0.85rem; color: #a0a0a0;">(Found in {finding.frequency} reviews)</span>'

        return f"""                    <li class="finding-item {finding.risk_level}">
                        <div class="finding-title">
                            {self._escape_html(finding.title)}{freq_text}
                            <span class="finding-badge {finding.risk_level}">{finding.risk_level}</span>
                        </div>
                        {f'<div class="finding-desc">{self._escape_html(finding.description)}</div>' if finding.description else ''}
                        <div class="finding-meta">
                            <span>📁 {self._escape_html(sources)}</span>
                            <span>🔁 {finding.frequency}x</span>
                        </div>
                    </li>
"""

    def _build_d3_scripts(self) -> str:
        """Build D3.js visualization scripts."""
        scripts = D3_RISK_DISTRIBUTION_SCRIPT

        if self.aggregated.risk_heatmap:
            scripts += "\n" + D3_RISK_HEATMAP_SCRIPT

        return scripts

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def save_html(self, path: str | Path) -> None:
        """Save the dashboard to an HTML file.

        Args:
            path: Output file path.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        html = self.render_html()
        path.write_text(html)
