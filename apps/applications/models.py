from django.contrib.auth import get_user_model
from django.db import models

from apps.common.models import BaseModel
from .validators import (phone_validator, telegram_validator,
                         portfolio_validator, validate_resume)

User = get_user_model()


class Region(BaseModel):
    title = models.CharField(max_length=255, unique=True, verbose_name="Nomi")

    class Meta:
        verbose_name = "Viloyat"
        verbose_name_plural = "Viloyatlar"
        ordering = ['title']

    def __str__(self):
        return self.title


class Direction(BaseModel):
    title = models.CharField(max_length=255, unique=True, verbose_name="Nomi")

    class Meta:
        verbose_name = "Yo'nalish"
        verbose_name_plural = "Yo'nalishlar"
        ordering = ['title']

    def __str__(self):
        return self.title


class ApplicationStatus(models.TextChoices):
    PENDING = 'pending', 'Kutilmoqda'
    ACCEPTED = 'accepted', 'Qabul qilindi'
    REJECTED = 'rejected', 'Rad etildi'


class Application(BaseModel):
    full_name = models.CharField(max_length=255, verbose_name="To'liq ism sharif")
    birth_date = models.DateField(verbose_name="Tug'ilgan sana")

    is_student = models.BooleanField(default=False, verbose_name="Talabami?")
    university = models.CharField(max_length=255, null=True, blank=True,
                                  verbose_name="O'qish joyi va kursi")

    region = models.ForeignKey(Region, on_delete=models.PROTECT,
                               related_name='applications', verbose_name="Viloyat")

    phone = models.CharField(max_length=20, validators=[phone_validator], verbose_name="Telefon raqami")
    telegram = models.CharField(max_length=255, null=True, blank=True, validators=[telegram_validator],
                                verbose_name="Telegram profil havolasi")

    direction = models.ForeignKey(Direction, on_delete=models.PROTECT,
                                  related_name='applications', verbose_name="Yo'nalish")

    resume = models.FileField(upload_to='applications/resumes/', validators=[validate_resume],
                              verbose_name="Rezyume (CV)")

    extra_info = models.TextField(null=True, blank=True, verbose_name="Qo'shimcha ma'lumot")
    portfolio = models.CharField(max_length=500, null=True, blank=True, validators=[portfolio_validator],
                                 verbose_name="Portfolio manzili")

    status = models.CharField(
        max_length=10,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
        db_index=True,
        verbose_name="Holati"
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_applications',
        verbose_name="Xulosa kiritgan xodim"
    )
    conclusion = models.TextField(null=True, blank=True, verbose_name="Xulosa")
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Xulosa kiritilgan vaqt")

    class Meta:
        verbose_name = "Ariza"
        verbose_name_plural = "Arizalar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.direction}"
