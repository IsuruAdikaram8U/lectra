from django.db import models

from accounts.models import Tenant, User


class HallType(models.TextChoices):
    # Shared by Module.required_hall_type and Hall.hall_type so the two
    # can be compared directly later (e.g. module.required_hall_type ==
    # hall.hall_type) without risk of the two enums drifting apart.
    LECTURE_HALL = 'LECTURE_HALL', 'Lecture Hall'
    COMPUTER_LAB = 'COMPUTER_LAB', 'Computer Lab'
    HARDWARE_LAB = 'HARDWARE_LAB', 'Hardware Lab'


class Department(models.Model):
    # A department within a faculty (tenant) — e.g. IT, CM, IDS.
    # departments own modules and employ lecturers.
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='departments')
    code = models.CharField(max_length=10)   # e.g. "IT", "CM", "IDS"
    name = models.CharField(max_length=150)  # full name

    class Meta:
        # Same department code can repeat across different tenants,
        # but not twice within the same tenant.
        unique_together = ('tenant', 'code')

    def __str__(self):
        return f"{self.code} - {self.name}"


class DegreeProgram(models.Model):
    # A degree offered by a department — e.g. IT dept -> "IT" degree,
    # CM dept -> "AI" degree, IDS dept -> "ITM" degree.
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='degree_programs')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='degree_programs')
    code = models.CharField(max_length=10)   # e.g. "IT", "AI", "ITM"
    name = models.CharField(max_length=150)  # e.g. "Artificial Intelligence"

    class Meta:
        # Same degree code can repeat across different tenants,
        # but not twice within the same tenant.
        unique_together = ('tenant', 'code')

    def __str__(self):
        return self.code


class Batch(models.Model):
    # A yearly intake — e.g. "B23". One batch contains students from
    # several degree programs at once (see BatchDegreeEnrollment below).
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='batches')
    name = models.CharField(max_length=20)          # e.g. "B23"
    current_semester = models.IntegerField()         # e.g. 5

    class Meta:
        # Same batch name can repeat across different tenants,
        # but not twice within the same tenant.
        unique_together = ('tenant', 'name')

    def __str__(self):
        return self.name


class BatchDegreeEnrollment(models.Model):
    # Junction table: how many students from a given degree program
    # are part of a given batch. E.g. B23 = 250 IT + 50 AI + 125 ITM,
    # so this table would have 3 rows for batch B23.
    #
    # No direct `tenant` field here on purpose — tenant scoping is done
    # by joining through `batch` or `degree_program` instead, so the
    # junction row's tenant can never drift out of sync with its parents.
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='degree_enrollments')
    degree_program = models.ForeignKey(DegreeProgram, on_delete=models.CASCADE, related_name='batch_enrollments')
    student_count = models.IntegerField()  # e.g. B23 + AI = 50

    class Meta:
        # A batch can only have one enrollment row per degree program —
        # otherwise the same batch+degree pair could get double-counted.
        unique_together = ('batch', 'degree_program')

    def __str__(self):
        return f"{self.batch} / {self.degree_program} ({self.student_count})"


class Module(models.Model):
    # A subject/course. One module can be shared across multiple degree
    # programs (see ModuleDegreeMapping) and taught by multiple lecturers
    # (see ModuleLecturer).

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='modules')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='modules')  # owning dept
    code = models.CharField(max_length=20)    # e.g. "IN3210"
    title = models.CharField(max_length=150)  # e.g. "Mobile Application Development"

    # DecimalField (not FloatField) so values like 2.50 save exactly,
    # with no floating-point rounding surprises.
    credits = models.DecimalField(max_digits=4, decimal_places=2)  # e.g. 2.5

    # Which semester this module belongs to (e.g. 5). Required: this is what
    # lets the timetable engine answer "which modules apply to B23's current
    # semester?" — DegreeProgram alone only tells you *which* degree studies
    # it, not *when* in that degree.
    semester = models.IntegerField()

    is_practical = models.BooleanField(default=False)

    # Nullable: only practical/lab modules need a specific hall type;
    # a pure lecture module can leave this blank and just need any lecture hall.
    required_hall_type = models.CharField(
        max_length=20, choices=HallType.choices, null=True, blank=True
    )

    class Meta:
        # Module codes are unique within a tenant, not globally.
        unique_together = ('tenant', 'code')

    def __str__(self):
        return f"{self.code} - {self.title}"


class ModuleDegreeMapping(models.Model):
    # Junction table: which degree programs a module is taught to.
    # E.g. "Mobile App Development" maps to IT, AI, and ITM all at once.
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='degree_mappings')
    degree_program = models.ForeignKey(DegreeProgram, on_delete=models.CASCADE, related_name='module_mappings')

    class Meta:
        # A module shouldn't be mapped to the same degree program twice.
        unique_together = ('module', 'degree_program')

    def __str__(self):
        return f"{self.module} -> {self.degree_program}"


class Lecturer(models.Model):
    # A staff member who can be assigned to teach modules.
    # Linked 1:1 to a User so a lecturer can log in to the system.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='lecturer_profile')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='lecturers')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='lecturers')
    title = models.CharField(max_length=20)    # e.g. "Dr.", "Prof.", "Ms."
    name = models.CharField(max_length=150)    # full display name

    # Nullable — not every lecturer has a declared specialization on file.
    specialization = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.title} {self.name}"


class ModuleLecturer(models.Model):
    # Junction table: which lecturers *can* teach a given module
    # (a module can have more than one qualified lecturer).
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='module_lecturers')
    lecturer = models.ForeignKey(Lecturer, on_delete=models.CASCADE, related_name='module_lecturers')

    class Meta:
        # The same lecturer shouldn't be linked to the same module twice.
        unique_together = ('module', 'lecturer')

    def __str__(self):
        return f"{self.lecturer} teaches {self.module}"


class LecturerAvailability(models.Model):
    # A lecturer's declared available/unavailable time window on a given day.
    # Used later by clash detection / auto-generation to avoid scheduling
    # a lecturer when they're blocked.

    class DayOfWeek(models.TextChoices):
        MONDAY = 'MONDAY', 'Monday'
        TUESDAY = 'TUESDAY', 'Tuesday'
        WEDNESDAY = 'WEDNESDAY', 'Wednesday'
        THURSDAY = 'THURSDAY', 'Thursday'
        FRIDAY = 'FRIDAY', 'Friday'
        SATURDAY = 'SATURDAY', 'Saturday'

    lecturer = models.ForeignKey(Lecturer, on_delete=models.CASCADE, related_name='availability_windows')
    day_of_week = models.CharField(max_length=10, choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    # True = lecturer is free in this window; False = explicitly blocked/unavailable.
    is_available = models.BooleanField(default=True)

    def __str__(self):
        state = 'available' if self.is_available else 'blocked'
        return f"{self.lecturer} {state} {self.day_of_week} {self.start_time}-{self.end_time}"


class Hall(models.Model):
    # A physical room: a lecture hall or a computer/hardware lab.
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='halls')
    code = models.CharField(max_length=20)   # e.g. "1LH01A"
    name = models.CharField(max_length=100)  # e.g. "LAB1", "AI LAB"
    hall_type = models.CharField(max_length=20, choices=HallType.choices)

    total_capacity = models.IntegerField()    # total physical seats/machines in the room

    # Actual usable seats / *working* computers. Clash detection and any
    # capacity check must always use this field, never total_capacity —
    # a lab with 40 machines but only 32 working ones can only host 32 students.
    usable_capacity = models.IntegerField()

    has_projector = models.BooleanField(default=False)

    class Meta:
        # Hall codes are unique within a tenant, not globally.
        unique_together = ('tenant', 'code')

    def __str__(self):
        return f"{self.code} ({self.name})"


class StudentGroup(models.Model):
    # A group of students formed for one class session. May be an entire
    # batch's worth of students in one degree program, or a mixed group
    # combining subsets from multiple batches/degree programs (e.g. a
    # shared practical session).
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='student_groups')
    name = models.CharField(max_length=100)  # e.g. "IT-G1", "Mobile App Mixed-G1"

    # Used to check against Hall.usable_capacity when scheduling this group.
    total_students = models.IntegerField()

    def __str__(self):
        return self.name


class GroupBatchMapping(models.Model):
    # Junction table: how many students from which batch make up a given
    # student group. E.g. a mixed group of 40 could be 25 from B23 + 15 from B24.
    student_group = models.ForeignKey(StudentGroup, on_delete=models.CASCADE, related_name='batch_mappings')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='group_mappings')
    student_count = models.IntegerField()  # students contributed from this batch

    def __str__(self):
        return f"{self.student_group} <- {self.batch} ({self.student_count})"
