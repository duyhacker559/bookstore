from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0012_feedback_visibility_flags"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="rating",
            unique_together=set(),
        ),
    ]
