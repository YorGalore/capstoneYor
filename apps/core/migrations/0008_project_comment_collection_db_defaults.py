from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0007_project_comment_collection")]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="collect_comments",
            field=models.BooleanField(db_default=False, default=False),
        ),
        migrations.AlterField(
            model_name="project",
            name="comment_posts_per_run",
            field=models.PositiveSmallIntegerField(db_default=10, default=10),
        ),
        migrations.AlterField(
            model_name="project",
            name="comments_per_post",
            field=models.PositiveSmallIntegerField(db_default=25, default=25),
        ),
    ]
