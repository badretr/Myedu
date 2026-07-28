from django.contrib import admin
from .models import (AcademicYear, Classroom, StudentEnrollment, Subject, Semester,
                     Grade, Absence, Schedule, StudentNote, EnrollmentHistory, ScheduleEntry,
                     LessonEntry, CourseResource)

admin.site.register(AcademicYear)
admin.site.register(Classroom)
admin.site.register(StudentEnrollment)
admin.site.register(Subject)
admin.site.register(Semester)
admin.site.register(Grade)
admin.site.register(Absence)
admin.site.register(Schedule)
admin.site.register(StudentNote)
admin.site.register(EnrollmentHistory)
admin.site.register(ScheduleEntry)
admin.site.register(LessonEntry)
admin.site.register(CourseResource)
