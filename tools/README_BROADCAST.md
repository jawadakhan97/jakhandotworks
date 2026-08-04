# Newsletter and Blog Broadcast System

This system automatically broadcasts newsletter and blog posts via the Kit (ConvertKit) API when you commit changes to your content files.

## Overview

The system consists of:

1. **`tools/kit_broadcast.py`** - Main Python script that:
   - Detects new/modified newsletter or blog posts from git commits
   - Renders HTML using templates in `src/templates/`
   - Sends broadcast emails via the Kit API

2. **`tools/git-post-commit-hook.sh`** - Git hook script for automatic triggering

3. **Templates**:
   - `src/templates/newsletter.html` - Email newsletter template
   - `src/templates/blog.html` - Blog post template

## File Structure

```
src/content/newsletter/NUM_TITLE/index.md  # Newsletter content
src/content/blog/NUM_TITLE/index.md        # Blog post content
src/templates/newsletter.html              # Newsletter HTML template
src/templates/blog.html                    # Blog HTML template
tools/kit_broadcast.py                     # Broadcast script
tools/git-post-commit-hook.sh              # Git hook script
```

## Content Format

### Newsletter Example (`src/content/newsletter/1_my_newsletter/index.md`)

```markdown
---
title: "My Newsletter Title"
date: 2026-08-05
---

Your newsletter content here in Markdown format.

- Supports lists
- **Bold** and *italic* text
- [Links](https://example.com)
- And more!
```

### Blog Post Example (`src/content/blog/1_my_post/index.md`)

```markdown
---
title: "My Blog Post Title"
date: 2026-08-05
tags:
  - technology
  - programming
---

Your blog post content here in Markdown format.
```

## Setup

### 1. Install Dependencies

```bash
pip install pyyaml
```

Note: For best markdown conversion, also install pandoc:
- macOS: `brew install pandoc`
- Linux: `sudo apt-get install pandoc`
- Windows: Download from https://pandoc.org/installing.html

### 2. Configure Environment Variables

Set these environment variables (add to your `.bashrc`, `.zshrc`, or CI/CD config):

```bash
export KIT_API_KEY="your_kit_api_key_here"
export KIT_FORM_ID="your_subscriber_form_id"
export SITE_URL="https://jakhandotworks.com"
```

### 3. Get Your Kit API Credentials

1. Log into your Kit (ConvertKit) account
2. Go to Settings → Advanced → API Keys
3. Create a new API key
4. Note your Form ID from the Forms section

### 4. Install Git Hook (Optional for Automatic Broadcasting)

To automatically broadcast on every commit:

```bash
# Copy the hook script
cp tools/git-post-commit-hook.sh .git/hooks/post-commit

# Make it executable
chmod +x .git/hooks/post-commit
```

## Usage

### Manual Broadcasting

Run the broadcast script manually:

```bash
# Auto-detect content type from last commit
python tools/kit_broadcast.py

# Force process as newsletter
python tools/kit_broadcast.py --newsletter

# Force process as blog post
python tools/kit_broadcast.py --blog

# Process a specific commit
python tools/kit_broadcast.py --commit-hash abc123

# Test without sending (dry run) - RECOMMENDED BEFORE FIRST USE
python tools/kit_broadcast.py --dry-run

# Combine options
python tools/kit_broadcast.py --newsletter --dry-run
python tools/kit_broadcast.py --blog --commit-hash abc123 --dry-run
```

### Testing Locally (Recommended Before Using Kit API)

**Always test with `--dry-run` first** to see what would be sent without actually sending:

```bash
# Test the most recent commit
python tools/kit_broadcast.py --dry-run

# Test a specific commit
python tools/kit_broadcast.py --commit-hash <hash> --dry-run

# Force test as newsletter or blog
python tools/kit_broadcast.py --newsletter --dry-run
python tools/kit_broadcast.py --blog --dry-run
```

The dry run will show you:
- Which files were detected
- The email subject line
- HTML content length
- A preview of the rendered HTML (first 500 characters)

This is perfect for verifying your templates and content formatting before connecting to the Kit API.

### Automatic Broadcasting (with Git Hook)

Once you've tested and are ready for automatic broadcasting:

1. Set your environment variables:
   ```bash
   export KIT_API_KEY="your_kit_api_key_here"
   export KIT_FORM_ID="your_subscriber_form_id"
   export SITE_URL="https://jakhandotworks.com"
   ```

2. Install the git hook:
   ```bash
   cp tools/git-post-commit-hook.sh .git/hooks/post-commit
   chmod +x .git/hooks/post-commit
   ```

3. Commit your content:
   ```bash
   git add src/content/newsletter/2_my_update/index.md
   git commit -m "Add new newsletter"
   ```

The hook will automatically detect the content and trigger the broadcast.

## Template Variables

### Newsletter Template (`src/templates/newsletter.html`)

- `{{ title }}` - Newsletter title from front matter
- `{{ date }}` - Publication date
- `{{ content }}` - HTML-converted markdown content
- `{{ year }}` - Current year (for copyright)
- `{{ unsubscribe_url }}` - Kit's unsubscribe link placeholder

### Blog Template (`src/templates/blog.html`)

- `{{ title }}` - Blog post title from front matter
- `{{ date }}` - Publication date
- `{{ content }}` - HTML-converted markdown content
- `{{ year }}` - Current year (for copyright)
- `{% if tags %}...{% endif %}` - Conditional tag display

## How It Works

1. **Git Commit**: You commit a new/modified `index.md` file in either:
   - `src/content/newsletter/NUM_TITLE/`
   - `src/content/blog/NUM_TITLE/`

2. **Detection**: The script scans the commit for matching file patterns

3. **Rendering**: 
   - Parses markdown front matter (YAML)
   - Converts markdown body to HTML
   - Fills template with content

4. **Broadcasting**:
   - Creates a broadcast via Kit API v2
   - Sends to your specified form/subscriber list

## Troubleshooting

### "KIT_API_KEY environment variable not set"

Ensure you've exported the environment variable:
```bash
export KIT_API_KEY="your_key"
```

### "pandoc not found"

Install pandoc for better markdown conversion, or the script will use basic paragraph conversion.

### No content detected

Verify your file path matches the pattern:
- `src/content/newsletter/1_slug/index.md`
- `src/content/blog/1_slug/index.md`

The folder name must start with a number followed by an underscore.

## API Reference

The script uses Kit API v2:
- Endpoint: `POST https://api.kit.com/v2/broadcasts`
- Documentation: https://developers.kit.com/v2/reference/create-a-broadcast

## Security Notes

- Never commit your API keys to version control
- Use environment variables or a secrets manager
- The git hook exits with code 0 even on failure to avoid blocking commits
