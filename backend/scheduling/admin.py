from django.contrib import admin

from .models import Timetable, ScheduleEntry


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ['batch', 'name', 'status', 'version', 'valid_from', 'valid_to', 'tenant']
    list_filter = ['tenant', 'batch', 'status']
    search_fields = ['name']


@admin.register(ScheduleEntry)
class ScheduleEntryAdmin(admin.ModelAdmin):
    list_display = [
        'timetable', 'module', 'event_name', 'lecturer', 'hall',
        'is_online', 'session_type', 'day_of_week', 'start_time', 'end_time',
    ]
    list_filter = ['timetable', 'session_type', 'day_of_week', 'is_online']
    # student_groups is a ManyToManyField — filter_horizontal gives a nicer
    # dual-list widget in the admin form instead of a plain multi-select box.
    filter_horizontal = ['student_groups']
