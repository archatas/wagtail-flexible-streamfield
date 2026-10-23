# wagtail-flexible-streamfield

A Wagtail `StreamField` subclass that doesn't create new migrations when block configurations change.

## Installation

```bash
pip install wagtail-flexible-streamfield
```

Add `wagtail_flexible_streamfield` to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    "wagtail_flexible_streamfield",
]
```

## Usage

Replace `from wagtail.fields import StreamField` with the package's import:

```python
from wagtail_flexible_streamfield.fields import StreamField

class MyPage(Page):
    content = StreamField([
        ("text", CharBlock()),
        ("rich_text", RichTextBlock()),
    ], blank=True)
```

A single migration is created when you first add the field. After that, adding, removing, or modifying blocks never requires a new migration — the field's `deconstruct()` output is always identical regardless of the block configuration.

## How it works

Wagtail's default `StreamField.deconstruct()` records every block definition in the migration file. This package overrides `deconstruct()` to store an empty `block_lookup` instead, so Django's migration autodetector never sees a change when blocks are updated.

`__init__()` is also overridden to accept calls with no block arguments (the form Django uses when reconstructing the field from a migration), and `to_python()` is overridden to return a useful lazy `StreamValue` when block definitions are unavailable at migration time.
