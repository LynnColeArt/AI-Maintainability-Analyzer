import os
import tokenize
from radon.complexity import cc_visit
from pathlib import Path

# Configuration Constants
CLAUDE_TOLERANCES = {
    'python': {
        'complexity_tiers': {
            'simple': 15,
            'safe': 35,
            'complex': 55,
            'danger': 56
        },
        'comment_tiers': {
            'excellent': 25,
            'good': 15,
            'fair': 5,
            'poor': 0
        }
    },
    'config': {
        'size_tiers': {
            'simple': 1000,
            'safe': 2500,
            'complex': 4000,
            'danger': 4001
        }
    }
}

AI_THRESHOLDS = {
    'claude-3.5-sonnet': {
        'python_complexity': 55,
        'config_size_kb': 4000
    },
    'claude-3.5-haiku': {
        'python_complexity': 35,
        'config_size_kb': 2500
    },
    'gpt-4-turbo': {
        'python_complexity': 45,
        'config_size_kb': 3500
    }
}

PYTHON_EXTS = {'.py'}
CONFIG_EXTS = {'.ini', '.cfg', '.conf', '.toml', '.yml', '.yaml', '.json'}

def get_file_size(path):
    """Get file size metrics with error handling"""
    try:
        bytes_size = os.path.getsize(path)
        return {
            'bytes': bytes_size,
            'kb': round(bytes_size / 1024, 1),
            'mb': round(bytes_size / (1024 ** 2), 3)
        }
    except OSError:
        return {'bytes': 0, 'kb': 0, 'mb': 0}

def analyze_comments(file_path):
    """Analyze comment density and quality with error handling"""
    try:
        comment_lines = 0
        total_lines = 0
        has_module_doc = False

        with open(file_path, 'rb') as f:
            tokens = tokenize.tokenize(f.readline)
            for tok in tokens:
                if tok.type == tokenize.COMMENT:
                    comment_lines += 1

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.readlines()
            total_lines = len(content)
            if content:
                has_module_doc = content[0].strip().startswith('"""') or \
                                content[0].strip().startswith("'''")

        density = round((comment_lines / total_lines * 100), 1) if total_lines > 0 else 0
        quality = 'POOR'
        
        for tier, threshold in CLAUDE_TOLERANCES['python']['comment_tiers'].items():
            if density >= threshold:
                quality = tier.upper()
                break

        if total_lines == 0 and has_module_doc:
            quality = 'EXCELLENT'

        return {'comment_density': density, 'comment_quality': quality}
    
    except Exception as e:
        print(f"Comment analysis failed for {file_path}: {str(e)}")
        return {'comment_density': 0, 'comment_quality': 'ERROR'}

def adjust_safety(base_safety, comment_density):
    """Adjust safety rating based on comment quality"""
    safety_order = ['SIMPLE', 'SAFE', 'COMPLEX', 'DANGER']
    try:
        idx = safety_order.index(base_safety)
        if comment_density >= 25:
            return safety_order[max(0, idx-1)]
        elif comment_density < 10:
            return safety_order[min(len(safety_order)-1, idx+1)]
        return base_safety
    except ValueError:
        return base_safety

def get_safety_rating(file_data):
    """Calculate safety rating with fallbacks"""
    try:
        file_type = file_data['type']
        metric = file_data['complexity'] if file_type == 'python' else file_data['size']['kb']
        tiers = CLAUDE_TOLERANCES[file_type]['complexity_tiers' if file_type == 'python' else 'size_tiers']
        
        for rating, threshold in tiers.items():
            if metric <= threshold:
                base_safety = rating.upper()
                break
        else:
            base_safety = 'DANGER'

        if file_type == 'python':
            return adjust_safety(base_safety, file_data.get('comment_density', 0))
        return base_safety
    except KeyError:
        return 'ERROR'

def get_ai_recommendations(file_data):
    """Generate AI recommendations with enhanced safety checks"""
    try:
        recommendations = []
        file_type = file_data.get('type', 'unknown')
        safety = file_data.get('safety', 'ERROR')
        
        if file_type not in ('python', 'config'):
            return ['Human Review']

        for model, specs in AI_THRESHOLDS.items():
            threshold = specs['python_complexity' if file_type == 'python' else 'config_size_kb']
            metric = file_data.get('complexity', 0) if file_type == 'python' else file_data.get('size', {}).get('kb', 0)
            
            if metric <= threshold:
                recommendations.append(model)

        if safety == 'DANGER':
            return ['claude-3.5-sonnet'] if 'claude-3.5-sonnet' in recommendations else []
        elif safety == 'COMPLEX':
            return [m for m in recommendations if m != 'claude-3.5-haiku']
        
        return recommendations
    except Exception:
        return ['Analysis Failed']

def analyze_file(file_path):
    """Robust file analysis with guaranteed type field"""
    try:
        if os.path.basename(file_path) == 'report.py':
            return None

        ext = os.path.splitext(file_path)[1].lower()
        file_type = 'python' if ext in PYTHON_EXTS else 'config' if ext in CONFIG_EXTS else 'other'
        
        if file_type == 'other':
            return None

        result = {
            'path': str(Path(file_path).resolve()),
            'type': file_type,
            'size': get_file_size(file_path),
            'tokens': 0,
            'complexity': 0,
            'comment_density': 0,
            'comment_quality': 'N/A',
            'safety': 'PENDING',
            'recommendations': []
        }

        if file_type == 'python':
            with open(file_path, 'rb') as f:
                result['tokens'] = len(list(tokenize.tokenize(f.readline)))

            with open(file_path, 'r', encoding='utf-8') as f:
                result['complexity'] = sum(func.complexity for func in cc_visit(f.read()))

            comment_data = analyze_comments(file_path)
            result.update(comment_data)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                result['tokens'] = len(content.split())

        result['safety'] = get_safety_rating(result)
        result['recommendations'] = get_ai_recommendations(result)
        return result

    except Exception as e:
        print(f"Critical error analyzing {file_path}: {str(e)}")
        return {
            'path': str(Path(file_path).resolve()),
            'type': 'error',
            'size': {'bytes': 0, 'kb': 0, 'mb': 0},
            'tokens': 0,
            'complexity': 0,
            'comment_density': 0,
            'comment_quality': 'ERROR',
            'safety': 'ANALYSIS FAILED',
            'recommendations': ['Human Review']
        }

def generate_report(files):
    """Generate error-resistant report"""
    valid_files = [f for f in files if f and f.get('type') in ('python', 'config')]
    
    md = [
        "# AI Maintainability Assessment Report",
        "## Analysis Summary",
        "| Path | Type | Size (KB) | Tokens | Complexity | Comments | Safety | Models |",
        "|------|------|-----------|--------|------------|----------|--------|--------|"
    ]
    
    for file in sorted(valid_files, key=lambda x: (-x.get('complexity',0), x['path'])):
        comments = (
            f"{file.get('comment_density', 0)}% ({file.get('comment_quality', 'N/A')})" 
            if file['type'] == 'python' 
            else "N/A"
        )
        
        md.append(
            f"| `{file.get('path', '')}` | "
            f"{file.get('type', 'unknown')} | "
            f"{file.get('size', {}).get('kb', 0)} | "
            f"{file.get('tokens', 0)} | "
            f"{file.get('complexity', 'N/A')} | "
            f"{comments} | "
            f"**{file.get('safety', 'ERROR')}** | "
            f"{' • '.join(file.get('recommendations', ['Human Review']))} |"
        )
    
    md.extend([
        "\n## Safety Rating System",
        "### Python Files:",
        "- **SIMPLE** (≤15 CC): Safe for quick AI edits",
        "- **SAFE** (≤35 CC): Haiku's recommended limit",
        "- **COMPLEX** (≤55 CC): Requires Sonnet",
        "- **DANGER** (>55 CC): Needs human review",
        "",
        "### Config Files:",
        "- **SIMPLE** (≤1MB): Simple key-value changes",
        "- **SAFE** (≤2.5MB): Haiku's size limit",
        "- **COMPLEX** (≤4MB): Needs Sonnet's context",
        "- **DANGER** (>4MB): Potential context issues",
        "",
        "## Comment Impact",
        "- Excellent docs (≥25%) can improve safety rating",
        "- Poor docs (<10%) may worsen safety rating",
        "",
        "*Analysis based on Claude 3.5 capabilities (July 2024)*"
    ])
    
    return '\n'.join(md)

def main():
    """Main execution with enhanced error handling"""
    files = []
    try:
        for root, _, filenames in os.walk('.'):
            for fn in filenames:
                if fn == 'report.py':
                    continue
                
                ext = os.path.splitext(fn)[1].lower()
                if ext in PYTHON_EXTS | CONFIG_EXTS:
                    full_path = os.path.join(root, fn)
                    analysis = analyze_file(full_path)
                    if analysis:
                        files.append(analysis)
        
        report_dir = os.path.join(os.getcwd(), 'foundational')
        os.makedirs(report_dir, exist_ok=True)
        
        report_path = os.path.join(report_dir, 'report.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(generate_report(files))
        
        print(f"Report generated successfully: {report_path}")
    
    except Exception as e:
        print(f"Fatal error during analysis: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()