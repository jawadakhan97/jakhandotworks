#!/usr/bin/env python3
"""
Generate listing pages for newsletter and blog archives.
Scans content directories and creates index.html files with links to all posts.
Tracks which posts have been processed to avoid re-reporting the same items.
"""

import json
import re
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
    print("PyYAML is required. Install with: pip install pyyaml")
    exit(1)

ROOT = Path.cwd()
CONTENT_DIR = ROOT / "src" / "content"
NEWSLETTER_DIR = CONTENT_DIR / "newsletter"
BLOG_DIR = CONTENT_DIR / "blog"
PUBLIC_DIR = ROOT / "public"
STATE_FILE = ROOT / "tools" / ".listings_state.json"


def load_state():
    """Load the state file tracking processed posts."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            pass
    return {"newsletter": [], "blog": []}


def save_state(state):
    """Save the state file."""
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def parse_front_matter(md_path):
    """Parse markdown file and extract front matter."""
    content = md_path.read_text(encoding="utf-8")
    front_match = re.match(r"\A---\s*\n(.*?)\n(?:---|\.\.\.)\s*\n?(.*)\Z", content, re.S)
    if not front_match:
        return {}, ""
    
    try:
        meta = yaml.safe_load(front_match.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    
    return meta, front_match.group(2).strip()


def scan_content_directory(directory, content_type):
    """Scan a content directory and return sorted list of posts."""
    posts = []
    
    if not directory.exists():
        return posts
    
    # Find all numbered directories (e.g., 1_first_newsletter, 2_second_post)
    pattern = re.compile(r"(\d+)_(.+?)/index\.md$")
    
    for md_file in directory.rglob("index.md"):
        # Skip the main index.md
        if md_file.parent == directory:
            continue
        
        rel_path = md_file.relative_to(CONTENT_DIR)
        match = pattern.search(str(rel_path))
        
        if match:
            issue_num = match.group(1)
            slug = match.group(2)
            
            meta, _ = parse_front_matter(md_file)
            
            # Skip drafts
            if meta.get("draft", False) is True:
                continue
            
            title = meta.get("title", f"Issue {issue_num}")
            date = meta.get("date", "")
            
            posts.append({
                "number": issue_num,
                "slug": slug,
                "slug_with_num": f"{issue_num}_{slug}",
                "title": title,
                "date": date,
            })
    
    # Sort by number
    posts.sort(key=lambda x: int(x["number"]))
    return posts


def generate_listing_html(posts, content_type, title, output_depth):
    """Generate HTML listing page."""
    year = datetime.now().year
    
    if content_type == "newsletter":
        item_label = "Issue"
    else:
        item_label = "Post"
    
    items_html = ""
    for post in posts:
        date_str = f" — {post['date']}" if post['date'] else ""
        # Generate relative path based on output depth
        rel_path = "../" * output_depth + post['slug_with_num'] + "/index.html"
        items_html += f'''
        <li class="listing-item">
            <a href="{rel_path}">{post['title']}</a>
            <span class="listing-meta">{item_label} #{post['number']}{date_str}</span>
        </li>'''
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} Archive</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Merriweather:ital,opsz,wght@0,18..144,300..900;1,18..144,300..900&family=Montserrat:ital,wght@0,100..900;1,100..900&family=Playfair+Display:ital,wght@0,400..900;1,400..900&display=swap" rel="stylesheet">
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Merriweather', Georgia, serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 2em;
        }}
        h1 {{
            font-family: 'Playfair Display', Georgia, serif;
            font-size: 2em;
            color: #1a1a1a;
            margin-bottom: 0.5em;
        }}
        .intro {{
            color: #666;
            margin-bottom: 2em;
        }}
        .listing {{
            list-style: none;
            padding: 0;
        }}
        .listing-item {{
            margin: 1.5em 0;
            padding-bottom: 1.5em;
            border-bottom: 1px solid #eee;
        }}
        .listing-item:last-child {{
            border-bottom: none;
        }}
        .listing-item a {{
            font-family: 'Playfair Display', Georgia, serif;
            font-size: 1.3em;
            color: #1a1a1a;
            text-decoration: none;
        }}
        .listing-item a:hover {{
            color: #0066cc;
        }}
        .listing-meta {{
            display: block;
            font-family: 'Montserrat', sans-serif;
            font-size: 0.85em;
            color: #888;
            margin-top: 0.25em;
        }}
        footer {{
            margin-top: 3em;
            padding-top: 1em;
            border-top: 1px solid #ddd;
            font-family: 'Montserrat', sans-serif;
            font-size: 0.75em;
            color: #888;
            text-align: center;
        }}
    </style>
</head>
<body>
    <h1>{title} Archive</h1>
    <p class="intro">Below are all the {content_type}s I've published.{' Subscribe to receive future newsletters directly in your inbox.' if content_type == 'newsletter' else ''}</p>
    <ul class="listing">{items_html}
    </ul>
    <footer>
        <p>&copy; {year} Jawad A. Khan</p>
    </footer>
</body>
</html>'''
    
    return html


def main():
    # Load previous state
    state = load_state()
    
    # Scan newsletters
    newsletters = scan_content_directory(NEWSLETTER_DIR, "newsletter")
    newsletter_ids = [f"{p['number']}_{p['slug']}" for p in newsletters]
    
    # Scan blog posts
    blog_posts = scan_content_directory(BLOG_DIR, "blog")
    blog_ids = [f"{p['number']}_{p['slug']}" for p in blog_posts]
    
    # Determine new items
    new_newsletters = [n for n in newsletters if f"{n['number']}_{n['slug']}" not in state["newsletter"]]
    new_blog_posts = [b for b in blog_posts if f"{b['number']}_{b['slug']}" not in state["blog"]]
    
    # Report findings
    total_newsletters = len(newsletters)
    total_blog_posts = len(blog_posts)
    
    if new_newsletters:
        print(f"Found {len(new_newsletters)} new newsletter(s) (total: {total_newsletters})")
        for n in new_newsletters:
            print(f"  - {n['title']}")
    else:
        print(f"No new newsletters (total: {total_newsletters} already processed)")
    
    if new_blog_posts:
        print(f"Found {len(new_blog_posts)} new blog post(s) (total: {total_blog_posts})")
        for b in new_blog_posts:
            print(f"  - {b['title']}")
    else:
        print(f"No new blog posts (total: {total_blog_posts} already processed)")
    
    # Generate newsletter listing (output_depth=1 since public/newsletter/index.html links to public/newsletter/1_*/index.html)
    newsletter_html = generate_listing_html(newsletters, "newsletter", "Newsletter", output_depth=1)
    newsletter_output = PUBLIC_DIR / "newsletter" / "index.html"
    newsletter_output.parent.mkdir(parents=True, exist_ok=True)
    newsletter_output.write_text(newsletter_html, encoding="utf-8")
    print(f"Generated: {newsletter_output}")
    
    # Generate blog listing (output_depth=1 since public/blog/index.html links to public/blog/1_*/index.html)
    blog_html = generate_listing_html(blog_posts, "blog", "Blog", output_depth=1)
    blog_output = PUBLIC_DIR / "blog" / "index.html"
    blog_output.parent.mkdir(parents=True, exist_ok=True)
    blog_output.write_text(blog_html, encoding="utf-8")
    print(f"Generated: {blog_output}")
    
    # Update state with all current posts
    state["newsletter"] = newsletter_ids
    state["blog"] = blog_ids
    save_state(state)
    
    print("\nListing pages generated successfully!")


if __name__ == "__main__":
    main()
