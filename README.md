# Jawad A. Khan Portfolio Website - Static Site Generator

A static site generator built with Python, Pandoc, and YAML front matter for creating a professional portfolio website with blog and newsletter capabilities.

## Table of Contents

- [Overview](#overview)
- [Directory Structure](#directory-structure)
- [Quick Start](#quick-start)
- [Building the Site](#building-the-site)
- [Content Creation](#content-creation)
  - [Blog Posts](#blog-posts)
  - [Newsletter Issues](#newsletter-issues)
  - [Works/Projects](#worksprojects)
- [Broadcast System (Kit API)](#broadcast-system-kit-api)
  - [Setup](#setup)
  - [Usage](#usage)
  - [How It Works](#how-it-works)
- [Templates](#templates)
- [Styling](#styling)
- [Development Workflow](#development-workflow)
- [Commands Reference](#commands-reference)

## Overview

This static site generator (SSG) creates a portfolio website with the following features:

- **Portfolio/Works Section**: Showcase projects with customizable cards
- **Blog**: Publish articles with automatic archive listing
- **Newsletter**: Send email broadcasts via Kit (ConvertKit) API with web archive
- **Research Log**: Document research and learnings
- **About Page**: Personal information and background
- **Responsive Design**: Mobile-friendly CSS styling
- **Incremental Builds**: Track processed content for faster rebuilds

The system uses:
- **Pandoc**: Markdown to HTML conversion
- **YAML Front Matter**: Metadata for pages and posts
- **Python Build Script**: Orchestrates site generation
- **Kit API**: Email broadcast automation

## Directory Structure

```
/workspace/
├── src/
│   ├── content/              # Markdown source files
│   │   ├── about/            # About page content
│   │   ├── blog/             # Blog posts (numbered directories)
│   │   │   ├── index.md      # Blog archive page
│   │   │   └── 1_first_post/
│   │   │       └── index.md
│   │   ├── newsletter/       # Newsletter issues (numbered directories)
│   │   │   ├── index.md      # Newsletter archive page
│   │   │   └── 1_first_newsletter/
│   │   │       └── index.md
│   │   ├── research-log/     # Research log entries
│   │   └── works/            # Project/portfolio entries
│   ├── static/
│   │   └── assets/
│   │       └── css/
│   │           └── style.css # Main stylesheet
│   └── templates/
│       ├── default.html      # Default page template (includes header/nav)
│       ├── blog.html         # Blog post template
│       ├── newsletter.html   # Newsletter web version template
│       ├── email.html        # Email-specific template (for Kit broadcasts)
│       └── template.html     # Alternative template
├── tools/
│   ├── build.py              # Main build script
│   ├── kit_broadcast.py      # Kit API broadcast automation
│   ├── generate_listings.py  # Generate archive listing pages
│   ├── git-post-commit-hook.sh # Git hook for auto-broadcasting
│   └── README_BROADCAST.md   # Detailed broadcast system documentation
├── public/                   # Generated output (compiled site) - DO NOT EDIT
├── pyproject.toml            # Python project configuration
├── uv.lock                   # Dependency lock file
└── README.md                 # This file
```

## Quick Start

### Prerequisites

1. **Python 3.8+** with `uv` package manager
2. **Pandoc** (https://pandoc.org/installing.html)
3. **Node.js** (optional, for CSS minification)

### Installation

```bash
# Install dependencies using uv
uv sync

# Install pandoc (macOS)
brew install pandoc

# Install pandoc (Linux)
apt-get install pandoc
```

### Build and Serve

```bash
# Build the site
uv run python tools/build.py

# Generate archive listings
uv run python tools/generate_listings.py

# Start local development server
python3 -m http.server 8000

# Or use livereload for auto-refresh
livereload .
```

Visit `http://localhost:8000/public` to view your site.

## Building the Site

### Full Build

Run the main build script to compile all Markdown files to HTML:

```bash
uv run python tools/build.py
```

This script:
1. Scans `src/content/` for all `.md` files
2. Parses YAML front matter for metadata
3. Converts Markdown to HTML using Pandoc
4. Applies templates based on content type
5. Outputs to `public/` directory

### Incremental Builds

The build system tracks processed blog posts and newsletters in `.listings_state.json` to avoid reprocessing unchanged content.

### CSS Minification

```bash
npx clean-css-cli src/static/assets/css/style.css -o src/static/assets/css/style.min.css
```

## Content Creation

### Blog Posts

Create a new blog post in a numbered directory:

```bash
mkdir -p src/content/blog/2_my_second_post
```

Create `src/content/blog/2_my_second_post/index.md`:

```markdown
---
title: "My Second Post"
date: 2026-08-05
draft: false
tags:
  - development
  - tutorial
---

This is the content of my blog post.

## Section Heading

Write your content here using standard Markdown syntax.
```

**Front Matter Fields:**
- `title` (required): Display title
- `date` (optional): Publication date (YYYY-MM-DD)
- `draft` (optional): Set to `true` to prevent publishing/broadcasting
- `tags` (optional): List of tags for categorization

### Newsletter Issues

Create a newsletter issue similarly:

```bash
mkdir -p src/content/newsletter/2_august_updates
```

Create `src/content/newsletter/2_august_updates/index.md`:

```markdown
---
title: "August Updates"
date: 2026-08-05
draft: false
---

Welcome to this month's newsletter!

## What's New

- Project A update
- Project B launch
```

**Important:** Newsletter content has two versions:
1. **Web version**: Displayed on your site (uses `newsletter.html` template)
2. **Email version**: Sent via Kit API (uses `email.html` template with inline CSS)

The broadcast system automatically converts your Markdown to both formats.

### Works/Projects

Create project entries in categorized directories:

```bash
mkdir -p src/content/works/games/my_awesome_game
```

Create `src/content/works/games/my_awesome_game/index.md`:

```markdown
---
title: "My Awesome Game"
project: my_awesome_game
subtitle: "A thrilling adventure"
preview_url: "/path/to/preview.mp4"
preview_image: "/path/to/screenshot.png"
features:
  - Feature one
  - Feature two
---

Project description and details.
```

## Broadcast System (Kit API)

The Kit broadcast system automatically sends newsletters and blog posts to your subscribers when you commit changes.

### Setup

#### 1. Get Kit API Credentials

1. Sign up at [Kit.com](https://www.kit.com)
2. Navigate to Settings → Developer
3. Create an API key
4. Note your Form ID (subscriber list)

#### 2. Configure Environment Variables

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
export KIT_API_KEY="your_api_key_here"
export KIT_FORM_ID="your_form_id_here"
export SITE_URL="https://jakhandotworks.com"
```

Reload your shell:
```bash
source ~/.bashrc  # or source ~/.zshrc
```

#### 3. Install Git Hook

```bash
cp tools/git-post-commit-hook.sh .git/hooks/post-commit
chmod +x .git/hooks/post-commit
```

### Usage

#### Automatic Broadcasting

Once the git hook is installed, every commit that modifies newsletter or blog content will trigger a broadcast (if not marked as draft).

```bash
git add src/content/newsletter/2_august_updates/
git commit -m "Add August newsletter"
# Broadcast automatically sent via Kit API
```

#### Manual Broadcasting

Test before enabling automatic sends:

```bash
# Dry run (preview without sending)
uv run python tools/kit_broadcast.py --dry-run

# Force newsletter mode
uv run python tools/kit_broadcast.py --newsletter

# Force blog mode
uv run python tools/kit_broadcast.py --blog

# Process specific commit
uv run python tools/kit_broadcast.py --commit-hash abc123def

# Actual send (remove --dry-run)
uv run python tools/kit_broadcast.py
```

### How It Works

1. **Detection**: The script detects commits that modify files in `src/content/newsletter/` or `src/content/blog/`
2. **Parsing**: Extracts front matter and Markdown body
3. **Draft Check**: Skips posts with `draft: true`
4. **Duplicate Prevention**: Checks `.kit_sent_log.json` to avoid resending same content
5. **Template Rendering**: 
   - Web version: Uses `newsletter.html` or `blog.html` template
   - Email version: Uses `email.html` template with inline CSS for email clients
6. **API Call**: Sends POST request to Kit API with HTML content
7. **Logging**: Records sent items to prevent duplicates

**Tracking Mechanism:**

The system tracks sent broadcasts in `.kit_sent_log.json`:

```json
{
  "sent_items": [
    {
      "content_type": "newsletter",
      "file_path": "/workspace/src/content/newsletter/1_first_newsletter/index.md",
      "commit_hash": "abc123...",
      "broadcast_id": "12345",
      "sent_at": "2026-08-05T10:30:00"
    }
  ]
}
```

**Email vs Web Styling:**

- **Web Version**: Uses external CSS (`style.css`) for full styling capabilities
- **Email Version**: Uses inline CSS in `<style>` tags for email client compatibility
  - Email clients strip external stylesheets
  - Inline styles ensure consistent rendering across Gmail, Outlook, etc.
  - Simpler layout (single column, max 600px width)

## Templates

### default.html

Base template for most pages. Includes:
- Header with navigation (Home, About, Works, Blog, Newsletter, Research Log)
- Footer with newsletter signup form and webring
- Variable substitution using Pandoc's template syntax (`$variable$`)

### blog.html

Template for individual blog posts. Features:
- Post title and date
- Content area
- Tags display
- Consistent navigation

### newsletter.html

Template for web-viewable newsletter issues. Similar to blog template but optimized for newsletter format.

### email.html

Specialized template for email broadcasts:
- Inline CSS for email client compatibility
- Unsubscribe link placeholder
- Simplified layout
- No JavaScript or external resources

## Styling

The main stylesheet is located at `src/static/assets/css/style.css`.

Key features:
- Responsive design with mobile breakpoints
- Custom typography (Merriweather, Montserrat, Playfair Display fonts)
- Project card grid layouts
- Timeline component for research logs
- Tag styling
- Footer webring integration

To customize:
1. Edit `src/static/assets/css/style.css`
2. Optionally minify: `npx clean-css-cli src/static/assets/css/style.css -o src/static/assets/css/style.min.css`
3. Rebuild site to see changes

## Development Workflow

### Recommended Workflow

1. **Create Content**: Write Markdown files in `src/content/`
2. **Build**: Run `uv run python tools/build.py`
3. **Preview**: Open `public/index.html` in browser or use local server
4. **Test Broadcast**: Use `--dry-run` flag before committing
5. **Commit**: Git commit triggers automatic broadcast (if configured)
6. **Deploy**: Push `public/` directory to your hosting provider

### Testing Locally

```bash
# Terminal 1: Auto-rebuild on changes
watchmedo shell-command -p "*.md" -c "uv run python tools/build.py" -R src/content/

# Terminal 2: Serve and auto-refresh
livereload public/

# Terminal 3: Test broadcast before committing
uv run python tools/kit_broadcast.py --dry-run
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `uv run python tools/build.py` | Build entire site from Markdown to HTML |
| `uv run python tools/generate_listings.py` | Generate blog and newsletter archive pages |
| `uv run python tools/kit_broadcast.py` | Send pending broadcasts via Kit API |
| `uv run python tools/kit_broadcast.py --dry-run` | Preview broadcasts without sending |
| `python3 -m http.server 8000` | Start simple HTTP server for testing |
| `livereload .` | Start auto-refreshing development server |
| `npx clean-css-cli ...` | Minify CSS stylesheet |

## Troubleshooting

### Common Issues

**Pandoc not found:**
```bash
# Install pandoc
brew install pandoc  # macOS
apt-get install pandoc  # Linux
```

**Broadcast not sending:**
- Verify `KIT_API_KEY` and `KIT_FORM_ID` environment variables are set
- Check that post is not marked as `draft: true`
- Review `.kit_sent_log.json` to see if already sent

**Styles not loading:**
- Ensure `root_url` variable is correctly set in templates
- Check that CSS file exists in `public/assets/css/`

**Listing pages empty:**
- Run `uv run python tools/generate_listings.py` after building
- Verify numbered directory format: `1_slug_name/index.md`

## Additional Resources

- [Kit API Documentation](https://developers.kit.com/v2/)
- [Pandoc User Guide](https://pandoc.org/MANUAL.html)
- [Detailed Broadcast Documentation](tools/README_BROADCAST.md)

## License

Source code available at: https://github.com/jawadakhan97/jakhandotworks
