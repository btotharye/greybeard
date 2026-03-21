# Batch Review Analysis Dashboard

The batch analysis feature allows you to combine multiple code reviews, aggregate findings, detect patterns, and generate an interactive dashboard with risk visualization.

## Overview

When reviewing multiple files or components, `batch-analyze` helps you:

- **Aggregate** findings from multiple reviews into a single analysis
- **Deduplicate** similar findings across reviews
- **Identify patterns** and recurring issues
- **Visualize risks** with interactive D3.js charts
- **Export results** in multiple formats (HTML, Markdown, JSON)

## Installation

Batch analysis is included with greybeard. No additional installation needed.

## Basic Usage

```bash
greybeard batch-analyze review1.txt review2.txt review3.txt
```

This analyzes three review files and generates an interactive HTML dashboard.

## Output Formats

### HTML Dashboard (Default)

```bash
greybeard batch-analyze *.txt --format html --output analysis.html
```

Generates an interactive dashboard with:
- Risk distribution pie chart (D3.js)
- Risk heatmap by category
- Detected trends and patterns
- All findings with frequency counts
- Recurring findings (consensus issues)
- Responsive design with dark mode support

### Markdown Summary

```bash
greybeard batch-analyze review1.txt review2.txt --format markdown --output report.md
```

Generates a structured markdown report with:
- Executive summary (counts by risk level)
- Detected trends
- Recurring findings
- All findings organized by risk level

### JSON Data Export

```bash
greybeard batch-analyze review*.txt --format json --output data.json
```

Exports raw data for further analysis:
- Metadata (total reviews, timestamp)
- Summary counts
- All findings with details
- Recurring findings
- Detected trends
- Full review data

## Finding Extraction

The analyzer extracts findings from review text using pattern matching. Supported formats:

```
Critical: SQL injection vulnerability
High risk: Missing authentication
Medium: Poor error handling
Low: Inconsistent naming
Info: Consider adding logging

# Also supported with emoji markers:
🔴 Critical: ...
🟠 High: ...
🟡 Medium: ...
🟢 Low: ...
ℹ️ Info: ...
```

## Risk Levels

- **Critical**: Security vulnerabilities, data loss, system crashes
- **High**: Significant issues affecting functionality or security
- **Medium**: Code quality, maintainability, or minor bugs
- **Low**: Style, documentation, minor improvements
- **Info**: Notes, suggestions, discussion points

## Deduplication & Aggregation

The analyzer uses fuzzy matching to identify similar findings across reviews:

```
Review 1: "SQL injection in login form"
Review 2: "SQL injection vulnerability in auth"
→ Deduplicated as: "SQL injection" (frequency: 2)
```

Findings appearing in 2+ reviews are marked as "recurring" and highlighted in the dashboard.

## Trend Detection

Automatically detects:

- **High consensus**: Findings appearing in 50%+ of reviews
- **Critical concentration**: Multiple critical issues
- **Risk categories**: Top risk areas by tag

## CLI Examples

### Single format output
```bash
greybeard batch-analyze file1.txt file2.txt file3.txt
```

### Custom output path
```bash
greybeard batch-analyze *.txt --output reports/batch-analysis.html
```

### Markdown summary for sharing
```bash
greybeard batch-analyze api.txt database.txt ui.txt \
  --format markdown \
  --output findings.md
```

### JSON for programmatic processing
```bash
greybeard batch-analyze reviews/*.txt \
  --format json \
  --output analysis-data.json
```

## Python API

You can also use batch analysis in Python scripts:

```python
from greybeard.batch_analyzer import BatchAnalyzer
from greybeard.reporters.dashboard import DashboardReporter

# Create analyzer
analyzer = BatchAnalyzer()

# Add reviews
analyzer.add_review("api.txt", open("api.txt").read())
analyzer.add_review("db.txt", open("db.txt").read())
analyzer.add_review("ui.txt", open("ui.txt").read())

# Analyze
aggregated = analyzer.analyze()

# Generate dashboard
reporter = DashboardReporter(aggregated)
reporter.save_html("dashboard.html")

# Or export other formats
analyzer.export_markdown("report.md")
analyzer.export_json("data.json")

# Access aggregated data
print(f"Total findings: {aggregated.total_findings}")
print(f"Critical issues: {aggregated.critical_count}")
print(f"Recurring findings: {len(aggregated.recurring_findings)}")
print(f"Trends: {aggregated.trends}")
```

## Data Classes

### Finding

```python
@dataclass
class Finding:
    title: str                    # Finding title
    description: str              # Detailed description
    risk_level: RiskLevel         # critical|high|medium|low|info
    frequency: int = 1            # How many reviews mention it
    sources: list[str] = []       # Which review files
    tags: list[str] = []          # Categorization tags
```

### ReviewSummary

```python
@dataclass
class ReviewSummary:
    source_file: str              # Source file identifier
    review_text: str              # Original review text
    findings: list[Finding] = []  # Extracted findings
    total_risk_score: float = 0.0 # Aggregated risk score
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
```

### AggregatedFindings

```python
@dataclass
class AggregatedFindings:
    findings: list[Finding]       # Deduplicated findings
    total_reviews: int = 0
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    risk_heatmap: dict[str, int]  # tag -> risk count
    recurring_findings: list[Finding]  # 2+ reviews
    trends: list[str]             # Detected patterns
    created_at: str               # ISO timestamp
```

## Deduplication Algorithm

The analyzer uses Jaccard similarity for matching:

```
similarity = |intersection| / |union|
```

Two findings are considered similar if they share:
- 50%+ of their words (default threshold)
- Similar risk level after normalization

Example:
```
"SQL injection in login"     → {sql, injection, in, login}
"SQL injection vulnerability" → {sql, injection, vulnerability}
Intersection: {sql, injection}
Union: {sql, injection, in, login, vulnerability}
Similarity: 2/5 = 0.4 (below 0.5 threshold, but configurable)
```

## Advanced Usage

### Custom Finding Extraction

You can extend the analyzer by implementing custom finding extraction:

```python
from greybeard.batch_analyzer import BatchAnalyzer, Finding

analyzer = BatchAnalyzer()

# Manually add findings
finding = Finding(
    title="Custom Finding",
    description="Manually created",
    risk_level="high",
    sources=["custom.txt"],
    tags=["custom"],
)

review = analyzer.add_review("custom.txt", "Raw review text")
review.findings.append(finding)
```

### Risk Weighting

Findings are weighted for risk scoring:

```python
RISK_WEIGHTS = {
    "critical": 10,
    "high": 5,
    "medium": 2,
    "low": 1,
    "info": 0,
}
```

Total risk score = sum of (finding count × weight) for each finding type.

## Dashboard Features

The interactive HTML dashboard includes:

- **Summary Cards**: Quick overview of risk counts
- **Risk Distribution Pie Chart**: Visual breakdown by risk level
- **Risk Heatmap**: Category-based risk visualization
- **Detected Trends**: Automatically identified patterns
- **All Findings Tab**: Complete list with frequency
- **Recurring Findings Tab**: Consensus issues (2+ reviews)
- **Responsive Design**: Mobile-friendly layout
- **Dark/Light Mode**: Automatic OS preference detection

## Limitations

- Pattern matching is heuristic-based (not 100% accurate)
- Finding extraction works best with structured review text
- Very similar but not identical findings may not deduplicate
- Large review sets (100+ reviews) may have slower performance

## Troubleshooting

### Findings not extracted
- Ensure review text uses recognized risk patterns
- Check capitalization and punctuation
- Use "High risk:" instead of just "High"

### Dashboard not loading
- Check if JavaScript is enabled in browser
- D3.js library loads from CDN (requires internet)
- Try markdown or JSON format instead

### Duplicate findings appearing
- Fuzzy match threshold can be adjusted (default 0.5)
- Manually review similar findings
- Consider normalizing review language

## See Also

- [greybeard CLI](./cli.md)
- [Review Modes](./modes.md)
- [Content Packs](./packs.md)
