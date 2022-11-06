# Generated by Django 4.1.2 on 2022-10-30 13:30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TimeBlock",
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
                ("date", models.DateField()),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
            ],
            options={
                "verbose_name": "Блокировка времени",
                "verbose_name_plural": "Блокировки времени",
                "ordering": ("date", "start_time"),
            },
        ),
        migrations.CreateModel(
            name="UserDetail",
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
                ("phone", models.CharField(blank=True, max_length=11, null=True)),
                ("telegram", models.CharField(blank=True, max_length=30, null=True)),
                ("skype", models.CharField(blank=True, max_length=30, null=True)),
                ("discord", models.CharField(blank=True, max_length=30, null=True)),
                ("alias", models.CharField(blank=True, max_length=50, null=True)),
                (
                    "usual_cost",
                    models.IntegerField(blank=True, default=1000, null=True),
                ),
                ("high_cost", models.IntegerField(blank=True, default=1300, null=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="details",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"verbose_name": "Детали", "verbose_name_plural": "Детали",},
        ),
        migrations.CreateModel(
            name="Lesson",
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("salary", models.IntegerField()),
                ("time", models.TimeField()),
                ("date", models.DateField()),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Урок",
                "verbose_name_plural": "Уроки",
                "ordering": ("date", "time"),
            },
        ),
    ]