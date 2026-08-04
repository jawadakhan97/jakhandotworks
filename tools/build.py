#!/usr/bin/env python3
import html
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "PyYAML is required. Install with: python3 -m pip install pyyaml\n"
    )
    sys.exit(1)

ROOT = Path.cwd()
CONTENT = (ROOT / "src" / "content").resolve()
PUBLIC = ROOT / "public"
DEFAULT_TEMPLATE = ROOT / "src" / "templates" / "default.html"
BLOG_TEMPLATE = ROOT / "src" / "templates" / "blog.html"
NEWSLETTER_TEMPLATE = ROOT / "src" / "templates" / "newsletter.html"
LISTINGS_STATE_FILE = ROOT / ".listings_state.json"

# Content directories
NEWSLETTER_DIR = CONTENT / "newsletter"
BLOG_DIR = CONTENT / "blog"

# UPDATED: Point to your static assets folder
ASSETS_SRC = ROOT / "src" / "static" / "assets"

CARD_RE = re.compile(r"\{\{\s*card:\s*([A-Za-z0-9_-]+)\s*\}\}")
FRONT_RE = re.compile(
    r"\A---\s*\n(.*?)\n(?:---|\.\.\.)\s*\n?(.*)\Z",
    re.S,
)


def esc(value):
    return html.escape(str(value), quote=True)


def truthy(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "yes", "on", "1"}


def split_front_matter(text):
    text = text.lstrip("\ufeff")
    match = FRONT_RE.match(text)
    if not match:
        return "", text, False
    return match.group(1), match.group(2), True


def parse_yaml(raw, path):
    try:
        data = yaml.safe_load(raw)
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError as exc:
        sys.stderr.write(f"WARNING: bad YAML in {path}: {exc}\n")
        return {}


def as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def markdown_to_html(text):
    text = str(text).strip()
    if not text:
        return ""
    try:
        proc = subprocess.run(
            ["pandoc", "-f", "markdown", "-t", "html5"],
            input=text.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.decode("utf-8").strip()
    except FileNotFoundError:
        pass
    escaped = esc(text)
    paragraphs = [
        part.strip() for part in re.split(r"\n\s*\n", escaped) if part.strip()
    ]
    return "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)


def get_out_rel(source_path):
    """
    Determines the output path relative to public/.
    Example: src/content/about.md -> about/index.html
    """
    try:
        rel_path = source_path.relative_to(CONTENT)
    except ValueError:
        return Path("index.html")

    out_rel = rel_path.with_suffix(".html")
    if out_rel.name != "index.html":
        out_rel = out_rel.with_suffix("") / "index.html"
    return out_rel


def get_root_prefix(out_rel: Path) -> str:
    """
    Calculates the relative path back to the root based on the OUTPUT file depth.
    Example: public/about/index.html (depth 1) -> ../
    """
    depth = len(out_rel.parts) - 1
    if depth == 0:
        return "./"
    return "../" * depth


def page_url_for(target_source, current_out_rel):
    """Calculates the relative link to another page based on output paths."""
    target_out_rel = get_out_rel(target_source)
    current_dir = current_out_rel.parent
    rel = os.path.relpath(target_out_rel, current_dir)
    return rel.replace(os.sep, "/")


def normalize_url(url, current_out_rel):
    """Normalizes absolute URLs (starting with /) to be relative to the current page."""
    url = str(url)
    if url.startswith("/"):
        return get_root_prefix(current_out_rel) + url.lstrip("/")
    return url


def load_listings_state():
    """Load the state file tracking processed posts."""
    if LISTINGS_STATE_FILE.exists():
        try:
            return json.loads(LISTINGS_STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            pass
    return {"newsletter": [], "blog": []}


def save_listings_state(state):
    """Save the state file."""
    LISTINGS_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


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
        
        rel_path = md_file.relative_to(CONTENT)
        match = pattern.search(str(rel_path))
        
        if match:
            issue_num = match.group(1)
            slug = match.group(2)
            
            meta, _ = split_front_matter(md_file.read_text(encoding="utf-8"))
            try:
                meta = yaml.safe_load(meta) or {}
            except yaml.YAMLError:
                meta = {}
            
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


def render_simple_template(template_text, variables):
    """Simple template renderer for {{ variable }} syntax."""
    result = template_text
    
    # First handle for loops for tags (before single variable replacement)
    if "tags" in variables and variables["tags"]:
        for_pattern = re.compile(r'\{%\s*for\s+tag\s+in\s+tags\s*%\}(.*?)\{%\s*endfor\s*%\}', re.S)
        if for_pattern.search(result):
            items_html = "".join(f'<span class="blog-tag">{esc(tag)}</span>' for tag in variables["tags"])
            result = for_pattern.sub(items_html, result)
    
    # Handle simple if conditions
    if_cond_pattern = re.compile(r"\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}", re.S)
    
    def replace_if(match):
        var_name = match.group(1)
        content = match.group(2)
        if variables.get(var_name):
            return content
        return ""
    
    result = if_cond_pattern.sub(replace_if, result)
    
    # Replace {{ variable }} patterns with regex to handle spacing
    var_pattern = re.compile(r"\{\{\s*(\w+)\s*\}\}")
    
    def replace_var(match):
        var_name = match.group(1)
        if var_name in variables:
            value = variables[var_name]
            # Convert date objects to ISO format string
            if hasattr(value, 'isoformat'):
                return value.isoformat()
            if isinstance(value, (str, int, float)):
                return str(value)
        return match.group(0)  # Keep original if not found
    
    result = var_pattern.sub(replace_var, result)
    
    return result


def generate_listing_items_html(posts, content_type):
    """Generate the HTML list items for a listing page."""
    if content_type == "newsletter":
        item_label = "Issue"
    else:
        item_label = "Post"
    
    items_html = ""
    for post in posts:
        date_str = f" — {post['date']}" if post['date'] else ""
        rel_path = "../" + post['slug_with_num'] + "/index.html"
        items_html += f'''
        <li class="listing-item">
            <a href="{rel_path}">{esc(post['title'])}</a>
            <span class="listing-meta">{item_label} #{post['number']}{date_str}</span>
        </li>'''
    
    return items_html


def build_listing_page(source_path, posts, content_type):
    """Build a listing page by reading the index.md and injecting the listings."""
    raw_yaml, body, has_front = split_front_matter(
        source_path.read_text(encoding="utf-8")
    )
    
    meta = {}
    if has_front:
        try:
            meta = yaml.safe_load(raw_yaml) or {}
        except yaml.YAMLError:
            meta = {}
    
    # Generate the list items
    items_html = generate_listing_items_html(posts, content_type)
    
    # Find the LISTING_START marker and inject items after it
    listing_marker = "<!-- LISTING_START -->"
    if listing_marker in body:
        body = body.replace(listing_marker, listing_marker + "\n\n<ul class=\"listing\">" + items_html + "\n</ul>")
    
    # Build full markdown with front matter
    full_markdown = f"---\n{raw_yaml}\n---\n{body}"
    
    # Use pandoc to render with the default template
    out_rel = get_out_rel(source_path)
    out_path = PUBLIC / out_rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    root_url = get_root_prefix(out_rel)
    
    cmd = [
        "pandoc",
        "-f",
        "markdown+yaml_metadata_block+raw_html",
        "-t",
        "html5",
        "--standalone",
        "--template",
        str(DEFAULT_TEMPLATE),
        "-V",
        f"root_url={root_url}",
        "-o",
        str(out_path),
    ]
    
    proc = subprocess.run(
        cmd, input=full_markdown.encode("utf-8"), capture_output=True
    )
    
    if proc.returncode != 0:
        print(
            f"Error building {source_path}:\n{proc.stderr.decode('utf-8')}",
            file=sys.stderr,
        )
        return None
    else:
        print(f"  -> {out_path.relative_to(ROOT)}")
        return out_path


def build_project_index():
    projects = {}
    if not CONTENT.exists():
        return projects
    for path in sorted(CONTENT.rglob("*.md")):
        raw_yaml, _, has_front = split_front_matter(path.read_text(encoding="utf-8"))
        if not has_front:
            continue
        meta = parse_yaml(raw_yaml, path)
        slug = meta.get("project")
        if slug:
            projects[str(slug)] = (meta, path)
        if path.name == "index.md" and path.parent != CONTENT:
            fallback = path.parent.name
            if fallback and fallback not in projects:
                projects[fallback] = (meta, path)
    return projects


def render_card(slug, projects, current_out_rel):
    if slug not in projects:
        return f"<!-- card '{esc(slug)}' not found -->"

    meta, source_path = projects[slug]
    title = meta.get("title", slug)

    # Collect previews first so placement can be decided.
    previews = []

    if meta.get("preview_url"):
        previews.append(
            {
                "label": meta.get("preview_label", "Play"),
                "url": meta.get("preview_url"),
                "kind": meta.get("preview_kind", "link"),
            }
        )

    if isinstance(meta.get("previews"), list):
        previews.extend(meta.get("previews"))

    previews_html = ""

    if previews:
        parts = ['<div class="previews">']

        for item in previews:
            label = str(item.get("label", "Play"))
            kind = str(item.get("kind", "link")).lower()

            url = (
                page_url_for(source_path, current_out_rel)
                if kind == "page" or not item.get("url")
                else normalize_url(item.get("url"), current_out_rel)
            )

            css_class = "play big" if len(label) > 10 else "play"
            parts.append(f'<a class="{css_class}" href="{esc(url)}">{esc(label)}</a>')

        parts.append("</div>")
        previews_html = "\n".join(parts)

    preview_placement = str(meta.get("preview_placement", "main")).lower()

    image_url = str(meta.get("image") or "").strip()
    has_image = bool(image_url)

    # Only create an aside if there is actually aside content.
    has_aside = has_image or (preview_placement == "aside" and previews_html)

    classes = ["project-entry"]

    if meta.get("card_class"):
        classes.append(str(meta.get("card_class")))
    elif truthy(meta.get("featured")):
        classes.append("featured")

    if has_aside:
        classes.append("has-aside")

    out = [f'<article class="{esc(" ".join(classes))}">']

    # Title block - keep it simple, no wrapper needed
    out.append(f'<h2 class="project-title">{esc(title)}</h2>')

    if meta.get("subtitle"):
        out.append(f'<p class="project-subtitle">{esc(meta.get("subtitle"))}</p>')

    visible_tags = as_list(meta.get("keywords") or meta.get("tags"))
    if visible_tags:
        out.append(
            '<div class="project-tags">'
            + "".join(f'<span class="tag">{esc(t)}</span>' for t in visible_tags)
            + "</div>"
        )

    if meta.get("tagline") or meta.get("byline"):
        out.append(
            f'<p class="project-byline">{esc(meta.get("tagline") or meta.get("byline"))}</p>'
        )

    # Main content block
    out.append('<div class="project-content">')

    if meta.get("landing_description") or meta.get("description"):
        out.append(
            f'<div class="project-body">{markdown_to_html(meta.get("landing_description") or meta.get("description"))}</div>'
        )

    features = meta.get("features")
    if features:
        f_html = (
            "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in features) + "</ul>"
            if isinstance(features, list)
            else markdown_to_html(str(features))
        )
        out.append(f'<div class="project-features"><h3>Key Features</h3>{f_html}</div>')

    # Default: play buttons / previews go in the main column.
    if previews_html and preview_placement != "aside":
        out.append(previews_html)

    out.append("</div>")

    # Aside block, only when needed
    if has_aside:
        out.append('<aside class="project-aside">')

        if has_image:
            if image_url.startswith(("http://", "https://")):
                src = image_url
            elif image_url.startswith("/"):
                src = normalize_url(image_url, current_out_rel)
            else:
                src = get_root_prefix(current_out_rel) + image_url

            out.append(f'<img src="{esc(src)}" alt="{esc(title)}" class="project-image">')

        if previews_html and preview_placement == "aside":
            out.append(previews_html)

        out.append("</aside>")

    out.append("</article>")
    return "\n".join(out)


def build_site():
    # 1. Destroy and recreate the public directory
    if PUBLIC.exists():
        print(f"Cleaning {PUBLIC}...")
        shutil.rmtree(PUBLIC)
    PUBLIC.mkdir()

    # 2. Copy static assets (CSS, images)
    if ASSETS_SRC.exists():
        print(f"Copying assets to {PUBLIC / 'assets'}...")
        # Copies src/static/assets/* -> public/assets/*
        shutil.copytree(ASSETS_SRC, PUBLIC / "assets")
    else:
        print(f"Warning: {ASSETS_SRC} does not exist. Skipping asset copy.")

    # 3. Build pages
    projects = build_project_index()

    # Track newsletters and blog posts for listing generation
    newsletters = []
    blog_posts = []

    for source_path in CONTENT.rglob("*.md"):
        print(f"Building {source_path.relative_to(ROOT)}...")
        raw_yaml, body, has_front = split_front_matter(
            source_path.read_text(encoding="utf-8")
        )

        # Calculate output path once per file
        out_rel = get_out_rel(source_path)
        out_path = PUBLIC / out_rel
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if this is a newsletter or blog post
        rel_path_str = str(source_path.relative_to(CONTENT))
        is_newsletter = rel_path_str.startswith("newsletter/") and source_path.name == "index.md" and source_path.parent != NEWSLETTER_DIR
        is_blog = rel_path_str.startswith("blog/") and source_path.name == "index.md" and source_path.parent != BLOG_DIR

        # Parse front matter for newsletters/blog posts
        meta = {}
        if has_front:
            try:
                meta = yaml.safe_load(raw_yaml) or {}
            except yaml.YAMLError:
                meta = {}

        if is_newsletter or is_blog:
            # Build individual post page using template
            content_type = "newsletter" if is_newsletter else "blog"
            template_path = NEWSLETTER_TEMPLATE if is_newsletter else BLOG_TEMPLATE
            
            # Convert markdown body to HTML
            content_html = markdown_to_html(body)
            
            # Get metadata
            title = meta.get("title", "Untitled")
            date = meta.get("date", datetime.now().strftime("%Y-%m-%d"))
            tags = meta.get("tags", [])
            year = datetime.now().year
            
            # Read template
            template_text = template_path.read_text(encoding="utf-8")
            
            # Render template with variables
            variables = {
                "title": title,
                "date": date,
                "content": content_html,
                "year": year,
                "tags": tags,
                "unsubscribe_url": "{{ unsubscribe_url }}",
            }
            
            rendered_html = render_simple_template(template_text, variables)
            
            # Write the individual post page
            out_path.write_text(rendered_html, encoding="utf-8")
            print(f"  -> {out_path.relative_to(ROOT)}")
            
            # Track for listing
            if is_newsletter:
                dir_name = source_path.parent.name
                match = re.match(r"(\d+)_(.+)", dir_name)
                if match:
                    newsletters.append({
                        "number": match.group(1),
                        "slug": match.group(2),
                        "slug_with_num": dir_name,
                        "title": title,
                        "date": date,
                    })
            else:
                dir_name = source_path.parent.name
                match = re.match(r"(\d+)_(.+)", dir_name)
                if match:
                    blog_posts.append({
                        "number": match.group(1),
                        "slug": match.group(2),
                        "slug_with_num": dir_name,
                        "title": title,
                        "date": date,
                    })
        else:
            # Regular page - use pandoc with default template
            # Pass out_rel to render_card so links are correct relative to the OUTPUT file
            def replace_card(match):
                return "\n\n" + render_card(match.group(1), projects, out_rel) + "\n\n"

            expanded_body = CARD_RE.sub(replace_card, body)
            full_markdown = (
                f"---\n{raw_yaml}\n---\n{expanded_body}" if has_front else expanded_body
            )

            root_url = get_root_prefix(out_rel)

            # Pandoc handles the entire template, including header/footer, and writes directly to disk
            cmd = [
                "pandoc",
                "-f",
                "markdown+yaml_metadata_block+raw_html",
                "-t",
                "html5",
                "--standalone",
                "--template",
                str(DEFAULT_TEMPLATE),
                "-V",
                f"root_url={root_url}",
                "-o",
                str(out_path),
            ]

            proc = subprocess.run(
                cmd, input=full_markdown.encode("utf-8"), capture_output=True
            )

            if proc.returncode != 0:
                print(
                    f"Error building {source_path}:\n{proc.stderr.decode('utf-8')}",
                    file=sys.stderr,
                )
            else:
                print(f"  -> {out_path.relative_to(ROOT)}")

    # Sort newsletters and blog posts by number
    newsletters.sort(key=lambda x: int(x["number"]))
    blog_posts.sort(key=lambda x: int(x["number"]))

    # Load previous state
    state = load_listings_state()
    
    # Determine new items
    newsletter_ids = [f"{n['number']}_{n['slug']}" for n in newsletters]
    blog_ids = [f"{b['number']}_{b['slug']}" for b in blog_posts]
    
    new_newsletters = [n for n in newsletters if f"{n['number']}_{n['slug']}" not in state["newsletter"]]
    new_blog_posts = [b for b in blog_posts if f"{b['number']}_{b['slug']}" not in state["blog"]]
    
    # Report findings
    if new_newsletters:
        print(f"\nFound {len(new_newsletters)} new newsletter(s) (total: {len(newsletters)})")
        for n in new_newsletters:
            print(f"  - {n['title']}")
    else:
        print(f"\nNo new newsletters (total: {len(newsletters)} already processed)")
    
    if new_blog_posts:
        print(f"Found {len(new_blog_posts)} new blog post(s) (total: {len(blog_posts)})")
        for b in new_blog_posts:
            print(f"  - {b['title']}")
    else:
        print(f"No new blog posts (total: {len(blog_posts)} already processed)")

    # Build newsletter listing page from index.md
    newsletter_index_path = NEWSLETTER_DIR / "index.md"
    if newsletter_index_path.exists():
        build_listing_page(newsletter_index_path, newsletters, "newsletter")
    
    # Build blog listing page from index.md
    blog_index_path = BLOG_DIR / "index.md"
    if blog_index_path.exists():
        build_listing_page(blog_index_path, blog_posts, "blog")

    # Update state
    state["newsletter"] = newsletter_ids
    state["blog"] = blog_ids
    save_listings_state(state)


if __name__ == "__main__":
    build_site()
