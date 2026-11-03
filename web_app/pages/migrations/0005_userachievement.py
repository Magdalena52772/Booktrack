from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0004_usernotification"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserAchievement",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("key", models.CharField(max_length=50)),
                ("earned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        db_column="user_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="achievements",
                        to="pages.booktrackuser",
                    ),
                ),
            ],
            options={
                "db_table": "user_achievements",
                "ordering": ("-earned_at", "-id"),
                "unique_together": {("user", "key")},
            },
        ),
    ]
