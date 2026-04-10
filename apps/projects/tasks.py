import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from .models import Project, ProjectStatus, Task, TaskStatus

logger = logging.getLogger(__name__)


@shared_task
def send_push_notification_task(user_id, title, message):
    logger.info(f"Bildirishnoma: {user_id} - {title} - {message}")
    return True


@shared_task
def update_overdue_status_and_notify():
    now = timezone.now()

    overdue_projects = list(Project.objects.filter(
        status__in=[ProjectStatus.PLANNING, ProjectStatus.ACTIVE],
        deadline__lt=now
    ).only('id', 'title', 'status', 'manager_id'))

    if overdue_projects:
        for project in overdue_projects:
            project.status = ProjectStatus.OVERDUE
            if project.manager_id:
                send_push_notification_task.delay(
                    project.manager_id,
                    "Loyiha muddati o'tdi",
                    f"'{project.title}' loyihasi rejadagidan kechikmoqda."
                )

        Project.objects.bulk_update(overdue_projects, ['status'], batch_size=500)

    overdue_tasks = list(Task.objects.filter(
        status__in=[TaskStatus.TODO, TaskStatus.IN_PROGRESS],
        deadline__lt=now
    ).select_related('project').only('id', 'title', 'status', 'project__manager_id'))

    if overdue_tasks:
        for task in overdue_tasks:
            task.status = TaskStatus.OVERDUE
            if task.project.manager_id:
                send_push_notification_task.delay(
                    task.project.manager_id,
                    "Vazifa muddati o'tdi",
                    f"'{task.title}' vazifasi belgilangan muddatdan kechikdi."
                )

        Task.objects.bulk_update(overdue_tasks, ['status'], batch_size=1000)

    return f"{len(overdue_projects)} loyiha, {len(overdue_tasks)} vazifa holati 'overdue' qilindi."


@shared_task
def send_morning_reminders():
    today = timezone.now().date()

    remind_tasks = Task.objects.filter(
        Q(deadline__date=today) | Q(status=TaskStatus.OVERDUE),
        assignee__isnull=False
    ).exclude(
        status__in=[TaskStatus.DONE, TaskStatus.CHECKED, TaskStatus.PRODUCTION]
    ).only('id', 'title', 'assignee_id')

    count = 0
    for task in remind_tasks.iterator(chunk_size=1000):
        send_push_notification_task.delay(
            task.assignee_id,
            "Bugungi kunlik eslatma",
            f"'{task.title}' vazifasini bugun yakunlash shart yoki muddati o'tgan!"
        )
        count += 1

    return f"{count} ta xodimga ertalabki eslatmalar navbatga qo'yildi."

