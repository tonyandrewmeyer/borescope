#!/usr/bin/env python3
# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Build docs/src/*.md into docs/docs/*.html via Jinja2 + markdown-it-py.

See docs/README.md for the rationale and authoring rules.

Usage:
    uv run python docs/src/_build.py           # rebuild every page
    uv run python docs/src/_build.py --check   # build + diff against committed HTML

The build is intentionally small: markdown body → HTML via markdown-it-py
with the attrs_block plugin (for `## Heading {#anchor}` IDs), wrapped in a
Jinja2 chrome template per section.
"""

from __future__ import annotations

import argparse
import difflib
import html.parser
import json
import pathlib
import re
import sys
import tempfile

import jinja2
import markdown_it
import yaml
from mdit_py_plugins import attrs

DOCS_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC_DIR = DOCS_ROOT / 'src'
OUT_DIR = DOCS_ROOT / 'docs'
TEMPLATES_DIR = SRC_DIR / '_templates'
SITE_CONFIG = SRC_DIR / '_site.yaml'

# Unicode → HTML-entity rewrites applied to the final HTML so the build
# output matches the hand-authored committed HTML byte-for-byte (minus
# intentional formatting changes).  Order matters: ``&`` must already be
# escaped to ``&amp;`` by the markdown renderer before we touch the rest.
ENTITY_REWRITES: tuple[tuple[str, str], ...] = (
    ('—', '&mdash;'),
    ('–', '&ndash;'),
    ('“', '&ldquo;'),
    ('”', '&rdquo;'),
    ('‘', '&lsquo;'),
    ('’', '&rsquo;'),
    ('…', '&hellip;'),
    ('→', '&rarr;'),
    ('≤', '&le;'),
    ('≥', '&ge;'),
    ('≠', '&ne;'),
    ('×', '&times;'),
    (' ', '&nbsp;'),
)


def _load_site() -> dict:
    with SITE_CONFIG.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Split a `---` delimited YAML frontmatter block off the top of `text`."""
    if not text.startswith('---\n'):
        raise ValueError('source file is missing YAML frontmatter')
    end = text.find('\n---\n', 4)
    if end == -1:
        raise ValueError('unterminated YAML frontmatter block')
    meta = yaml.safe_load(text[4:end])
    body = text[end + 5 :].lstrip('\n')
    return meta, body


def _make_md() -> markdown_it.MarkdownIt:
    md = markdown_it.MarkdownIt(
        'commonmark', {'html': True, 'linkify': False, 'typographer': False}
    )
    md.enable('table')
    md = md.use(attrs.attrs_block_plugin)
    md = md.use(attrs.attrs_plugin)
    return md


def _apply_entity_rewrites(text: str) -> str:
    for unicode_ch, entity in ENTITY_REWRITES:
        text = text.replace(unicode_ch, entity)
    return text


_EXTERNAL_LINK_RE = re.compile(
    r'<a href="(https?://[^"]+)"(?![^>]*\btarget=)>',
)


def _mark_external_links(html_text: str) -> str:
    """Add ``target="_blank" rel="noopener"`` to external links.

    Matches any `<a>` with an http(s) href that doesn't already carry a
    target attribute -- the hand-authored style where external links
    consistently open in a new tab.
    """
    return _EXTERNAL_LINK_RE.sub(
        lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener">',
        html_text,
    )


def _build_all_pages_index(site: dict) -> list[dict]:
    """Flat list of every doc page, used to power the Cmd+K palette."""
    entries: list[dict] = [{'slug': 'index', 'label': 'Documentation home', 'section': ''}]
    for section_key, cfg in site['sections'].items():
        label = site['section_breadcrumb_label'].get(section_key, '')
        for page in cfg.get('pages', []):
            entries.append({
                'slug': page['slug'],
                'label': page['label'],
                'section': label,
            })
    return entries


def _render_page(
    src: pathlib.Path,
    site: dict,
    env: jinja2.Environment,
    md: markdown_it.MarkdownIt,
    all_pages: list[dict],
) -> str:
    raw = src.read_text(encoding='utf-8')
    meta, body_md = _split_frontmatter(raw)

    section = meta['section']
    section_cfg = site['sections'].get(section, {})
    section_label = site['section_breadcrumb_label'].get(section, '')

    body_html = md.render(body_md).rstrip()
    body_html = _mark_external_links(body_html)

    layout = meta.get('layout')
    if layout is None:
        layout = 'index' if section == 'index' else 'page'

    template = env.get_template('page.html.j2')
    rendered = template.render(
        title=meta['title'],
        description=meta['description'],
        h1=meta['h1'],
        subtitle=meta['subtitle'],
        slug=meta.get('slug', src.stem),
        section=section,
        section_label=section_label,
        sidebar_heading=section_cfg.get('heading', ''),
        section_pages=section_cfg.get('pages', []),
        breadcrumb_label=meta.get('breadcrumb_label', ''),
        see_also=meta.get('see_also'),
        on_this_page=meta.get('on_this_page'),
        primary_list=meta.get('primary_list', 'section'),
        layout=layout,
        body=body_html,
        all_pages_json=json.dumps(all_pages, separators=(',', ':')),
    )
    return _apply_entity_rewrites(rendered)


def _iter_sources() -> list[pathlib.Path]:
    return sorted(p for p in SRC_DIR.glob('*.md') if not p.name.startswith('_'))


def _build_all(out_dir: pathlib.Path) -> list[tuple[pathlib.Path, str]]:
    site = _load_site()
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        keep_trailing_newline=True,
    )
    md = _make_md()

    all_pages = _build_all_pages_index(site)
    out_dir.mkdir(parents=True, exist_ok=True)
    built: list[tuple[pathlib.Path, str]] = []
    for src in _iter_sources():
        rendered = _render_page(src, site, env, md, all_pages)
        dest = out_dir / f'{src.stem}.html'
        built.append((dest, rendered))
    return built


class _DOMFlatten(html.parser.HTMLParser):
    """Collapse an HTML document into a list of comparable event tuples.

    Each event is a (kind, ...) tuple suitable for structural equality
    comparison.  Whitespace runs inside text nodes are collapsed; entity
    references are resolved so ``&mdash;`` and an em dash compare equal.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.events: list[tuple] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.events.append(('start', tag, tuple(sorted(attrs))))

    def handle_endtag(self, tag: str) -> None:
        self.events.append(('end', tag))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.events.append(('void', tag, tuple(sorted(attrs))))

    def handle_data(self, data: str) -> None:
        normalised = ' '.join(data.split())
        if normalised:
            self.events.append(('text', normalised))


def _flatten_dom(source: str) -> list[tuple]:
    parser = _DOMFlatten()
    parser.feed(source)
    # Coalesce adjacent text runs — they can appear split when inline
    # elements sit flush against text.
    merged: list[tuple] = []
    for event in parser.events:
        if event[0] == 'text' and merged and merged[-1][0] == 'text':
            merged[-1] = ('text', (merged[-1][1] + ' ' + event[1]).strip())
        else:
            merged.append(event)
    return merged


def _check(out_dir: pathlib.Path, semantic: bool) -> int:
    """Build into a temp dir, diff every file against the committed HTML.

    When ``semantic`` is True (default), the diff is DOM-structural: tags,
    attributes, and whitespace-normalised text must match, but source
    formatting (line wrapping, indentation) is tolerated.  This is the check
    that matters for catching content drift.

    When ``semantic`` is False, a literal byte-for-byte diff is performed.
    That's stricter and useful after the committed HTML has been regenerated
    from markdown once.
    """
    mismatches: list[pathlib.Path] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        built = _build_all(tmp_path)
        for dest, rebuilt_html in built:
            rel = dest.relative_to(tmp_path)
            committed = out_dir / rel
            if not committed.exists():
                print(f'[new]       {rel}')
                mismatches.append(rel)
                continue
            existing = committed.read_text(encoding='utf-8')
            if semantic:
                if _flatten_dom(existing) != _flatten_dom(rebuilt_html):
                    mismatches.append(rel)
                    print(f'[differs]   {rel}  (semantic DOM mismatch)')
            else:
                if existing != rebuilt_html:
                    mismatches.append(rel)
                    diff = difflib.unified_diff(
                        existing.splitlines(keepends=True),
                        rebuilt_html.splitlines(keepends=True),
                        fromfile=f'committed/{rel}',
                        tofile=f'rebuilt/{rel}',
                        n=2,
                    )
                    sys.stdout.write(''.join(diff))
                    print(f'[differs]   {rel}')
    if mismatches:
        print(f'\n{len(mismatches)} file(s) differ from committed HTML', file=sys.stderr)
        return 1
    print('docs: rebuilt HTML matches committed output')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--check',
        action='store_true',
        help='Build into a temp dir and diff against committed HTML (semantic DOM).',
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='With --check, require byte-for-byte match instead of semantic DOM.',
    )
    args = parser.parse_args()

    if args.check:
        return _check(OUT_DIR, semantic=not args.strict)

    built = _build_all(OUT_DIR)
    for dest, rendered in built:
        dest.write_text(rendered, encoding='utf-8')
        print(f'wrote {dest.relative_to(DOCS_ROOT.parent)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
