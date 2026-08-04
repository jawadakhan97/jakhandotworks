#!/usr/bin/env python3
"""
Kit API Newsletter/Blog Broadcast System

This script is designed to be called from a git post-commit hook.
It detects new/modified newsletter or blog posts and broadcasts them via the Kit API.

Usage:
    python kit_broadcast.py [--newsletter | --blog] [--commit-hash HASH]

Environment Variables Required:
    KIT_API_KEY: Your Kit (ConvertKit) API key
    KIT_FORM_ID: The form/subscriber list ID for newsletters
    SITE_URL: Base URL of your website (e.g., https://jakhandotworks.com)
"""

import argparse
import html
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML is required. Install with: pip install pyyaml\n")
    sys.exit(1)

# Configuration
ROOT = Path.cwd()
CONTENT_DIR = ROOT / "src" / "content"
NEWSLETTER_DIR = CONTENT_DIR / "newsletter"
BLOG_DIR = CONTENT_DIR / "blog"
NEWSLETTER_TEMPLATE = ROOT / "src" / "templates" / "newsletter.html"
BLOG_TEMPLATE = ROOT / "src" / "templates" / "blog.html"
EMAIL_TEMPLATE = ROOT / "src" / "templates" / "email.html"
SENT_LOG_FILE = ROOT / ".kit_sent_log.json"

# Kit API Configuration
KIT_API_BASE = "https://api.kit.com/v4"


def load_sent_log():
    """Load the sent log from file."""
    if SENT_LOG_FILE.exists():
        try:
            with open(SENT_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError, IOError:
            pass
    return {"sent_items": []}


def save_sent_log(log_data):
    """Save the sent log to file."""
    try:
        with open(SENT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2)
    except IOError as e:
        sys.stderr.write(f"Warning: Could not save sent log: {e}\n")


def is_already_sent(content_type, file_path, commit_hash):
    """Check if this content has already been sent."""
    log_data = load_sent_log()
    file_str = str(file_path)

    for item in log_data.get("sent_items", []):
        if (
            item.get("content_type") == content_type
            and item.get("file_path") == file_str
        ):
            if item.get("commit_hash") == commit_hash:
                return True
    return False


def mark_as_sent(content_type, file_path, commit_hash, broadcast_id=None):
    """Mark content as sent in the log."""
    log_data = load_sent_log()

    log_data["sent_items"].append(
        {
            "content_type": content_type,
            "file_path": str(file_path),
            "commit_hash": commit_hash,
            "broadcast_id": broadcast_id,
            "sent_at": datetime.now().isoformat(),
        }
    )

    save_sent_log(log_data)


def get_current_commit_hash():
    """Get the current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_git_commit_info(commit_hash=None):
    """Get information about the commit."""
    if commit_hash:
        cmd = ["git", "show", "--name-only", "--format=%H%n%s", commit_hash]
    else:
        try:
            cmd = ["git", "rev-parse", "HEAD~1"]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            cmd = ["git", "diff", "--name-only", "HEAD~1", "HEAD"]
        except subprocess.CalledProcessError:
            cmd = ["git", "show", "--name-only", "--format=", "HEAD"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip().split("\n")
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"Error getting commit info: {e}\n")
        return []


def detect_content_type(changed_files, force_type=None):
    """
    Detect if changed files include newsletter or blog posts.
    Returns list of tuples: [(content_type, file_path, issue_number, title, meta), ...]

    If force_type is specified, only look for that content type.
    Only returns items where draft is False or not specified.
    """
    results = []

    if force_type:
        pattern = re.compile(r"src/content/" + force_type + r"/(\d+)_(.+?)/index\.md$")
    else:
        pattern = re.compile(r"src/content/(newsletter|blog)/(\d+)_(.+?)/index\.md$")

    for file_path in changed_files:
        match = pattern.match(file_path)
        if match:
            if force_type:
                content_type = force_type
                issue_num = match.group(1)
                slug = match.group(2)
            else:
                content_type = match.group(1)
                issue_num = match.group(2)
                slug = match.group(3)

            full_path = ROOT / file_path

            if full_path.exists():
                file_content = full_path.read_text(encoding="utf-8")
                front_match = re.match(
                    r"\A---\s*\n(.*?)\n(?:---|\.\.\.)\s*\n?", file_content, re.S
                )
                if front_match:
                    try:
                        meta = yaml.safe_load(front_match.group(1)) or {}

                        if meta.get("draft", False) is True:
                            print(f"  Skipping {file_path}: marked as draft")
                            continue

                        title = meta.get("title", f"Issue {issue_num}")
                        results.append(
                            (content_type, full_path, issue_num, title, meta)
                        )
                    except yaml.YAMLError:
                        results.append(
                            (
                                content_type,
                                full_path,
                                issue_num,
                                f"Issue {issue_num}",
                                {},
                            )
                        )
                else:
                    results.append(
                        (content_type, full_path, issue_num, f"Issue {issue_num}", {})
                    )

    return results


def parse_markdown_content(md_path):
    """Parse markdown file and extract front matter and body."""
    content = md_path.read_text(encoding="utf-8")

    front_match = re.match(
        r"\A---\s*\n(.*?)\n(?:---|\.\.\.)\s*\n?(.*)\Z", content, re.S
    )
    if not front_match:
        return {}, content

    try:
        meta = yaml.safe_load(front_match.group(1)) or {}
    except yaml.YAMLError as e:
        sys.stderr.write(f"Warning: YAML parsing error: {e}\n")
        meta = {}

    body = front_match.group(2).strip()
    return meta, body


def convert_markdown_to_html(markdown_text):
    """Convert markdown to HTML using pandoc."""
    try:
        proc = subprocess.run(
            ["pandoc", "-f", "markdown", "-t", "html5"],
            input=markdown_text.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.decode("utf-8").strip()
    except FileNotFoundError:
        sys.stderr.write("Warning: pandoc not found, using basic conversion\n")

    escaped = html.escape(markdown_text)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", escaped) if p.strip()]
    return "".join(f"<p>{p}</p>" for p in paragraphs)


def render_template(template_path, variables):
    """Simple template renderer for {{ variable }} syntax."""
    template = template_path.read_text(encoding="utf-8")

    for key, value in variables.items():
        if isinstance(value, str):
            template = template.replace("{{ " + key + " }}", value)
        elif isinstance(value, int):
            template = template.replace("{{ " + key + " }}", str(value))

    if_cond_pattern = re.compile(r"\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}", re.S)

    def replace_if(match):
        var_name = match.group(1)
        content = match.group(2)
        if variables.get(var_name):
            return content
        return ""

    template = if_cond_pattern.sub(replace_if, template)

    if "tags" in variables and variables["tags"]:
        tags_html = "".join(
            '<span class="blog-tag">' + html.escape(str(tag)) + "</span>"
            for tag in variables["tags"]
        )

        for_pattern = re.compile(
            r"\{%\s*for\s+tag\s+in\s+tags\s*%\}(.*?)\{%\s*endfor\s*%\}", re.S
        )

        def replace_for(match):
            item_template = match.group(1)
            result = []
            for tag in variables["tags"]:
                item_html = item_template.replace("{{ tag }}", html.escape(str(tag)))
                result.append(item_html)
            return "".join(result)

        template = for_pattern.sub(replace_for, template)

    return template


def build_newsletter_html(meta, body, template_path):
    """Build HTML email content from markdown using email.html template."""
    content_html = convert_markdown_to_html(body)

    variables = {
        "title": meta.get("title", "Newsletter"),
        "date": meta.get("date", datetime.now().strftime("%Y-%m-%d")),
        "content": content_html,
        "year": datetime.now().year,
        "unsubscribe_url": "{{ unsubscribe_url }}",
    }

    return render_template(EMAIL_TEMPLATE, variables)


def build_blog_html(meta, body, template_path):
    """Build HTML blog post content from markdown."""
    content_html = convert_markdown_to_html(body)

    variables = {
        "title": meta.get("title", "Blog Post"),
        "date": meta.get("date", datetime.now().strftime("%Y-%m-%d")),
        "content": content_html,
        "year": datetime.now().year,
        "tags": meta.get("tags", []),
    }

    return render_template(template_path, variables)


def broadcast_to_kit(subject, html_content, subscriber_form_id=None):
    """Send a broadcast email via Kit API."""
    api_key = os.environ.get("KIT_API_KEY")
    if not api_key:
        sys.stderr.write("Error: KIT_API_KEY environment variable not set\n")
        return False

    form_id = subscriber_form_id or os.environ.get("KIT_FORM_ID")
    if not form_id:
        sys.stderr.write("Error: KIT_FORM_ID environment variable not set\n")
        return False

    site_url = os.environ.get("SITE_URL")

    payload = {
        "broadcast": {
            "subject": subject,
            "body_html": html_content,
            "form_ids": [int(form_id)],
            "reply_email": "jawad_khan@outlook.com",
            "sender_email": "jawad_khan@outlook.com",
            "sender_name": "Jawad A. Khan",
        }
    }

    url = f"{KIT_API_BASE}/broadcasts"

    headers = {
        "X-Kit-Api-Key": f"{api_key}",
        "Content-Type": "application/json",
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = Request(url, data=data, headers=headers, method="POST")

        with urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            broadcast_id = result.get("broadcast", {}).get("id")
            print(f"✓ Broadcast created successfully! ID: {broadcast_id}")
            print(f"  Subject: {subject}")
            print(f"  Sent to form: {form_id}")
            return True

    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        sys.stderr.write(f"HTTP Error {e.code}: {e.reason}\n")
        sys.stderr.write(f"Response: {error_body}\n")
        return False
    except URLError as e:
        sys.stderr.write(f"URL Error: {e.reason}\n")
        return False
    except Exception as e:
        sys.stderr.write(f"Error sending broadcast: {e}\n")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Broadcast newsletter/blog posts via Kit API"
    )
    parser.add_argument(
        "--newsletter", action="store_true", help="Force process as newsletter"
    )
    parser.add_argument(
        "--blog", action="store_true", help="Force process as blog post"
    )
    parser.add_argument(
        "--commit-hash", type=str, help="Specific commit hash to process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be sent without actually sending",
    )

    args = parser.parse_args()

    changed_files = get_git_commit_info(args.commit_hash)

    if not changed_files:
        print("No changed files detected or unable to read git history.")
        return 0

    force_type = None
    if args.newsletter:
        force_type = "newsletter"
    elif args.blog:
        force_type = "blog"

    commit_hash = args.commit_hash or get_current_commit_hash()

    results = detect_content_type(changed_files, force_type)

    if not results:
        print("No newsletter or blog post changes detected.")
        print("Changed files:")
        for f in changed_files:
            print(f"  - {f}")
        return 0

    success_count = 0
    fail_count = 0
    skip_count = 0

    for content_type, file_path, issue_num, title, meta in results:
        if is_already_sent(content_type, file_path, commit_hash):
            print(f"\nSkipping {content_type} (already sent):")
            print(f"  File: {file_path}")
            print(f"  Issue: {issue_num}")
            skip_count += 1
            continue

        print(f"\nDetected {content_type} update:")
        print(f"  File: {file_path}")
        print(f"  Issue: {issue_num}")
        print(f"  Title: {title}")

        meta, body = parse_markdown_content(file_path)

        if content_type == "newsletter":
            template_path = NEWSLETTER_TEMPLATE
            html_content = build_newsletter_html(meta, body, template_path)
            subject = f"[Newsletter #{issue_num}] {title}"
        else:
            template_path = BLOG_TEMPLATE
            html_content = build_blog_html(meta, body, template_path)
            subject = f"[Blog] {title}"

        print(f"\nPrepared {content_type}:")
        print(f"  Subject: {subject}")
        print(f"  HTML length: {len(html_content)} characters")

        if args.dry_run:
            print("\n[DRY RUN] Would send to Kit API but skipping...")
            print("\n--- Example Broadcast POST Payload ---")
            print(f"URL: {KIT_API_BASE}/broadcasts")
            print("Method: POST")
            print("Headers:")
            print("  Content-Type: application/json")
            print("  Authorization: Bearer [KIT_API_KEY]")
            print("\nPayload:")
            payload_example = {
                "broadcast": {
                    "subject": subject,
                    "body_html": html_content,
                    "form_ids": [int(form_id)]
                    if (form_id := os.environ.get("KIT_FORM_ID"))
                    else ["YOUR_FORM_ID"],
                    "reply_email": "jawad_khan@outlook.com",
                    "sender_email": "jawad_khan@outlook.com",
                    "sender_name": "Jawad A. Khan",
                }
            }
            print(json.dumps(payload_example, indent=2))
            print("\n--- End Example Payload ---")
            print(f"\nHTML Content Preview (first 500 chars):")
            print(html_content[:500])
            success_count += 1
        else:
            success = broadcast_to_kit(subject, html_content)
            if success:
                broadcast_id = None
                mark_as_sent(content_type, file_path, commit_hash, broadcast_id)
                success_count += 1
            else:
                fail_count += 1

    print(f"\n--- Summary ---")
    print(f"Processed: {success_count + fail_count} item(s)")
    print(f"Successful: {success_count}")
    if skip_count > 0:
        print(f"Skipped (already sent): {skip_count}")
    if fail_count > 0:
        print(f"Failed: {fail_count}")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
