"""Compatibility shim for TTS library on Python 3.9.

Fixes the Python 3.10+ union syntax issue in the bangla dependency.
This patches the bangla package's __init__.py file to use Python 3.9-compatible syntax.
"""
import sys
import os
from pathlib import Path
import importlib.util

# Only patch on Python 3.9
if sys.version_info < (3, 10):
    try:
        # Find the bangla package location using importlib (doesn't actually import)
        spec = importlib.util.find_spec('bangla')
        bangla_init = None
        
        if spec and spec.origin:
            bangla_init = Path(spec.origin)
        else:
            # Fallback: search site-packages
            import site
            for site_pkg in site.getsitepackages():
                potential_path = Path(site_pkg) / 'bangla' / '__init__.py'
                if potential_path.exists():
                    bangla_init = potential_path
                    break
        
        # Patch the file if found and not already patched
        if bangla_init and bangla_init.exists():
            with open(bangla_init, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if needs patching (contains Python 3.10+ syntax)
            needs_patch = 'bool | None' in content or 'int | None' in content or 'str | None' in content or 'float | None' in content
            
            if needs_patch:
                # Patch: Replace Python 3.10+ union syntax with Optional
                patched_content = content
                patched_content = patched_content.replace('bool | None', 'Optional[bool]')
                patched_content = patched_content.replace('int | None', 'Optional[int]')
                patched_content = patched_content.replace('str | None', 'Optional[str]')
                patched_content = patched_content.replace('float | None', 'Optional[float]')
                
                # Check if Optional is already imported
                has_typing_import = 'from typing import' in patched_content
                has_optional_in_typing = 'Optional' in patched_content.split('from typing import')[1].split('\n')[0] if has_typing_import else False
                
                if has_typing_import and not has_optional_in_typing:
                    # Add Optional to existing typing import
                    lines = patched_content.split('\n')
                    for i, line in enumerate(lines):
                        if 'from typing import' in line and 'Optional' not in line:
                            # Add Optional to the import
                            if line.strip().endswith(','):
                                lines[i] = line.rstrip() + ' Optional,'
                            elif '(' in line:  # Multi-line import
                                # Find the closing paren
                                for j in range(i, min(i+10, len(lines))):
                                    if ')' in lines[j]:
                                        lines[j] = lines[j].replace(')', 'Optional, )')
                                        break
                            else:
                                lines[i] = line.rstrip() + ', Optional'
                            break
                    patched_content = '\n'.join(lines)
                elif not has_typing_import:
                    # Add typing import at the top
                    lines = patched_content.split('\n')
                    insert_idx = 0
                    # Find first non-comment, non-empty line
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if stripped and not stripped.startswith('#'):
                            insert_idx = i
                            break
                    lines.insert(insert_idx, 'from typing import Optional')
                    patched_content = '\n'.join(lines)
                
                # Write back only if changed
                if patched_content != content:
                    # Create backup
                    backup_path = bangla_init.with_suffix('.py.bak')
                    if not backup_path.exists():
                        with open(bangla_init, 'r', encoding='utf-8') as f:
                            backup_path.write_text(f.read())
                    
                    # Write patched version
                    with open(bangla_init, 'w', encoding='utf-8') as f:
                        f.write(patched_content)
    except Exception:
        # Silently fail - if patching doesn't work, the original error will surface
        pass
