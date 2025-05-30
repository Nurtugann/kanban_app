# main/models.py

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

# -------------------------------------------------------------------
# Статичные справочники
# -------------------------------------------------------------------

REGION_CHOICES = [
    ('KST', 'Костанай'),
    ('AKM', 'Акмола'),
    ('PAV', 'Павлодар'),
    ('KAR', 'Караганда'),
    ('VKO', 'ВКО'),
    ('SKO', 'СКО'),
]


class Status(models.Model):
    """
    Статус для Kanban-доски и истории:
      - name: название
      - order: порядок на доске
      - duration_days: рекомендованное максимальное время в статусе
    """
    name = models.CharField("Название статуса", max_length=50)
    order = models.PositiveIntegerField(
        "Порядок отображения",
        default=0,
        help_text="Чем меньше — тем левее на доске"
    )
    duration_days = models.PositiveIntegerField(
        "Рекомендуемое время (дней)",
        default=0,
        help_text="Рекомендованное количество дней в этом статусе"
    )

    class Meta:
        ordering = ["order"]
        verbose_name = "Статус"
        verbose_name_plural = "Статусы"

    def __str__(self):
        return self.name


# -------------------------------------------------------------------
# Основные модели
# -------------------------------------------------------------------

class Company(models.Model):
    """
    Компания — основной объект, привязанный к пользователю-владельцу.
    Имеет регион (из фиксированного списка), статус и позицию на доске.
    """
    name = models.CharField("Название компании", max_length=200)
    status = models.ForeignKey(
        Status,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="+",
        verbose_name="Текущий статус"
    )
    position = models.IntegerField(
        "Позиция в колонке",
        default=0,
        help_text="Порядок внутри одного статуса на доске"
    )
    region = models.CharField(
        "Регион",
        max_length=3,
        choices=REGION_CHOICES,
        default="KST",
        help_text="Географический регион компании"
    )

    class Meta:
        ordering = ["position"]
        verbose_name = "Компания"
        verbose_name_plural = "Компании"

    def __str__(self):
        return self.name

    def region_display(self):
        return dict(REGION_CHOICES).get(self.region, '—')


class CompanyStatusHistory(models.Model):
    """
    История смены статусов компании.
    Храним момент смены и сам статус.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="history",
        verbose_name="Компания"
    )
    status = models.ForeignKey(
        Status,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Статус"
    )
    changed_at = models.DateTimeField(
        "Дата и время смены",
        default=timezone.now,
        help_text="Когда был установлен этот статус"
    )

    class Meta:
        ordering = ["-changed_at"]
        verbose_name = "Запись истории статусов"
        verbose_name_plural = "История статусов"

    def __str__(self):
        ts = self.changed_at.strftime("%Y-%m-%d %H:%M")
        st = self.status.name if self.status else "Без статуса"
        return f"{self.company.name}: {ts} → {st}"


class Comment(models.Model):
    """
    Комментарий пользователя к компании.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Компания"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Автор"
    )
    text = models.TextField("Текст комментария")
    created_at = models.DateTimeField(
        "Дата создания",
        auto_now_add=True
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"

    def __str__(self):
        return f"Комментарий от {self.author.username} к {self.company.name}"


# -------------------------------------------------------------------
# Профили пользователей
# -------------------------------------------------------------------

User = get_user_model()


class Profile(models.Model):
    """
    Расширение модели User — дополнительное поле region.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Пользователь"
    )
    region = models.CharField(
        "Регион пользователя",
        max_length=3,
        choices=REGION_CHOICES,
        default="KST",
        help_text="Географический регион пользователя"
    )

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return f"Профиль {self.user.username}"


@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    """
    При создании User сразу создаём Profile,
    при каждом save — проверяем, что профиль существует.
    """
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)
