

from api.views import ConversationListView
from django.contrib.auth.views import LogoutView
from api.views import AssignmentView
from api.views import CurrentUserView
from api.views import *
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
path('dashboard', DashboardView.as_view(), name='dashboard'),
path('auth/login', LoginView.as_view(), name='login'),
path('auth/logout', LogoutView.as_view(), name='logout'),
path('users/<int:id>', CurrentUserView.as_view(), name='users'),
path('users/me', CurrentUserView.as_view(), name='users'),
path('assignments', AssignmentView.as_view(), name='assignments'),
path('assignments/<int:assignment_id>/', GetSingleAssignment.as_view(), name='assignments'),
path('assignments/<int:grade_id>/<str:section_id>/<str:subject_id>/', GetSingleAssignment.as_view(), name='assignments'),
path('assignments/<int:assignment_id>/submissions', AssignmentSubmissionsView.as_view(), name='assignment-submissions'),
path('assignments/grade/submit', SubmissionGradeView.as_view(), name='grade-submission'),
path('teachersubjects', TeacherSubjectView.as_view(), name='teacher-subjects'),
path('students', StudentListView.as_view(), name='students'),
path('teachers', TeacherListView.as_view(), name='teachers'),
path('schema', SpectacularAPIView.as_view(), name='schema'),
path('docs', SpectacularSwaggerView.as_view(url_name='schema')),
path('redoc', SpectacularRedocView.as_view(url_name='schema')),
path('conversations', ConversationListView.as_view(), name='conversations'),
path('conversations/<int:id>/messages', MessageView.as_view(), name='messages'),
path('messages/send', SendMessageView.as_view(), name='send-message'),
path('messages/seen', MessageSeenView.as_view(), name='message-seen'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)