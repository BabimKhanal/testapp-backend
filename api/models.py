from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser
from django.db import models


class Subject(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True,
        choices=[
            ('Math', 'Math'),
            ('Science', 'Science'),
            ('English', 'English'),
            ('History', 'History'),
            ('Geography', 'Geography'),
            ('Chemistry', 'Chemistry'),
            ('Physics', 'Physics'),
            ('Biology', 'Biology'),
            ('Computer Science', 'Computer Science'),
            ('Other', 'Other')
        ]
    )
    def __str__(self):
        return self.name


class Users(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    gender = models.CharField(
        max_length=100,
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        null=True, blank=True
    )
    role = models.CharField(
        max_length=100,
        choices=[('admin', 'Admin'), ('teacher', 'Teacher'), ('student', 'Student')]
    )
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    # Student's current grade & section (simple approach, no historical tracking)
    grade_level = models.IntegerField(
        choices=[(i, i) for i in range(1, 13)],
        null=True, blank=True
    )
    section = models.CharField(
        max_length=1,
        choices=[(chr(65+i), chr(65+i)) for i in range(26)],
        null=True, blank=True
    )



    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith(('pbkdf2_sha256$', 'bcrypt', 'argon2')):
            self.set_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

    @property
    def is_student(self):
        return self.role == 'student'

    @property
    def is_teacher(self):
        return self.role == 'teacher'

    @property
    def is_admin(self):
        return self.role == 'admin'


class TeacherSubject(models.Model):
    teacher = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name='taught_subjects',
        limit_choices_to={'role': 'teacher'}
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    # You can add extra fields like "is_primary" if needed

    class Meta:
        unique_together = ['teacher', 'subject']   # one teacher can't teach the same subject twice

    def __str__(self):
        return f"{self.teacher.username} – {self.subject.name}"


class Assignment(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    images = models.ImageField(upload_to='assignments/', null=True, blank=True)
    assignment_file = models.FileField(upload_to='assignments/', null=True, blank=True)
    teacher = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='assignments_created')
    grade_level = models.IntegerField(
        choices=[(i, i) for i in range(1, 13)]
    )
    section = models.CharField(
        max_length=1,
        choices=[(chr(65+i), chr(65+i)) for i in range(26)]
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    title = models.CharField(max_length=100)
    student = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='submissions')
    images = models.ImageField(upload_to='submissions/', null=True, blank=True)
    submission_file = models.FileField(upload_to='submissions/', null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    marks_obtained = models.FloatField(null=True, blank=True)
    feedback = models.TextField(blank=True)

    class Meta:
        unique_together = ['assignment', 'student']

    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"




class Conversation(models.Model):
    participants = models.ManyToManyField(Users, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        participant_names = ", ".join([p.username for p in self.participants.all()])
        return f"Conversation: {participant_names}"

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    message_file = models.FileField(upload_to='messages/', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.username} in {self.conversation.id} at {self.created_at}"

    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation.id,
            'sender_id': self.sender.id,
            'sender_name': self.sender.username,
            'sender_profile': self.sender.profile_picture.url if self.sender.profile_picture else None,
            'content': self.content,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
        }
