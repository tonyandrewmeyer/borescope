# Documentation source

The borescope docs site is plain Markdown built into static HTML — no docs
framework, no JavaScript build step. The pages follow the
[Diátaxis](https://diataxis.fr/) framework: tutorial, how-to guides, reference,
and explanation.

## Layout

```
docs/
├── index.html          # marketing landing page (hand-authored)
├── style.css           # landing-page styles
├── tokens.css          # shared design tokens (colours, fonts)
├── logo.svg            # theme-neutral logo
├── favicon.svg
├── src/                # Markdown sources — EDIT THESE
│   ├── _build.py       # the build script
│   ├── _site.yaml      # section/page order for the sidebar
│   ├── _templates/     # Jinja2 chrome
│   └── *.md            # one file per page
├── llms.txt            # BUILT OUTPUT — llms.txt index for LLM agents
└── docs/               # BUILT OUTPUT — do not hand-edit
    ├── docs.css
    ├── *.html
    └── *.md            # plain-Markdown companion for each page (linked from llms.txt)
```

## Building

```console
uv run python docs/src/_build.py          # rebuild every page
uv run python docs/src/_build.py --check  # build + diff against committed HTML
tox -e docs                               # the same, via tox
```

The committed HTML under `docs/docs/` is regenerated output, checked in so the
site can be served straight from GitHub Pages. After editing any `src/*.md`,
rebuild and commit both the source and the regenerated HTML. CI runs
`--check` to catch drift.

## Authoring a page

Every source file starts with YAML frontmatter:

```yaml
---
title: "How to … — borescope"   # <title> and browser tab
description: "One-sentence meta description for search engines."
h1: "Page heading"
subtitle: "A sentence under the heading."
section: howto                   # tutorial | howto | reference | explanation
breadcrumb_label: "Page heading"
on_this_page:                    # optional in-page anchor nav
  - { anchor: "first", label: "First section" }
see_also:                        # optional sidebar links
  - { label: "CLI reference", href: "reference-cli.html" }
---
```

Add the page to the matching section in `_site.yaml` so it appears in the
sidebar. Give each `## Heading` an explicit anchor with the `{#anchor}`
attribute block on the line above it, matching the `on_this_page` anchors:

```markdown
{#first}
## First section
```
