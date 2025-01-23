# AI Maintainability Analyzer

This utility analyzes Python and configuration files to assess their complexity and readiness for AI assistance. It generates a report with safety ratings and recommended AI models for each file.

## Features

- Calculates cyclomatic complexity for Python files
- Analyzes comment density and quality in Python code
- Determines safety ratings based on complexity and file size
- Recommends appropriate AI models for each file
- Generates a Markdown report with analysis results

## Requirements

- Python 3.6+
- radon library for complexity analysis
- tokenize from Python standard library

Install dependencies:

```bash
pip install radon
```

## Usage

1. Place the `report.py` script in the directory containing your Python and configuration files.
2. Run the script:

```bash
python report.py
```

3. The analysis report will be generated in the `foundational` subdirectory as `report.md`.

## Safety Ratings

### Python Files
- **SIMPLE** (≤15 CC): Safe for quick AI edits
- **SAFE** (≤35 CC): Haiku's recommended limit  
- **COMPLEX** (≤55 CC): Requires Sonnet
- **DANGER** (>55 CC): Needs human review

### Config Files
- **SIMPLE** (≤1MB): Simple key-value changes
- **SAFE** (≤2.5MB): Haiku's size limit
- **COMPLEX** (≤4MB): Needs Sonnet's context
- **DANGER** (>4MB): Potential context issues

## AI Model Recommendations

The script recommends AI models based on the determined safety level and file complexity:

- **claude-3.5-haiku**: Suitable for simple and safe files
- **claude-3.5-sonnet**: Required for complex Python files and large config files
- **gpt-4-turbo**: Considered for mixed-language projects needing cross-file analysis
- **Human Review**: Recommended for files exceeding AI capabilities or with analysis failures

## License

This project is released under the GPL-3.0 License. See [LICENSE](LICENSE) for details.
