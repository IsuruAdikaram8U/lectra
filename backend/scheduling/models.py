from django.core.exceptions import ValidationError
from django.db import models

from accounts.models import Tenant
from academics.models import Batch, DegreeProgram, Hall, Lecturer, Module, StudentGroup


class Timetable(models.Model):
    # Container for one full timetable draft/version. ScheduleEntry rows
    # each belong to exactly one Timetable, so several drafts (and the
    # published history) for the same batch can coexist as separate rows.

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PUBLISHED = 'PUBLISHED', 'Published'
        ARCHIVED = 'ARCHIVED', 'Archived'

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='timetables')

    # Direct link to the batch (not just inferred from entries) so any
    # client can instantly query "the latest published timetable for B23"
    # without parsing free-text names.
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='timetables')

    # A batch is enrolled in multiple degree programs at once (see
    # BatchDegreeEnrollment), and each degree program publishes and manages
    # its OWN independent timetable for that batch — e.g. B23's IT timetable
    # and B23's AI timetable are two separate documents, not one shared one.
    # Required (not nullable): every real timetable belongs to exactly one degree program.
    degree_program = models.ForeignKey(DegreeProgram, on_delete=models.CASCADE, related_name='timetables')

    # Only ever set when a timetable is PUBLISHED — see save() below.
    # Drafts/suggestions leave this null, so several drafts can freely
    # coexist per batch without tripping the unique_together constraint.
    version = models.IntegerField(null=True, blank=True)

    # Human-facing label. Used for draft names ("Suggestion 1", "Suggestion 2")
    # while status=DRAFT, and optionally as a note on published versions
    # (e.g. "Pre-exam adjusted").
    name = models.CharField(max_length=150, null=True, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    valid_from = models.DateField()
    valid_to = models.DateField()

    class Meta:
        # Version numbering is scoped per (batch, degree_program) pair, not
        # just per batch — so B23's IT timetable and B23's AI timetable can
        # each independently reach "version 1" without colliding.
        # Has no effect on drafts, since version is null there and multiple
        # NULLs don't violate a unique constraint.
        unique_together = ('batch', 'degree_program', 'version')

    def save(self, *args, **kwargs):
        # Auto-assign the next version number the moment this row becomes
        # PUBLISHED, but only if it doesn't already have one (so re-saving
        # an already-published timetable doesn't bump its version again —
        # a genuinely new version is created as a new row/publish action).
        if self.status == self.Status.PUBLISHED and self.version is None:
            latest = (
                Timetable.objects
                # Scoped by degree_program too, so each degree program's
                # version sequence (V1, V2, V3...) is independent of the others.
                .filter(batch=self.batch, degree_program=self.degree_program, status=self.Status.PUBLISHED)
                .exclude(pk=self.pk)
                .aggregate(models.Max('version'))
            )
            current_max = latest['version__max'] or 0
            self.version = current_max + 1

        super().save(*args, **kwargs)

    def __str__(self):
        if self.version:
            return f"{self.batch} - V{self.version}"
        return f"{self.batch} - {self.name or 'Draft'}"


class ScheduleEntry(models.Model):
    # One row = one class session/slot within a specific Timetable.

    class SessionType(models.TextChoices):
        LECTURE = 'LECTURE', 'Lecture'
        LAB = 'LAB', 'Lab'
        TUTORIAL = 'TUTORIAL', 'Tutorial'

    class DayOfWeek(models.TextChoices):
        MONDAY = 'MONDAY', 'Monday'
        TUESDAY = 'TUESDAY', 'Tuesday'
        WEDNESDAY = 'WEDNESDAY', 'Wednesday'
        THURSDAY = 'THURSDAY', 'Thursday'
        FRIDAY = 'FRIDAY', 'Friday'
        SATURDAY = 'SATURDAY', 'Saturday'

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='schedule_entries')

    # NOTE on cross-degree shared sessions: a single physical class session
    # can legitimately need to appear on more than one Timetable at once
    # (e.g. a module jointly taught to IT and ITM students in the same hall,
    # same time slot). Rather than making this field a ManyToMany, the
    # convention is: create ONE ScheduleEntry row PER Timetable it belongs
    # to, with identical module/lecturer/hall/day/time/student_groups data
    # but a different `timetable` FK on each row. This keeps the common case
    # (one entry, one timetable) simple and keeps clash-detection reasoning
    # about a single timetable per row, at the cost of some duplicated rows
    # for the relatively rare genuinely-shared sessions.
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='entries')

    # Nullable: a session doesn't have to be tied to a module (see event_name below).
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, null=True, blank=True, related_name='schedule_entries'
    )

    # Only used when module is null, to label a non-module event
    # (e.g. "Guest Talk", "Union Hour"). Validated together with `module`
    # in clean() below.
    event_name = models.CharField(max_length=150, null=True, blank=True)

    lecturer = models.ForeignKey(
        Lecturer, on_delete=models.CASCADE, null=True, blank=True, related_name='schedule_entries'
    )

    # Must be null when is_online=True, and set when is_online=False.
    # Enforced in clean() — conditional either/or rules like this can't
    # be expressed as a plain database constraint.
    hall = models.ForeignKey(
        Hall, on_delete=models.CASCADE, null=True, blank=True, related_name='schedule_entries'
    )

    # A single session can serve more than one group at once — e.g. a mixed
    # practical combining subsets of two or three degree programs in the
    # same room at the same time. Hence ManyToMany, not ForeignKey.
    student_groups = models.ManyToManyField(StudentGroup, related_name='schedule_entries')

    # When True, clash detection skips hall-capacity checks entirely,
    # since there's no physical room to check.
    is_online = models.BooleanField(default=False)

    session_type = models.CharField(max_length=20, choices=SessionType.choices)
    day_of_week = models.CharField(max_length=10, choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def clean(self):
        super().clean()

        # If there's no module, this session must be labelled some other way.
        if self.module is None and not self.event_name:
            raise ValidationError(
                "event_name is required when module is not set."
            )

        # Online sessions have no physical room; offline sessions must have one.
        if self.is_online and self.hall is not None:
            raise ValidationError("hall must be empty when is_online is True.")
        if not self.is_online and self.hall is None:
            raise ValidationError("hall is required when is_online is False.")

    def __str__(self):
        label = self.module.code if self.module else self.event_name
        return f"{label} - {self.day_of_week} {self.start_time}-{self.end_time}"
