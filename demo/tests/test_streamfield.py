"""
Unit tests for wagtail-flexible-streamfield.

Covers:
  - fields.py  — StreamField.__init__, deconstruct, to_python
"""

import json

import pytest
from wagtail.blocks import CharBlock, RichTextBlock, StreamBlock


def _simple_blocks():
    return [("text", CharBlock()), ("rich_text", RichTextBlock())]


def _make_field(**kwargs):
    from wagtail_flexible_streamfield.fields import StreamField

    return StreamField(_simple_blocks(), **kwargs)


# ---------------------------------------------------------------------------
# StreamField.__init__
# ---------------------------------------------------------------------------


class TestStreamFieldInit:
    def test_positional_block_types_accepted(self):
        from wagtail_flexible_streamfield.fields import StreamField

        field = StreamField(_simple_blocks())
        assert "text" in field.stream_block.child_blocks
        assert "rich_text" in field.stream_block.child_blocks

    def test_keyword_block_types_accepted(self):
        from wagtail_flexible_streamfield.fields import StreamField

        field = StreamField(block_types=_simple_blocks())
        assert "text" in field.stream_block.child_blocks

    def test_no_args_migration_scenario(self):
        """When called with no block info (as during migration) it must not raise."""
        from wagtail_flexible_streamfield.fields import StreamField

        field = StreamField()
        assert field.stream_block.child_blocks == {}

    def test_block_lookup_kwarg_migration_scenario(self):
        """Migration-reconstructed call: StreamField(block_lookup={}) must not raise."""
        from wagtail_flexible_streamfield.fields import StreamField

        field = StreamField(block_lookup={})
        assert field.stream_block.child_blocks == {}

    def test_none_block_types_treated_as_empty(self):
        from wagtail_flexible_streamfield.fields import StreamField

        field = StreamField(None)
        assert field.stream_block.child_blocks == {}


# ---------------------------------------------------------------------------
# StreamField.deconstruct — migration stability
# ---------------------------------------------------------------------------


class TestStreamFieldDeconstruct:
    def test_block_lookup_not_in_kwargs(self):
        field = _make_field()
        _, _, _, kwargs = field.deconstruct()
        assert "block_lookup" not in kwargs

    def test_block_types_not_in_args(self):
        field = _make_field()
        _, _, args, _ = field.deconstruct()
        assert args == []

    def test_block_types_not_in_kwargs(self):
        field = _make_field()
        _, _, _, kwargs = field.deconstruct()
        assert "block_types" not in kwargs

    def test_verbose_name_not_in_kwargs(self):
        field = _make_field(verbose_name="My content")
        _, _, _, kwargs = field.deconstruct()
        assert "verbose_name" not in kwargs

    def test_deconstruct_output_is_stable_across_different_blocks(self):
        from wagtail_flexible_streamfield.fields import StreamField

        field_a = StreamField([("text", CharBlock())])
        field_b = StreamField([("text", CharBlock()), ("rich_text", RichTextBlock())])

        _, path_a, args_a, kwargs_a = field_a.deconstruct()
        _, path_b, args_b, kwargs_b = field_b.deconstruct()

        assert path_a == path_b
        assert args_a == args_b
        assert kwargs_a == kwargs_b

    def test_blank_kwarg_preserved_in_deconstruct(self):
        from wagtail_flexible_streamfield.fields import StreamField

        field = StreamField(_simple_blocks(), blank=True)
        _, _, _, kwargs = field.deconstruct()
        assert kwargs.get("blank") is True

    def test_deconstruct_path_points_to_package(self):
        field = _make_field()
        _, path, _, _ = field.deconstruct()
        assert path == "wagtail_flexible_streamfield.fields.StreamField"


# ---------------------------------------------------------------------------
# makemigrations simulation — no new migration after block changes
# ---------------------------------------------------------------------------


class TestMakeMigrations:
    def test_adding_blocks_produces_no_new_migration(self):
        """
        Simulates `manage.py makemigrations --check` after a developer adds a
        new block to the StreamField.  The autodetector must report no changes
        because deconstruct() omits all block definitions.
        """
        from django.db import models as django_models
        from django.db.migrations.autodetector import MigrationAutodetector
        from django.db.migrations.loader import MigrationLoader
        from django.db.migrations.questioner import NonInteractiveMigrationQuestioner
        from django.db.migrations.state import ModelState, ProjectState
        from wagtail.blocks import CharBlock, RichTextBlock

        from wagtail_flexible_streamfield.fields import StreamField

        # "Before" — mirrors what 0001_initial stores: StreamField(blank=True)
        state_before = ProjectState()
        state_before.add_model(
            ModelState(
                "demo_app",
                "Article",
                [
                    (
                        "id",
                        django_models.AutoField(
                            auto_created=True,
                            primary_key=True,
                            serialize=False,
                            verbose_name="ID",
                        ),
                    ),
                    ("title", django_models.CharField(max_length=255)),
                    ("content", StreamField(blank=True)),
                ],
                {},
            )
        )

        # "After" — developer added RichTextBlock to the field definition
        state_after = ProjectState()
        state_after.add_model(
            ModelState(
                "demo_app",
                "Article",
                [
                    (
                        "id",
                        django_models.AutoField(
                            auto_created=True,
                            primary_key=True,
                            serialize=False,
                            verbose_name="ID",
                        ),
                    ),
                    ("title", django_models.CharField(max_length=255)),
                    (
                        "content",
                        StreamField(
                            [
                                ("text", CharBlock()),
                                ("rich_text", RichTextBlock()),
                            ],
                            blank=True,
                        ),
                    ),
                ],
                {},
            )
        )

        # MigrationLoader(None) is exactly what `manage.py makemigrations` uses
        loader = MigrationLoader(None, ignore_no_migrations=True)
        autodetector = MigrationAutodetector(
            state_before,
            state_after,
            NonInteractiveMigrationQuestioner(),
        )
        changes = autodetector.changes(graph=loader.graph)

        assert "demo_app" not in changes, (
            f"Expected no migration after adding a block, but got: {changes}"
        )


# ---------------------------------------------------------------------------
# StreamField.to_python — migration lazy-loading
# ---------------------------------------------------------------------------


class TestStreamFieldToPython:
    def test_returns_stream_value_for_json_string(self):
        from wagtail.blocks import StreamValue

        field = _make_field()
        data = json.dumps([{"type": "text", "value": "hello", "id": "abc"}])
        result = field.to_python(data)
        assert isinstance(result, StreamValue)

    def test_returns_stream_value_for_list(self):
        from wagtail.blocks import StreamValue

        field = _make_field()
        data = [{"type": "text", "value": "hello", "id": "abc"}]
        result = field.to_python(data)
        assert isinstance(result, StreamValue)

    def test_migration_scenario_empty_blocks_json_string(self):
        """
        When the field has no blocks (migration context) and a JSON string is
        provided, to_python() should return a lazy StreamValue rather than an
        empty one.
        """
        from wagtail.blocks import StreamValue
        from wagtail_flexible_streamfield.fields import StreamField

        field = StreamField(block_lookup={})
        raw = json.dumps([{"type": "text", "value": "hello", "id": "abc"}])
        result = field.to_python(raw)
        assert isinstance(result, StreamValue)
        assert result._raw_data is not None or result.is_lazy

    def test_migration_scenario_empty_blocks_list(self):
        """
        When the field has no blocks (migration context) and a list is
        provided, to_python() should return a lazy StreamValue.
        """
        from wagtail.blocks import StreamValue
        from wagtail_flexible_streamfield.fields import StreamField

        field = StreamField(block_lookup={})
        data = [{"type": "text", "value": "hello", "id": "abc"}]
        result = field.to_python(data)
        assert isinstance(result, StreamValue)

    def test_empty_value_returns_empty_stream_value(self):
        from wagtail.blocks import StreamValue

        field = _make_field()
        result = field.to_python("")
        assert isinstance(result, StreamValue)

    def test_none_value_returns_empty_stream_value(self):
        from wagtail.blocks import StreamValue

        field = _make_field()
        result = field.to_python(None)
        assert isinstance(result, StreamValue)
