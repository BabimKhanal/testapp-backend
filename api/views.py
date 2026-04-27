from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404
from django.db.models import Avg
from api.models import TeacherSubject
from api.serializer import *
from api.models import Subject
from drf_spectacular.utils import extend_schema
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from rest_framework.views import APIView
from django.shortcuts import render
from rest_framework import generics
from .models import Users
from rest_framework import status
from .serializer import UserSerializer
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        # Common counts for all roles
        total_students = Users.objects.filter(role='student').count()
        total_teachers = Users.objects.filter(role='teacher').count()

  
        if user.is_admin:
            total_assignments = Assignment.objects.count()
            total_submissions = Submission.objects.count()
            pending_grading = Submission.objects.filter(marks_obtained__isnull=True).count()
            avg_grade = Submission.objects.filter(marks_obtained__isnull=False).aggregate(Avg('marks_obtained'))['marks_obtained__avg']

            return Response({
                "success": True,
                "role": "admin",
                "data": {
                    "total_students": total_students,
                    "total_teachers": total_teachers,
                    "total_assignments": total_assignments,
                    "total_submissions": total_submissions,
                    "pending_grading": pending_grading,
                    "average_grade": round(avg_grade, 1) if avg_grade else 0,
                },
                "message": "Admin dashboard data"
            }, status=status.HTTP_200_OK)

        # ----- TEACHER -----
        if user.is_teacher:
            # Assignments created by this teacher
            assignments = Assignment.objects.filter(teacher=user)
            total_assignments = assignments.count()
            # Submissions for those assignments
            submissions = Submission.objects.filter(assignment__in=assignments)
            total_submissions = submissions.count()
            pending_grading = submissions.filter(marks_obtained__isnull=True).count()
            avg_grade = submissions.filter(marks_obtained__isnull=False).aggregate(Avg('marks_obtained'))['marks_obtained__avg']
            # Subjects taught by this teacher (through TeacherSubject)
            subjects_count = TeacherSubject.objects.filter(teacher=user).count()
            # Unique students who have submitted any of this teacher's assignments
            students_count = submissions.values('student').distinct().count()

            return Response({
                "success": True,
                "role": "teacher",
                "data": {
                    "total_students": students_count,
                    "total_teachers": total_teachers,  # overall, or could be filtered
                    "total_assignments": total_assignments,
                    "total_submissions": total_submissions,
                    "pending_grading": pending_grading,
                    "average_grade": round(avg_grade, 1) if avg_grade else 0,
                    "subjects_count": subjects_count,
                },
                "message": "Teacher dashboard data"
            }, status=status.HTTP_200_OK)

        if user.is_student:
            # Assignments for student's grade & section
            assignments = Assignment.objects.filter(
                grade_level=user.grade_level,
                section=user.section
            )
            total_assignments = assignments.count()
            # Submissions made by this student
            submissions = Submission.objects.filter(student=user)
            submitted_count = submissions.count()
            pending_count = total_assignments - submitted_count
            avg_grade = submissions.filter(marks_obtained__isnull=False).aggregate(Avg('marks_obtained'))['marks_obtained__avg']
            # Distinct subjects from assignments (optional)
            subjects_count = assignments.values('subject').distinct().count()

            return Response({
                "success": True,
                "role": "student",
                "data": {
                    "total_assignments": total_assignments,
                    "submitted_count": submitted_count,
                    "pending_count": pending_count,
                    "average_grade": round(avg_grade, 1) if avg_grade else 0,
                    "subjects_count": subjects_count,
                },
                "message": "Student dashboard data"
            }, status=status.HTTP_200_OK)

        # Fallback (should not happen)
        return Response({
            "success": False,
            "message": "Invalid user role"
        }, status=status.HTTP_403_FORBIDDEN)

class LoginView(APIView):
    @extend_schema(
        request=LoginSerializer,
        responses={
            status.HTTP_200_OK: LoginSerializer,
            status.HTTP_401_UNAUTHORIZED: LoginSerializer,
            status.HTTP_400_BAD_REQUEST: LoginSerializer
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user' ]

            if user : 
                refresh_token = RefreshToken.for_user(user)
                access_token = RefreshToken.for_user(user).access_token
                return Response({
                    "message": "Login successful",
                    "user_id": user.id,
                    "profile_pic": user.profile_picture.url if user.profile_picture else None,
                    "role": user.role,
                    "user": user.username,
                    "email": user.email,
                    "refresh_token": str(refresh_token),
                    "access_token": str(access_token)
            }, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 


class UserListView(generics.RetrieveUpdateAPIView):
    
    queryset = Users.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Return the current authenticated user
        return self.request.user

class CurrentUserView(generics.RetrieveUpdateAPIView):
    """Get or update the currently authenticated user's profile"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    extend_schema(
        responses={
            status.HTTP_200_OK: UserSerializer,
            status.HTTP_401_UNAUTHORIZED: UserSerializer,
            status.HTTP_400_BAD_REQUEST: UserSerializer
        }
    )
    def get_object(self):
        # Return the current authenticated user
        return self.request.user
    
    def get(self, request, *args, **kwargs):
        """Get current user profile"""
        user = self.get_object()
        serializer = self.get_serializer(user)
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Profile retrieved successfully"
        }, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        user = self.get_object()
        print(user)
        print(request.data)
        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            if 'profile_picture' in request.FILES:
                if user.profile_picture:
                    user.profile_picture.delete(save=True)
                user.profile_picture = request.FILES['profile_picture']
            serializer.save()
            return Response({
                "success": True,
                "data": serializer.data,
                "message": "Profile updated successfully"
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TeacherSubjectView(generics.ListCreateAPIView):
    queryset = TeacherSubject.objects.all()
    serializer_class = TeacherSubjectSerializer
    permission_classes = [IsAuthenticated ]
    
    def get_queryset(self):    
        return TeacherSubject.objects.filter(teacher_id=self.request.user.id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if request.user.is_student:
           serializer = TeacherSubjectSerializer(queryset, many=True)
        else:
           serializer = self.get_serializer(queryset, many=True)
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Teacher subjects fetched successfully"
        }, status=status.HTTP_200_OK)

class AssignmentView(generics.ListCreateAPIView):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer  # ✅ Add this
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    @extend_schema(
        responses={
            status.HTTP_200_OK: AssignmentSerializer,
            status.HTTP_401_UNAUTHORIZED: AssignmentSerializer,
            status.HTTP_400_BAD_REQUEST: AssignmentSerializer
        }
    )
    def get_object(self):
        # Return the current authenticated user
        return self.request.user

    def get_queryset(self):
       user = self.request.user
       if user.is_student:
        # Ensure both sides are same type
        grade_int = int(user.grade_level) if user.grade_level else None
        queryset = Assignment.objects.filter(
            grade_level=grade_int,
            section__iexact=user.section.strip()
        )
        return queryset
       else:
        queryset = Assignment.objects.filter(teacher=self.request.user)
        grade = self.request.query_params.get('grade', None)
        section = self.request.query_params.get('section', None)
        subject = self.request.query_params.get('subject', None)
        if grade:   
            queryset = queryset.filter(grade_level=grade)
        if section:   
            queryset = queryset.filter(section=section)
        if subject:   
            queryset = queryset.filter(subject=subject)    
        return queryset 
   #single assignment

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()  # ✅ Use filtered queryset
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "data": serializer.data,
            "message": "Assignments fetched successfully",
            "status": status.HTTP_200_OK
        })
    
    def create(self, request, *args, **kwargs):
        """Create a new assignment (teachers only)"""
        if not request.user.is_teacher :
            return Response({
                "error": "Only teachers can create assignments"
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Debug: Print what we received
        print("=" * 50)
        print("📥 Received data:")
        print("request.data:", request.data)
        print("request.FILES:", request.FILES)
        print("=" * 50)
        
        # ✅ Handle the data properly
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            # Save with the teacher
            assignment = serializer.save(teacher=request.user)

            
            return Response({
                "success": True,
                "data": serializer.data,
                "message": "Assignment created successfully"
            }, status=status.HTTP_201_CREATED)
        
        # Better error reporting
        print("❌ Validation errors:", serializer.errors)
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class GetSingleAssignment(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
   
    def get(self, request, *args, **kwargs):
        """Retrieve a single assignment by ID"""
        assignment_id = kwargs.get('assignment_id')
        
        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response({
                "success": False,
                "data": None,
                "message": "Assignment not found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Serialize the single assignment object
        serializer = AssignmentSerializer(assignment)
        
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Assignment retrieved successfully"
        }, status=status.HTTP_200_OK)
    
# views.py - Complete SubmissionView
class SubmissionView(generics.ListCreateAPIView):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()  # ✅ Use filtered queryset
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "data": serializer.data,
            "message": "Assignments fetched successfully",
            "status": status.HTTP_200_OK
        })

    

class AssignmentSubmissionsView(generics.ListAPIView):
    """List all submissions for a given assignment (teacher only)"""
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        assignment_id = self.kwargs['assignment_id']
        # Only teacher who owns the assignment can see submissions
        if self.request.user.is_teacher:
            return Submission.objects.filter(assignment_id=assignment_id, assignment__teacher=self.request.user)
        return Submission.objects.none()
    
    def post(self, request, *args, **kwargs):
        if not request.user.is_student:
            return Response({
                "error": "Only students can submit assignments"
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(student=request.user)
            return Response({
                "success": True,
                "data": serializer.data,
                "message": "Assignment submitted successfully"
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SubmissionGradeView(APIView):
    """Teacher grades a submission"""
    permission_classes = [IsAuthenticated]
    
    def patch(self, request):
        submission_id = request.data.get('submission')
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            return Response({
                "error": "Submission not found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user is the teacher of this assignment
        if not request.user.is_teacher or submission.assignment.teacher != request.user:
            return Response({
                "error": "Only the teacher who created this assignment can grade it"
            }, status=status.HTTP_403_FORBIDDEN)
        
        marks = request.data.get('marks_obtained')
        feedback = request.data.get('feedback', '')
        
        if marks is not None:
            submission.marks_obtained = marks
        if feedback:
            submission.feedback = feedback
        
        submission.save()
        
        serializer = SubmissionSerializer(submission)
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Submission graded successfully"
        }, status=status.HTTP_200_OK)

class StudentListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StudentSerializer
    
    def get_queryset(self):
        return Users.objects.filter(role='student')

        
class TeacherListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StudentSerializer
    
    def get_queryset(self):
        return Users.objects.filter(role='teacher')

# api/views.py
class ConversationListView(generics.ListCreateAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user)

    def create(self, request, *args, **kwargs):
        other_user_id = request.data.get('other_user_id')
        if not other_user_id:
            return Response({'error': 'other_user_id required'}, status=400)
        try:
            other_user = Users.objects.get(id=other_user_id)
        except Users.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        # ✅ Look for existing conversation
        existing = Conversation.objects.filter(participants=request.user).filter(participants=other_user).distinct()
        if existing.exists():
            conversation = existing.first()
            serializer = self.get_serializer(conversation)
            return Response(serializer.data, status=200)  # Return existing, not new

        # Otherwise create a new one
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, other_user)
        serializer = self.get_serializer(conversation)
        return Response(serializer.data, status=201)

class MessageView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer

    def get_queryset(self):
        conversation_id = self.kwargs['id']
        return Message.objects.filter(conversation_id=conversation_id)


class SendMessageView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer

    def create(self, request, *args, **kwargs):
        recipient_id = request.data.get("recipient_id")
        content = request.data.get("content", "").strip()
        message_file = request.FILES.get("file")

        if not recipient_id:
            return Response(
                {"error": "recipient_id required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not content and not message_file:
            return Response(
                {"error": "Either content or file is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recipient = get_object_or_404(Users, id=recipient_id)

        conversation = (
            Conversation.objects.filter(participants=request.user)
            .filter(participants=recipient)
            .distinct()
            .first()
        )

        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, recipient)

        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
            message_file=message_file,
        )

        payload = {
            "id": message.id,
            "conversation": conversation.id,
            "sender_id": message.sender.id,
            "sender_name": message.sender.username,
            "sender_profile": (
                message.sender.profile_picture.url
                if message.sender.profile_picture else None
            ),
            "content": message.content,
           "message_file": (
        request.build_absolute_uri(message.message_file.url)
        if message.message_file else None
    ),
            "created_at": message.created_at.isoformat(),
            "is_read": message.is_read,
        }

        channel_layer = get_channel_layer()
        for participant in conversation.participants.all():
            async_to_sync(channel_layer.group_send)(
                f"user_{participant.id}",
                {
                    "type": "private_message",
                    "message": payload,
                },
            )

        return Response(payload, status=status.HTTP_201_CREATED)
class MessageSeenView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer

    def update(self, request, *args, **kwargs):
        conversation_id = request.data.get('conversation_id')
        print("conversation_id", conversation_id)
        if not conversation_id:
            return Response({'error': 'conversation_id required'}, status=400)
        try:
            messages = Message.objects.filter(conversation_id=conversation_id)
            for message in messages:
                if message.sender != request.user:
                    message.is_read = True
                    message.save()
            return Response({'success': True}, status=status.HTTP_200_OK)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)