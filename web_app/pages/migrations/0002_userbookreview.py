from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserBookReview",
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
                (
                    "comment",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "user_book",
                    models.OneToOneField(
                        db_column="user_book_id",
                        on_delete=models.deletion.CASCADE,
                        related_name="review",
                        to="pages.userbook",
                    ),
                ),
            ],
            options={
                "db_table": "user_book_reviews",
            },
        ),
    ]
