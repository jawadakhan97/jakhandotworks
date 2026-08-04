# Newsletter & Blog Broadcast System

This system automatically broadcasts newsletters and blog posts via the Kit (ConvertKit) API when you commit changes to your content directories.

## Overview

The broadcast system consists of:

1. **`kit_broadcast.py`** - Main Python script that detects commits and sends broadcasts
2. **`git-post-commit-hook.sh`** - Git hook that triggers the broadcast script
3. **`generate_listings.py`** - Generates archive listing pages for newsletters and blogs
4. **Templates** - HTML templates in `src/templates/` for styling emails and posts

## Features

### Draft Control
- Add `draft: true` to front matter to prevent accidental sending
- Only posts with `draft: false` or no draft field will be broadcast

```yaml
---
title: "My Post"
date: 2026-08-05
draft: false  # Set to true to prevent sending
---
```

### Duplicate Prevention
- Tracks sent items in `.kit_sent_log.json`
- Prevents double-sending the same content from the same commit
- Shows skip count in summary output

### Local Testing
- Use `--dry-run` flag to test without sending
- Preview rendered HTML before broadcasting

### Multiple Posts
- Handles multiple newsletter/blog posts in a single commit
- Processes all matching files detected

## Setup

### 1. Install Dependencies

```bash
pip install pyyaml
# Optional: for better markdown conversion
brew install pandoc  # macOS
apt-get install pandoc  # Linux
```

### 2. Set Environment Variables

```bash
export KIT_API_KEY="your_kit_api_key"
export KIT_FORM_ID="your_form_id"
export SITE_URL="https://jakhandotworks.com"
```

Add these to your shell profile (`~/.bashrc`, `~/.zshrc`) for persistence.

### 3. Install Git Hook

```bash
cp tools/git-post-commit-hook.sh .git/hooks/post-commit
chmod +x .git/hooks/post-commit
```

### 4. Test Locally First

Before enabling automatic broadcasts:

```bash
# Test without sending
python tools/kit_broadcast.py --dry-run

# Test specific post types
python tools/kit_broadcast.py --newsletter --dry-run
python tools/kit_broadcast.py --blog --dry-run
```

### 5. Generate Listing Pages

After building your site, generate archive listings:

```bash
python tools/generate_listings.py
```

Or add to your build process.

## Usage

### Automatic Broadcasting

Once the git hook is installed, every commit that modifies files in:
- `src/content/newsletter/NUM_TITLE/index.md`
- `src/content/blog/NUM_TITLE/index.md`

Will trigger an automatic broadcast (if not marked as draft).

### Manual Broadcasting

```bash
# Broadcast all detected changes
python tools/kit_broadcast.py

# Force newsletter mode
python tools/kit_broadcast.py --newsletter

# Force blog mode
python tools/kit_broadcast.py --blog

# Process specific commit
python tools/kit_broadcast.py --commit-hash abc123

# Dry run (no actual sending)
python tools/kit_broadcast.py --dry-run
```

## Content Format

### Newsletter Example

```markdown
---
title: "August Updates"
date: 2026-08-05
draft: false
---

Welcome to this month's newsletter!

Here are the latest updates...
```

### Blog Post Example

```markdown
---
title: "Building a Broadcast System"
date: 2026-08-05
draft: false
tags:
  - development
  - automation
---

Today I'm going to show you how...
```

## Limits & Considerations

### Kit API Limits
- Check your Kit plan for broadcast limits
- Rate limiting may apply for frequent sends
- Form ID must have active subscribers

### Potential Issues

1. **Single-commit repositories**: The first commit may not trigger properly if there's no previous commit to diff against.

2. **Draft detection**: Only checks top-level front matter. Ensure `draft:` is at the top.

3. **Multiple posts in one commit**: All non-draft posts will be sent. Consider separate commits for different broadcasts.

4. **Template rendering**: Templates use simple `{{ variable }}` syntax. Complex logic requires template modification.

5. **Markdown conversion**: Without pandoc, falls back to basic paragraph conversion. Install pandoc for best results.

6. **Git hook failures**: If the script fails, it won't block your commit but broadcasts won't send. Check logs.

### Error Handling

- Missing API key: Script exits with error message
- Invalid form ID: HTTP error returned by Kit API
- Network issues: Caught and reported, script continues

## Benefits

1. **Automated workflow**: Write content, commit, and broadcast automatically
2. **Safety controls**: Draft flag prevents accidental sends
3. **Duplicate protection**: Sent log prevents double-broadcasting
4. **Local testing**: Dry-run mode for preview before sending
5. **Consistent styling**: Templates ensure brand consistency
6. **Archive generation**: Automatic listing pages for published content

## Troubleshooting

### No broadcasts detected
- Verify file path matches pattern: `src/content/newsletter/1_title/index.md`
- Check that `index.md` has valid YAML front matter
- Run with `--dry-run` to see detected files

### Draft posts being sent
- Ensure `draft: false` (not `"false"` as string)
- Check YAML syntax is valid

### Already sent messages appearing
- The sent log is per-commit. Rebasing or amending commits may reset tracking.
- Manually edit `.kit_sent_log.json` if needed

### Template rendering issues
- Verify template files exist in `src/templates/`
- Check variable names match between template and script

## Files

- `tools/kit_broadcast.py` - Main broadcast script
- `tools/generate_listings.py` - Archive page generator
- `tools/git-post-commit-hook.sh` - Git hook installer
- `src/templates/newsletter.html` - Email template
- `src/templates/blog.html` - Blog post template
- `.kit_sent_log.json` - Sent items tracking (auto-generated)

## Support

For Kit API issues, refer to: https://developers.kit.com/v2/
