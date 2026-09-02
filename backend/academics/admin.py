from django.contrib import admin

from .models import (
    Department, DegreeProgram, Batch, BatchDegreeEnrollment,
    Module, ModuleDegreeMapping, Lecturer, ModuleLecturer,
    LecturerAvailability, Hall, StudentGroup, GroupBatchMapping,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'tenant']
    search_fields = ['code', 'name']
    list_filter = ['tenant']


@admin.register(DegreeProgram)
class DegreeProgramAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'department', 'tenant']
    search_fields = ['code', 'name']
    list_filter = ['tenant', 'department']


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ['name', 'current_semester', 'tenant']
    search_fields = ['name']
    list_filter = ['tenant']


@admin.register(BatchDegreeEnrollment)
class BatchDegreeEnrollmentAdmin(admin.ModelAdmin):
    # Junction table — showing both sides plus the count is enough here.
    list_display = ['batch', 'degree_program', 'student_count']
    list_filter = ['batch', 'degree_program']


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'department', 'semester', 'credits', 'is_practical']
    search_fields = ['code', 'title']
    list_filter = ['tenant', 'department', 'semester', 'is_practical']


@admin.register(ModuleDegreeMapping)
class ModuleDegreeMappingAdmin(admin.ModelAdmin):
    list_display = ['module', 'degree_program']
    list_filter = ['degree_program']


@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    list_display = ['title', 'name', 'department', 'specialization', 'tenant']
    search_fields = ['name']
    list_filter = ['tenant', 'department']


@admin.register(ModuleLecturer)
class ModuleLecturerAdmin(admin.ModelAdmin):
    list_display = ['module', 'lecturer']
    list_filter = ['module', 'lecturer']


@admin.register(LecturerAvailability)
class LecturerAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['lecturer', 'day_of_week', 'start_time', 'end_time', 'is_available']
    list_filter = ['day_of_week', 'is_available']


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'hall_type', 'total_capacity', 'usable_capacity', 'tenant']
    search_fields = ['code', 'name']
    list_filter = ['tenant', 'hall_type']


@admin.register(StudentGroup)
class StudentGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'total_students', 'tenant']
    search_fields = ['name']
    list_filter = ['tenant']


@admin.register(GroupBatchMapping)
class GroupBatchMappingAdmin(admin.ModelAdmin):
    list_display = ['student_group', 'batch', 'student_count']
    list_filter = ['batch']
