import os
import re
from pathlib import Path

EXCLUDE_DIRS = {'.git', '__pycache__', '.pytest_cache', 'venv', 'env', '.venv', 'dist', 'build', '.idea', '.vscode'}
SKIP_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.exe', '.dll', '.so', '.dylib', 
    '.pyc', '.pyd', '.db', '.sqlite', '.sqlite3', '.pdf', '.pptx', '.bin', '.pkl', '.zip', '.tar', '.gz'
}

def transform_content(content: str, filepath: str) -> tuple[str, int]:
    changes = 0
    
    # 1. Protect physical workspace disk path
    preserved = []
    def preserve_disk(m):
        preserved.append(m.group(0))
        return f"___PRESERVED_DISK_{len(preserved)-1}___"
    
    # Matches any path containing scratch/orvix_sphere with any slash or escaped slash
    disk_pattern = re.compile(r'([A-Za-z]:[\\/][^"\'\r\n]*?[\\/]scratch(?:\\\\|\\|/)orvix_sphere|scratch(?:\\\\|\\|/)orvix_sphere)', re.IGNORECASE)
    content = disk_pattern.sub(preserve_disk, content)
    
    # 2. Rebrand Identifiers (no dots)
    # Python classes: OrvixFoo -> PHASSFoo
    content, c = re.subn(r'\bOrvix([A-Z][a-zA-Z0-9_]*)', r'PHASS\1', content)
    changes += c
    
    # Constants: ORVIX_FOO -> PHASS_FOO
    content, c = re.subn(r'\bORVIX_([a-zA-Z0-9_]+)', r'PHASS_\1', content)
    changes += c
    
    # Modules/vars: orvix_foo -> phass_foo
    content, c = re.subn(r'\borvix_([a-zA-Z0-9_]+)', r'phass_\1', content)
    changes += c
    
    # Kebab-case: orvix-foo -> phass-foo
    content, c = re.subn(r'\borvix-([a-zA-Z0-9_]+)', r'phass-\1', content)
    changes += c
    
    # 3. Rebrand compound phrases (with dots or spaces)
    content, c = re.subn(r'\bORVIX\s+SPHERE\b', 'P.H.A.S.S SPHERE', content)
    changes += c
    content, c = re.subn(r'\bOrvix\s+Sphere\b', 'P.H.A.S.S Sphere', content)
    changes += c
    content, c = re.subn(r'\borvix\s+sphere\b', 'P.H.A.S.S Sphere', content)
    changes += c

    # 4. Rebrand standalone names
    # ORVIX -> P.H.A.S.S
    content, c = re.subn(r'\bORVIX\b', 'P.H.A.S.S', content)
    changes += c
    # Orvix -> P.H.A.S.S
    content, c = re.subn(r'\bOrvix\b', 'P.H.A.S.S', content)
    changes += c
    # orvix -> phass
    content, c = re.subn(r'\borvix\b', 'phass', content)
    changes += c

    # 5. Restore protected disk paths
    for idx, orig in enumerate(preserved):
        content = content.replace(f"___PRESERVED_DISK_{idx}___", orig)
        
    return content, changes

def run():
    modified_files = []
    total_changes = 0
    
    for dirpath, dirnames, filenames in os.walk('.'):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith('.')]
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in SKIP_EXTENSIONS:
                continue
            filepath = os.path.join(dirpath, f)
            if 'scratch' in filepath and ('rebrand.py' in filepath or 'test_transform.py' in filepath):
                continue
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as fp:
                    orig_content = fp.read()
                
                new_content, c = transform_content(orig_content, filepath)
                if c > 0 and new_content != orig_content:
                    with open(filepath, 'w', encoding='utf-8') as fp:
                        fp.write(new_content)
                    modified_files.append((filepath, c))
                    total_changes += c
            except Exception as e:
                print(f"Error processing {filepath}: {e}")
                
    print(f"Rebranding complete! Modified {len(modified_files)} files with {total_changes} total replacements.")
    for fp, cnt in modified_files[:30]:
        print(f"  {fp}: {cnt} replacements")
    if len(modified_files) > 30:
        print(f"  ... and {len(modified_files)-30} more files.")

if __name__ == '__main__':
    run()
