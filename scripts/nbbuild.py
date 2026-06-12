#!/usr/bin/env python3
"""Tiny notebook-authoring helper for workshop labs.

Build valid ``.ipynb`` files from simple ``md(...)`` / ``code(...)`` cell lists
using ``nbformat``, so notebook JSON is never hand-written. Per-module generator
scripts (``gen_<module>.py``) import these helpers and call ``write_notebook``.

    from nbbuild import md, code, write_notebook, next_link
    write_notebook(
        "docs/modules/01-intro.ipynb",
        [md("# Intro"), code("print(1)"), md(next_link("02-tools", "M2 · Tools"))],
        kernel_name="my-workshop",
        kernel_display="My Workshop",
    )

Why a helper instead of writing JSON by hand: notebook JSON is verbose and easy
to corrupt; ``nbformat`` guarantees a valid document and stable cell metadata.

CRITICAL — in-notebook cross-links must be DIRECTORY-STYLE, not ``.ipynb``:
MkDocs (with mkdocs-jupyter) serves ``docs/modules/02-tools.ipynb`` at the URL
``/modules/02-tools/``. Unlike Markdown pages, mkdocs-jupyter does NOT rewrite
links inside notebooks — it ships them verbatim. A naive link ``](02-tools.ipynb)``
therefore resolves against the CURRENT page directory as
``/modules/01-intro/02-tools.ipynb`` and 404s. Always link to a sibling module as
``](../02-tools/)``. The ``next_link`` helper below produces the correct form, so
prefer it over hand-written links.
"""

from __future__ import annotations

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook


def md(source: str) -> nbformat.NotebookNode:
    """Return a markdown cell from a source string (trailing newlines trimmed)."""
    return new_markdown_cell(source.rstrip("\n"))


def code(source: str) -> nbformat.NotebookNode:
    """Return a code cell from a source string (no pre-baked outputs)."""
    return new_code_cell(source.rstrip("\n"))


def next_link(target_id: str, label: str, *, arrow: str = "→") -> str:
    """Return a Markdown link to a sibling module using a directory-style URL.

    Args:
        target_id: the sibling module's file stem WITHOUT extension, e.g.
            ``"02-tools"`` for ``docs/modules/02-tools.ipynb``.
        label: human-readable link text, e.g. ``"M2 · Tools & Function Calling"``.
        arrow: leading glyph (default ``→``).

    The produced link is ``[label](../<target_id>/)`` — the directory-style form
    that resolves correctly on the built MkDocs site. See the module docstring for
    why ``.ipynb`` links break.
    """
    return f"{arrow} **[{label}](../{target_id}/)**"


def sibling_link(target_id: str, label: str) -> str:
    """Return a bare directory-style Markdown link to a sibling module page.

    Like :func:`next_link` but without the arrow/bold decoration — use inside
    prose, e.g. ``f"revisit {sibling_link('01-intro', 'M1')}"``.
    """
    return f"[{label}](../{target_id}/)"


def page_link(page_stem: str, label: str) -> str:
    """Return a directory-style link from a module page to a top-level site page.

    Top-level pages (``docs/setup.md``, ``docs/concepts.md``, ``docs/index.md``)
    are served one directory above ``modules/``. From a module page they are
    reached as ``../../setup/``, ``../../concepts/``, and ``../../`` (home).

    Args:
        page_stem: ``"setup"``, ``"concepts"``, or ``"index"`` (home).
        label: link text.
    """
    if page_stem == "index":
        return f"[{label}](../../)"
    return f"[{label}](../../{page_stem}/)"


def write_notebook(
    path: str,
    cells: list,
    *,
    kernel_name: str = "python3",
    kernel_display: str = "Python 3",
    language_version: str = "3.12",
) -> None:
    """Write ``cells`` to ``path`` as an ``.ipynb`` with workshop kernel metadata.

    Args:
        path: output ``.ipynb`` path. Parent directory must already exist.
        cells: list of cells from :func:`md` / :func:`code`.
        kernel_name: Jupyter kernel name participants register/select. Match the
            value used in ``python -m ipykernel install --name <kernel_name>``.
        kernel_display: kernel display name shown in the notebook UI.
        language_version: Python version string recorded in notebook metadata.
    """
    nb = new_notebook(cells=cells)
    nb.metadata.update(
        {
            "kernelspec": {
                "display_name": kernel_display,
                "language": "python",
                "name": kernel_name,
            },
            "language_info": {"name": "python", "version": language_version},
        }
    )
    with open(path, "w", encoding="utf-8") as fh:
        nbformat.write(nb, fh)
    print(f"wrote {path} ({len(cells)} cells)")
