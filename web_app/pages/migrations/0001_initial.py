from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BooktrackUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False)),
                ('username', models.TextField(unique=True)),
                ('email', models.TextField(blank=True, null=True)),
                ('name', models.TextField(blank=True, null=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('date_joined', models.DateTimeField()),
                ('external_id', models.IntegerField(blank=True, null=True, unique=True)),
                ('birth_date', models.DateField()),
                ('status', models.TextField(default='active')),
                ('last_activity', models.DateTimeField(blank=True, null=True)),
                ('r_tier', models.TextField(blank=True, default='regular')),
                ('cluster_group', models.IntegerField(blank=True, null=True)),
                ('books_read', models.IntegerField(default=0)),
                ('pages_per_day', models.FloatField(default=0)),
                ('current_streak', models.IntegerField(default=0)),
            ],
            options={
                'db_table': 'users',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('timestamp', models.DateTimeField()),
                ('pages_read', models.IntegerField(default=0)),
                ('session_minutes', models.IntegerField(default=0)),
            ],
            options={
                'db_table': 'activity',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('title', models.TextField()),
                ('authors', models.TextField(blank=True, null=True)),
                ('openlibrary_id', models.TextField(blank=True, null=True, unique=True)),
                ('total_pages', models.IntegerField(blank=True, null=True)),
                ('added_by_generator', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'books',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Challenge',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('title', models.TextField()),
                ('type', models.TextField()),
                ('target_value', models.IntegerField()),
                ('current_value', models.IntegerField(default=0)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField()),
                ('status', models.TextField(default='active')),
            ],
            options={
                'db_table': 'challenges',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Genre',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.TextField(unique=True)),
                ('readers', models.IntegerField(default=0)),
                ('avg_rating', models.FloatField(default=0)),
                ('books_read', models.IntegerField(default=0)),
                ('reading_time_share', models.FloatField(default=0)),
            ],
            options={
                'db_table': 'genres',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='UserBook',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('current_page', models.IntegerField(default=0)),
                ('status', models.TextField(default='reading')),
                ('rating', models.IntegerField(blank=True, null=True)),
                ('start_date', models.DateTimeField(blank=True, null=True)),
                ('finish_date', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'user_books',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='UserFavoriteGenre',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
            ],
            options={
                'db_table': 'user_favorite_genres',
                'managed': False,
            },
        ),
    ]
