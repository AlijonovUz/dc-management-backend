from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    SUPERADMIN = 'superadmin', 'SuperAdmin'
    ADMIN = 'admin', 'Admin',
    MANAGER = 'manager', 'Manager',
    EMPLOYEE = 'employee', 'Employee',
    AUDITOR = 'auditor', 'Auditor',
    ACCOUNTANT = 'accountant', 'Accountant'


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    fixed_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.get_full_name()} - {self.role}"
