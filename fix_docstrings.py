#!/usr/bin/env python3
"""Quick script to fix common docstring issues."""

import os
import re


def fix_docstring_file(filepath):
    """Fix docstring issues in a single file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Fix D212: Multi-line docstring summary should start at the first line
    # Pattern: """\n    Summary line
    # Should be: """Summary line
    content = re.sub(
        r'"""(\s*\n\s*)([A-Z][^.\n]*)',
        r'"""\2',
        content
    )
    
    # Fix D415: First line should end with a period
    # Find docstring first lines that don't end with punctuation
    def fix_period(match):
        docstring_start = match.group(1)
        first_line = match.group(2)
        rest = match.group(3)
        
        # Add period if first line doesn't end with punctuation
        if not first_line.rstrip().endswith(('.', '!', '?')):
            first_line = first_line.rstrip() + '.'
        
        return f'{docstring_start}{first_line}{rest}'
    
    content = re.sub(
        r'(""")(.*?)(\n.*?""")',
        fix_period,
        content,
        flags=re.DOTALL
    )
    
    # Fix D200: One-line docstring should fit on one line
    # Pattern: """\n    Single line\n    """
    # Should be: """Single line."""
    content = re.sub(
        r'"""\s*\n\s*([^.\n]*[^.\s])\s*\n\s*"""',
        lambda m: f'"""{m.group(1).strip()}.""""' if not m.group(1).strip().endswith(('.', '!', '?')) else f'"""{m.group(1).strip()}."""',
        content
    )
    
    # Fix D205: 1 blank line required between summary line and description
    # Pattern: """Summary\nDescription
    # Should be: """Summary\n\nDescription
    content = re.sub(
        r'("""[^.\n]*[.!?])\n([A-Z][^"""]*""")',
        r'\1\n\n\2',
        content,
        flags=re.DOTALL
    )
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed docstrings in {filepath}")
        return True
    return False


def main():
    """Fix docstrings in all Python files."""
    files_to_fix = [
        'token_manager.py',
        'headless_auth.py', 
        'notification.py',
        'simple_manual_auth.py',
        'clean_auth.py',
        'manual_auth.py',
        'restart_auth.py',
        'setup_headless_auth.py',
        'run_with_headless_auth.py',
        'auth_web_trigger.py',
        'add_headless_support.py'
    ]
    
    fixed_count = 0
    for filename in files_to_fix:
        if os.path.exists(filename):
            if fix_docstring_file(filename):
                fixed_count += 1
        else:
            print(f"File not found: {filename}")
    
    print(f"\nFixed docstrings in {fixed_count} files")


if __name__ == "__main__":
    main()
