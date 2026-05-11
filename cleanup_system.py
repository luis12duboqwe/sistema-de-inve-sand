#!/usr/bin/env python3
"""
Cleanup Script for Sistema de Inventario v2.0
Removes orphaned files, cleans console statements, and validates system
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple

class SystemCleaner:
    def __init__(self):
        self.root = Path('.')
        self.cleaned_files = []
        self.skipped_files = []
        
    def remove_fix_scripts(self) -> Tuple[int, List[str]]:
        """Remove all orphaned fix scripts"""
        print("\n[1/4] Removing orphaned fix scripts...")
        
        patterns = ['fix_*.py', '*.patch', 'fix_*.js', 'fix_*.cjs']
        removed = []
        
        for pattern in patterns:
            for file in self.root.glob(pattern):
                if file.name not in ['.gitignore', 'README.md']:
                    try:
                        file.unlink()
                        removed.append(file.name)
                        print(f"  ✓ Removed: {file.name}")
                    except Exception as e:
                        print(f"  ✗ Error removing {file.name}: {e}")
        
        return len(removed), removed
    
    def clean_console_logs(self, preserve_errors=True) -> Tuple[int, int]:
        """Remove console.log statements from TypeScript files"""
        print("\n[2/4] Cleaning console.log statements...")
        
        if not sys.stdout.isatty():
            # Non-interactive mode - skip
            print("  ⊘ Skipped (non-interactive mode)")
            return 0, 0
        
        response = input("  Remove console.log() statements? (y/n): ").strip().lower()
        if response != 'y':
            print("  ⊘ Skipped")
            return 0, 0
        
        files_modified = 0
        lines_removed = 0
        
        for file in self.root.rglob('*.tsx'):
            if 'node_modules' in str(file) or 'dist' in str(file):
                continue
            
            try:
                content = file.read_text()
                original_count = content.count('console.log(')
                
                # Remove console.log lines but preserve other console methods
                if preserve_errors:
                    lines = content.split('\n')
                    new_lines = []
                    for line in lines:
                        if 'console.log(' not in line:
                            new_lines.append(line)
                    content = '\n'.join(new_lines)
                else:
                    content = re.sub(r'.*console\.log\(.*\n', '', content)
                
                new_count = content.count('console.log(')
                removed = original_count - new_count
                
                if removed > 0:
                    file.write_text(content)
                    self.cleaned_files.append(str(file.relative_to(self.root)))
                    files_modified += 1
                    lines_removed += removed
                    print(f"  ✓ {file.name}: {removed} lines removed")
            except Exception as e:
                print(f"  ✗ Error processing {file.name}: {e}")
        
        return files_modified, lines_removed
    
    def validate_structure(self) -> bool:
        """Validate critical system structure"""
        print("\n[3/4] Validating system structure...")
        
        required_files = [
            'backend/app/models/__init__.py',
            'backend/app/main.py',
            'src/lib/inventoryServiceFactory.ts',
            'src/lib/apiClient.ts',
            'src/lib/inventoryService.ts',
        ]
        
        all_valid = True
        for file_path in required_files:
            file = self.root / file_path
            if file.exists():
                print(f"  ✓ {file_path}")
            else:
                print(f"  ✗ MISSING: {file_path}")
                all_valid = False
        
        return all_valid
    
    def generate_summary(self, fix_removed: int, files_cleaned: int, lines_removed: int):
        """Generate cleanup summary"""
        print("\n[4/4] Summary")
        print("=" * 50)
        print(f"\n  ✓ Fix scripts removed: {fix_removed}")
        print(f"  ✓ Files cleaned: {files_cleaned}")
        print(f"  ✓ Console.log lines removed: {lines_removed}")
        
        if self.cleaned_files:
            print(f"\n  Modified files:")
            for file in self.cleaned_files[:5]:
                print(f"    - {file}")
            if len(self.cleaned_files) > 5:
                print(f"    ... and {len(self.cleaned_files) - 5} more")
        
        print("\n" + "=" * 50)
        print("\nNext steps:")
        print("  1. Review changes: git diff")
        print("  2. Stage: git add -A")
        print("  3. Commit: git commit -m 'cleanup: Remove orphaned files'")
        print("  4. Push: git push origin main")
        print("")

def main():
    try:
        cleaner = SystemCleaner()
        
        fix_removed, removed_list = cleaner.remove_fix_scripts()
        files_cleaned, lines_removed = cleaner.clean_console_logs()
        structure_valid = cleaner.validate_structure()
        
        cleaner.generate_summary(fix_removed, files_cleaned, lines_removed)
        
        if not structure_valid:
            print("\n⚠️  Some required files are missing!")
            return 1
        
        return 0
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
