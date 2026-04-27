# serializer.py
from api.models import TeacherSubject
from api.models import Submission
from api.models import Assignment
from requests import Response
from rest_framework import serializers
from .models import *
from rest_framework import status

from rest_framework import serializers
from django.contrib.auth import authenticate

class LoginSerializer(serializers.Serializer):
    # Only define what you are sending from React Native
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        print(email, password)

        # Manually find the user by email
        user = Users.objects.filter(email=email).first()

        if user and user.check_password(password):
            data['user'] = user
            return data
        
        # If we reach here, login failed
        raise serializers.ValidationError("Invalid email or password.")

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True, allow_empty_file=True)
    
    class Meta:
        model = Users
        fields = '__all__'

class TeacherSubjectSerializer(serializers.ModelSerializer):
    subject = serializers.CharField(source='subject.name', read_only=True)
    grade = serializers.CharField(source='teacher.grade_level', read_only=True)
    section = serializers.CharField(source='teacher.section', read_only=True)
    teacher = serializers.CharField(source='teacher.get_full_name', read_only=True)
    class Meta:
        model = TeacherSubject
        fields = '__all__'
        read_only_fields = ['id',  'created_at', 'updated_at']

class AssignmentSerializer(serializers.ModelSerializer):
    images = serializers.ImageField(required=False, allow_null=True)
    assignment_file = serializers.FileField(required=False, allow_null=True)
    teacher_id = serializers.IntegerField(required=True)
    teacher = serializers.CharField(source='teacher.get_full_name', read_only=True)
    teacher_profile = serializers.ImageField(source='teacher.profile_picture', read_only=True)
    grade_level = serializers.IntegerField(required=True)
    section = serializers.CharField(max_length=1, required=True)
    subject = serializers.CharField(source='subject.name', read_only=True)
    submission_count = serializers.IntegerField(source='submissions.count', read_only=True)
    submission_percentage=serializers.SerializerMethodField( )
    total_students = serializers.SerializerMethodField( )
    
    def get_total_students(self, obj):
        return Users.objects.filter(role='student', grade_level=obj.grade_level, section=obj.section).count()
    def get_submission_percentage(self, obj):
        total_students = self.get_total_students(obj)
        submission_count = obj.submissions.count()
        return (submission_count / total_students * 100) if total_students > 0 else 0
        
    class Meta:
        model = Assignment
        fields = '__all__'
        read_only_fields = ['id', 'teacher', 'created_at', 'updated_at']
 
    def validate_due_date(self, value):
        from django.utils import timezone
 
        if value <= timezone.now():
            raise serializers.ValidationError("Due date must be in the future")
        return value
 
    def validate_title(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters long")
        return value
    
    
    def create(self, validated_data):
        """Handle file uploads during creation"""
        print("✅ Creating assignment with validated data:")
        print(f"  - Title: {validated_data.get('title')}")
        print(f"  - Has image: {'images' in validated_data}")
        print(f"  - Has file: {'assignment_file' in validated_data}")
        
        return super().create(validated_data)

class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = '__all__'
        read_only_fields = ['id', 'student', 'submitted_at', 'marks_obtained', 'feedback']

    def validate_title(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters long")
        return value
    
    def validate_submission_file(self , value):
        if value.size > 1024 * 1024 * 10:
            raise serializers.ValidationError("File size must be less than 10MB")
        return value

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ['id', 'first_name', 'last_name', 'email', 'profile_picture', 'grade_level', 'section']


class MessageSerializer(serializers.ModelSerializer):
    sender_profile = serializers.ImageField(source='sender.profile_picture', read_only=True)
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    message_file = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Message
        read_only_fields = ['id', 'sender', 'created_at', 'is_read']
        fields = ['id', 'sender_profile', 'sender_name', 'content', 'is_read', 'created_at', 'conversation','message_file']

class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    other_participant = serializers.SerializerMethodField()
    messages = MessageSerializer(many=True, read_only=True)
    
    def get_other_participant(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None

        participants_qs = obj.participants.exclude(id=request.user.id)
        if participants_qs.exists():
            other = participants_qs.first()
            return {
                'id': other.id,
                'name': other.get_full_name(),
                'profile_picture': other.profile_picture.url if other.profile_picture else None
            }
        return None

    class Meta:
        model = Conversation
        fields = '__all__'
        read_only_fields = ['id', 'participants', 'created_at']