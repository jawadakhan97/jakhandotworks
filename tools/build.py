#!/usr/bin/env python3
import html
import os
import re
import shutil
import subprocess
import sys
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
TEMPLATE = ROOT / "src" / "templates" / "default.html"

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

    # Header block
    out.append('<header class="entry-header">')
    out.append(f'<h2 class="title">{esc(title)}</h2>')

    if meta.get("subtitle"):
        out.append(f'<p class="subtitle">{esc(meta.get("subtitle"))}</p>')

    visible_tags = as_list(meta.get("keywords") or meta.get("tags"))
    if visible_tags:
        out.append(
            '<div class="tags">'
            + "".join(f'<span class="tag">{esc(t)}</span>' for t in visible_tags)
            + "</div>"
        )

    if meta.get("tagline") or meta.get("byline"):
        out.append(
            f'<p class="byline">{esc(meta.get("tagline") or meta.get("byline"))}</p>'
        )

    out.append("</header>")

    # Main block
    out.append('<div class="entry-main">')

    if meta.get("landing_description") or meta.get("description"):
        out.append(
            f'<div class="body">{markdown_to_html(meta.get("landing_description") or meta.get("description"))}</div>'
        )

    features = meta.get("features")
    if features:
        f_html = (
            "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in features) + "</ul>"
            if isinstance(features, list)
            else markdown_to_html(str(features))
        )
        out.append(f'<div class="features"><h3>Key Features</h3>{f_html}</div>')

    # Default: play buttons / previews go in the main column.
    if previews_html and preview_placement != "aside":
        out.append(previews_html)

    out.append("</div>")

    # Aside block, only when needed
    if has_aside:
        out.append('<aside class="entry-aside">')

        if has_image:
            if image_url.startswith(("http://", "https://")):
                src = image_url
            elif image_url.startswith("/"):
                src = normalize_url(image_url, current_out_rel)
            else:
                src = get_root_prefix(current_out_rel) + image_url

            out.append(f'<img src="{esc(src)}" alt="{esc(title)}" class="entry-image">')

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

    for source_path in CONTENT.rglob("*.md"):
        print(f"Building {source_path.relative_to(ROOT)}...")
        raw_yaml, body, has_front = split_front_matter(
            source_path.read_text(encoding="utf-8")
        )

        # Calculate output path once per file
        out_rel = get_out_rel(source_path)
        out_path = PUBLIC / out_rel
        out_path.parent.mkdir(parents=True, exist_ok=True)

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
            str(TEMPLATE),
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


if __name__ == "__main__":
    build_site()
