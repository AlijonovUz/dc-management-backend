import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.finance.models import Ledger, Payroll, TransactionType
from apps.projects.models import MeetingAttendance, Project, ProjectStatus, Task, TaskStatus
from apps.users.models import Role, User

logger = logging.getLogger(__name__)

TWO_PLACES = Decimal("0.01")


def _round(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _get_month_range(now):
    first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_of_prev_month = first_of_this_month - timedelta(seconds=1)
    first_of_prev_month = last_of_prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return first_of_prev_month, last_of_prev_month


def _add_ledger_entries(ledger_bulk: list, user, amount: Decimal,
                        transaction_type: str, description: str,
                        expense=None, payroll=None):
    ledger_bulk.append(
        Ledger(
            user=user,
            amount=amount,
            transaction_type=transaction_type,
            description=description[:255],
            expense=expense,
            payroll=payroll,
        )
    )


def _calc_meeting_penalty(user, start: any, end: any) -> Decimal:
    missed_qs = (
        MeetingAttendance.objects
        .filter(
            user=user,
            is_attended=False,
            absence_reason__isnull=True,
            meeting__start_time__range=(start, end),
        )
        .exclude(meeting__organizer=user)
        .select_related("meeting")
    )

    total_penalty = Decimal("0.00")
    for att in missed_qs:
        pct = att.meeting.penalty_percentage
        if pct > 0 and user.fixed_salary > 0:
            total_penalty += _round((user.fixed_salary * Decimal(str(pct))) / 100)

    return total_penalty


def _calc_manager_kpi(user, start, end):
    completed_projects = (
        Project.objects
        .filter(
            manager=user,
            status=ProjectStatus.COMPLETED,
            updated_at__range=(start, end),
        )
        .only("title", "project_price", "penalty_percentage", "updated_at", "deadline")
    )

    kpi_bonus = Decimal("0.00")
    total_penalty = Decimal("0.00")

    for project in completed_projects:
        gross = _round(project.project_price)
        penalty = Decimal("0.00")

        if project.penalty_percentage > 0 and project.updated_at > project.deadline:
            penalty = _round((gross * Decimal(str(project.penalty_percentage))) / 100)

        net = gross - penalty
        kpi_bonus += gross
        total_penalty += penalty

        logger.debug(
            "Manager %s | loyiha '%s' | gross=%s | penalty=%s | net=%s",
            user.username, project.title, gross, penalty, net,
        )

    net_bonus = kpi_bonus - total_penalty
    return kpi_bonus, total_penalty, net_bonus


def _calc_employee_kpi(user, start, end):
    completed_tasks = list(
        Task.objects
        .filter(
            assignee=user,
            status__in=[TaskStatus.CHECKED, TaskStatus.PRODUCTION],
            updated_at__range=(start, end),
        )
        .only(
            "title", "task_price", "penalty_percentage",
            "estimated_minutes", "actual_minutes", "reopened_count",
            "deadline", "updated_at",
        )
    )

    kpi_bonus = Decimal("0.00")
    total_penalty = Decimal("0.00")
    bugs_count = 0

    for task in completed_tasks:
        gross = _round(task.task_price)

        est = task.estimated_minutes or 0
        act = task.actual_minutes or 0

        if est > 0 and act > 0:
            velocity = Decimal(str(min(est / act, 1.0)))
        else:
            velocity = Decimal("1.0")

        weighted_bonus = _round(gross * velocity)

        penalty = Decimal("0.00")
        if task.penalty_percentage > 0 and task.updated_at > task.deadline:
            penalty += _round((gross * Decimal(str(task.penalty_percentage))) / 100)

        if task.penalty_percentage > 0 and task.reopened_count > 0:
            reopen_penalty = _round(
                (gross * Decimal(str(task.penalty_percentage))) / 100
            ) * task.reopened_count
            penalty += reopen_penalty

        net = max(weighted_bonus - penalty, Decimal("0.00"))

        kpi_bonus += weighted_bonus
        total_penalty += penalty
        bugs_count += task.reopened_count

        logger.debug(
            "Employee %s | task '%s' | gross=%s | velocity=%s | weighted=%s | penalty=%s | net=%s",
            user.username, task.title, gross, velocity, weighted_bonus, penalty, net,
        )

    overdue_tasks = list(
        Task.objects
        .filter(
            assignee=user,
            status=TaskStatus.OVERDUE,
            updated_at__range=(start, end),
        )
        .only("title", "task_price", "penalty_percentage")
    )
    missed_deadlines = len(overdue_tasks)

    for task in overdue_tasks:
        if task.penalty_percentage > 0 and task.task_price > 0:
            overdue_penalty = _round(
                (_round(task.task_price) * Decimal(str(task.penalty_percentage))) / 100
            )
            total_penalty += overdue_penalty
            logger.debug(
                "Employee %s | overdue task '%s' | task_price=%s | penalty=%s",
                user.username, task.title, task.task_price, overdue_penalty,
            )

    net_bonus = max(kpi_bonus - total_penalty, Decimal("0.00"))
    tasks_done = len(completed_tasks)

    return kpi_bonus, total_penalty, net_bonus, tasks_done, missed_deadlines, bugs_count


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def calculate_monthly_salaries(self):
    now = timezone.now()
    month_start, month_end = _get_month_range(now)
    month_label = month_start.strftime("%Y-%m")

    logger.info("Oylik hisob-kitob boshlandi: %s", month_label)

    users_qs = (
        User.objects
        .filter(is_active=True)
        .only("id", "username", "role", "fixed_salary", "balance")
        .iterator(chunk_size=500)
    )

    processed = 0
    errors = 0

    for user in users_qs:
        try:
            _process_user(user, month_start, month_end, month_label)
            processed += 1
        except Exception as exc:
            errors += 1
            logger.error(
                "Foydalanuvchi %s (%s) uchun hisoblashda xato: %s",
                user.username, user.pk, exc,
                exc_info=True,
            )

    result = (
        f"{month_label} oyi | "
        f"muvaffaqiyatli: {processed} | "
        f"xato: {errors}"
    )
    logger.info("Oylik hisob-kitob yakunlandi: %s", result)
    return result


def _process_user(user: User, month_start, month_end, month_label: str):
    with transaction.atomic():
        ledger_bulk = []
        balance_delta = Decimal("0.00")

        kpi_bonus = Decimal("0.00")
        total_penalty = Decimal("0.00")
        tasks_done = 0
        missed_deadlines = 0
        bugs_count = 0

        if user.fixed_salary > 0:
            balance_delta += user.fixed_salary
            _add_ledger_entries(
                ledger_bulk, user,
                amount=user.fixed_salary,
                transaction_type=TransactionType.CREDIT,
                description=f"{month_label} oyi uchun asosiy oylik maosh",
            )

        if user.role == Role.EMPLOYEE:
            meeting_penalty = _calc_meeting_penalty(user, month_start, month_end)
            if meeting_penalty > 0:
                balance_delta -= meeting_penalty
                total_penalty += meeting_penalty
                _add_ledger_entries(
                    ledger_bulk, user,
                    amount=meeting_penalty,
                    transaction_type=TransactionType.DEBIT,
                    description=f"{month_label} oyi | yig'ilishlarni o'tkazib yuborish jarimalari",
                )

        if user.role == Role.MANAGER:
            kpi_bonus, proj_penalty, net_bonus = _calc_manager_kpi(user, month_start, month_end)
            total_penalty += proj_penalty

            if net_bonus > 0:
                balance_delta += net_bonus
                _add_ledger_entries(
                    ledger_bulk, user,
                    amount=net_bonus,
                    transaction_type=TransactionType.CREDIT,
                    description=f"{month_label} oyi | manager loyiha KPI bonusi (jarima chegirilgan)",
                )

        elif user.role == Role.EMPLOYEE:
            (
                kpi_bonus, task_penalty, net_bonus,
                tasks_done, missed_deadlines, bugs_count,
            ) = _calc_employee_kpi(user, month_start, month_end)
            total_penalty += task_penalty

            if net_bonus > 0:
                balance_delta += net_bonus
                _add_ledger_entries(
                    ledger_bulk, user,
                    amount=net_bonus,
                    transaction_type=TransactionType.CREDIT,
                    description=f"{month_label} oyi | xodim KPI bonusi (velocity + jarima chegirilgan)",
                )

        payroll = Payroll.objects.create(
            user=user,
            month=month_start.date(),
            fixed_salary=user.fixed_salary,
            kpi_bonus=kpi_bonus,
            penalty_amount=total_penalty,
            tasks_completed=tasks_done,
            deadline_missed=missed_deadlines,
            bug_count=bugs_count,
        )

        for entry in ledger_bulk:
            entry.payroll = payroll

        if ledger_bulk:
            Ledger.objects.bulk_create(ledger_bulk)

        if balance_delta != Decimal("0.00"):
            User.objects.filter(pk=user.pk).update(
                balance=F("balance") + balance_delta
            )

        logger.info(
            "Hisoblandi | %s (%s) | fixed=%s | kpi=%s | penalty=%s | delta=%s",
            user.username, user.role,
            user.fixed_salary, kpi_bonus, total_penalty, balance_delta,
        )
