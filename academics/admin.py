from django.contrib import admin
from .models import AcademicYear, Classroom, StudentEnrollment, Subject, Semester, Grade, Absence, Schedule

admin.site.register(AcademicYear)
admin.site.register(Classroom)
admin.site.register(StudentEnrollment)
admin.site.register(Subject)
admin.site.register(Semester)
admin.site.register(Grade)
admin.site.register(Absence)
admin.site.register(Schedule)
