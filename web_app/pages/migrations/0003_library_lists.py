from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pages", "0002_userbookreview")]

    operations = [
        migrations.CreateModel(
            name="UserFavoriteBook",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("book", models.ForeignKey(db_column="book_id", on_delete=models.deletion.CASCADE, related_name="favorite_book_links", to="pages.book")),
                ("user", models.ForeignKey(db_column="user_id", on_delete=models.deletion.CASCADE, related_name="favorite_book_links", to="pages.booktrackuser")),
            ],
            options={"db_table": "user_favorite_books", "unique_together": {("user", "book")}},
        ),
        migrations.CreateModel(
            name="UserReadingQueue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("book", models.ForeignKey(db_column="book_id", on_delete=models.deletion.CASCADE, related_name="reading_queue_links", to="pages.book")),
                ("user", models.ForeignKey(db_column="user_id", on_delete=models.deletion.CASCADE, related_name="reading_queue_links", to="pages.booktrackuser")),
            ],
            options={"db_table": "user_reading_queue", "unique_together": {("user", "book")}},
        ),
    ]
