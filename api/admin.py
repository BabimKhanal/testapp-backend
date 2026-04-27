from django.contrib import admin
from .models import *


# Register your models here.
admin.site.register([
    Users,
    Assignment,
    Submission,
    Subject,
    TeacherSubject,
    Conversation,
    Message
])