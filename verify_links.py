import os
import re
from pathlib import Path

def find_md_files(base_dir):
    return list(Path(base_dir).rglob("*.md"))

def extract_links(md_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match markdown links: [text](url/path)
    # Ignore purely anchor links like [text](#section)
    pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    links = pattern.findall(content)
    
    # Return list of tuples: (text, link)
    valid_links = []
    for text, link in links:
        link = link.strip()
        if link.startswith('#'):
            continue # skip anchor-only within same file
        valid_links.append((text, link))
        
    return valid_links

def verify_links(base_dir):
    md_files = find_md_files(base_dir)
    broken_links = []

    for md_file in md_files:
        links = extract_links(md_file)
        
        for text, link in links:
            if link.startswith('http://') or link.startswith('https://'):
                # We do not strictly verify HTTP links to avoid timeouts/rate limits here, 
                # but we could flag them. I will skip external requests for performance unless explicitly needed
                pass 
            else:
                # Local file link
                
                # remove anchor # from local path if exists
                clean_path = link.split('#')[0]
                if not clean_path:
                    continue # was probably just an anchor
                
                # Check absolute paths to github content
                if clean_path.startswith('/'):
                    # Sometimes researchers link starting from root, wait let's just flag it
                    broken_links.append((md_file, text, link, "Absolute paths usually break in generic viewers"))
                    continue

                # Relative paths
                target_file = (md_file.parent / clean_path).resolve()
                if not target_file.exists():
                    broken_links.append((md_file, text, link, "File does not exist locally"))

    return broken_links

if __name__ == "__main__":
    import sys
    base = os.getcwd()
    broken = verify_links(base)
    
    if not broken:
        print("All local links are structurally valid.")
        sys.exit(0)
    else:
        print(f"Found {len(broken)} broken links:")
        for md_file, text, link, reason in broken:
            rel_file = md_file.relative_to(base)
            print(f"- In {rel_file}: [{text}]({link}) -> {reason}")
        sys.exit(1)

 
