from django.db import models
from wagtail.blocks import CharBlock, RichTextBlock

from wagtail_flexible_streamfield.fields import StreamField

CONTENT_BLOCKS = [
    ("text", CharBlock(label="Text")),
    ("rich_text", RichTextBlock(label="Rich Text")),
]


class Article(models.Model):
    title = models.CharField(max_length=255)
    content = StreamField(CONTENT_BLOCKS, blank=True)

    class Meta:
        app_label = "demo_app"

    def __str__(self):
        return self.title
