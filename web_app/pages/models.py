from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class BooktrackUserManager(BaseUserManager):
    """Menedżer custom user modelu korzystającego z tabeli panelu administracyjnego."""

    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("The username must be set.")
        if not extra_fields.get("birth_date"):
            raise ValueError("The birth_date must be set.")

        user = self.model(
            username=username,
            email=self.normalize_email(email),
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("A superuser must have is_superuser=True.")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("A superuser must have is_staff=True.")

        return self.create_user(username, email, password, **extra_fields)


class BooktrackUser(AbstractBaseUser):
    """Custom user Django odwzorowany na tabelę ``users`` panelu.

    Tabela już istnieje i jest zasilana przez aplikację PySide6, dlatego
    Django nie może tworzyć jej ani zmieniać przez migracje.
    """

    is_superuser = models.BooleanField(default=False)
    username = models.TextField(unique=True)
    email = models.TextField(null=True, blank=True)
    name = models.TextField(null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField()
    external_id = models.IntegerField(unique=True, null=True, blank=True)
    birth_date = models.DateField()
    status = models.TextField(default="active")
    last_activity = models.DateTimeField(null=True, blank=True)
    r_tier = models.TextField(default="regular", blank=True)
    cluster_group = models.IntegerField(null=True, blank=True)
    books_read = models.IntegerField(default=0)
    pages_per_day = models.FloatField(default=0)
    current_streak = models.IntegerField(default=0)

    objects = BooktrackUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "birth_date"]

    class Meta:
        managed = False
        db_table = "users"

    def get_full_name(self):
        return self.name or self.username

    def get_short_name(self):
        return self.username


class Genre(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField(unique=True)
    readers = models.IntegerField(default=0)
    avg_rating = models.FloatField(default=0)
    books_read = models.IntegerField(default=0)
    reading_time_share = models.FloatField(default=0)

    class Meta:
        managed = False
        db_table = "genres"


class UserFavoriteGenre(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        BooktrackUser,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="favorite_genre_links",
    )
    genre = models.ForeignKey(
        Genre,
        on_delete=models.CASCADE,
        db_column="genre_id",
        related_name="user_links",
    )

    class Meta:
        managed = False
        db_table = "user_favorite_genres"
        unique_together = (("user", "genre"),)


class Book(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.TextField()
    authors = models.TextField(null=True, blank=True)
    openlibrary_id = models.TextField(unique=True, null=True, blank=True)
    genre = models.ForeignKey(
        Genre, on_delete=models.DO_NOTHING, db_column="genre_id", null=True, blank=True
    )
    total_pages = models.IntegerField(null=True, blank=True)
    added_by_generator = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "books"


class UserBook(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        BooktrackUser,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="user_books",
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, db_column="book_id", related_name="book_users"
    )
    current_page = models.IntegerField(default=0)
    status = models.TextField(default="reading")
    rating = models.IntegerField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    finish_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "user_books"
        unique_together = (("user", "book"),)


class Activity(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        BooktrackUser,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="activities",
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, db_column="book_id", related_name="activities"
    )
    timestamp = models.DateTimeField()
    pages_read = models.IntegerField(default=0)
    session_minutes = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = "activity"


class Challenge(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        BooktrackUser,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="challenges",
    )
    title = models.TextField()
    type = models.TextField()
    target_value = models.IntegerField()
    current_value = models.IntegerField(default=0)
    genre = models.ForeignKey(
        Genre, on_delete=models.DO_NOTHING, db_column="genre_id", null=True, blank=True
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField()
    status = models.TextField(default="active")

    class Meta:
        managed = False
        db_table = "challenges"
