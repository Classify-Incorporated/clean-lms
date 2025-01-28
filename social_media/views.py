from django.shortcuts import render
from .serialzers import *
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import action
from django.db.models import Q
from django.shortcuts import get_object_or_404
# Create your views here.

class Post_ViewSet(ModelViewSet):
    serializer_class = Post_Serializer

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()
    

class Share_ViewSet(ModelViewSet):
    serializer_class = Share_Serializer

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()
    

class Like_ViewSet(ModelViewSet):
    serializer_class = Like_Serializer

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()
    
class Comment_ViewSet(ModelViewSet):
    serializer_class = Comment_Serializer

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()
    
class Friend_ViewSet(ModelViewSet):
    serializer_class = Friend_Serializer

    def get_queryset(self):
        return Friend.objects.filter(to_user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        from_user = request.user 
        to_user_id = request.data.get('to_user')

        # Check if `to_user` exists
        try:
            to_user = CustomUser.objects.get(id=to_user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Prevent sending a friend request to yourself
        if from_user == to_user:
            return Response({"error": "You cannot send a friend request to yourself."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the friend request already exists
        if Friend.objects.filter(from_user=from_user, to_user=to_user).exists():
            return Response({"error": "Friend request already sent."}, status=status.HTTP_400_BAD_REQUEST)

        # Create the friend request
        friend_request = Friend.objects.create(from_user=from_user, to_user=to_user)
        return Response(Friend_Serializer(friend_request).data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['GET'], url_path='friends')
    def friends(self, request):
        """
        Get the list of friends for the logged-in user.
        """
        user = request.user
        friends = Friend.objects.filter(
            (Q(from_user=user) | Q(to_user=user)) & Q(status='accepted')
        )

        data = []
        for friend in friends:
            # Identify the actual friend (the user who is not the logged-in user)
            friend_user = friend.to_user if friend.from_user == user else friend.from_user
            profile = getattr(friend_user, 'profile', None)

            # Ensure we get the full name
            full_name = f"{profile.first_name or ''} {profile.last_name or ''}".strip() if profile else friend_user.username

            data.append({
                "id": friend_user.id,
                "name": full_name, 
                "photo": profile.student_photo.url if profile and profile.student_photo else None,  
            })

        return Response(data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['GET'], url_path='sent-requests')
    def sent_friend_requests(self, request):
        """
        Returns a list of user IDs to whom the logged-in user has sent friend requests.
        """
        user = request.user
        sent_requests = Friend.objects.filter(from_user=user).values_list('to_user_id', flat=True)
        return Response(list(sent_requests), status=status.HTTP_200_OK)


    @action(detail=False, methods=['GET'], url_path='pending-requests')
    def pending_requests(self, request):
        """
        Returns a list of users who have sent friend requests to the logged-in user.
        """
        friend_requests = Friend.objects.filter(to_user=request.user, status='pending')
        data = [
            {
                "id": request.id,
                "from_user_id": request.from_user.id,
                "from_user_name": f"{request.from_user.first_name} {request.from_user.last_name}",
                "from_user_photo": getattr(request.from_user.profile, 'photo', None)  # Safely retrieve photo if it exists
            }
            for request in friend_requests
        ]
        return Response(data, status=status.HTTP_200_OK)
    
    
    @action(detail=True, methods=['POST'])
    def accept(self, request, pk=None):
        """
        Accept a friend request.
        """
        try:
            friend_request = self.get_queryset().get(id=pk, to_user=request.user, status='pending')
        except Friend.DoesNotExist:
            return Response({"error": "Friend request not found or already handled."}, status=status.HTTP_404_NOT_FOUND)

        friend_request.status = 'accepted'
        friend_request.save()
        return Response({"message": "Friend request accepted."}, status=status.HTTP_200_OK)


    @action(detail=True, methods=['POST'])
    def reject(self, request, pk=None):
        """
        Reject a friend request.
        """
        try:
            friend_request = self.get_queryset().get(id=pk, to_user=request.user, status='pending')
        except Friend.DoesNotExist:
            return Response({"error": "Friend request not found or already handled."}, status=status.HTTP_404_NOT_FOUND)

        friend_request.delete() 
        return Response({"message": "Friend request rejected."}, status=status.HTTP_200_OK)
    

class Block_ViewSet(ModelViewSet):
    serializer_class = Block_Serializer

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()
    
class Chat_ViewSet(ModelViewSet):
    serializer_class = Chat_Serializer

    def get_queryset(self):
        sender_id = self.request.user.id  # The logged-in user
        receiver_id = self.request.query_params.get('receiver')  # The other user

        if not receiver_id:
            return Chat.objects.none()  # Return an empty queryset if no receiver is provided

        return Chat.objects.filter(
            Q(sender_id=sender_id, receiver_id=receiver_id) | Q(sender_id=receiver_id, receiver_id=sender_id)
        ).order_by('created_at') 

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={"request": request})  # Ensure absolute image URLs
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        sender = request.user
        receiver_id = request.data.get('receiver')
        message_text = request.data.get('message')

        # Ensure receiver is valid
        receiver = CustomUser.objects.get(id=receiver_id)

        # Create the chat message
        chat_message = Chat.objects.create(
            sender=sender,
            receiver=receiver,
            message=message_text
        )

        return Response(Chat_Serializer(chat_message).data, status=status.HTTP_201_CREATED)
    

class Report_ViewSet(ModelViewSet):
    serializer_class = Report_Serializer

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()

class User_ViewSet(ModelViewSet):
    serializer_class = CustomUser_Serializer

    def get_queryset(self):
        return CustomUser.objects.exclude(id=self.request.user.id)

def social_media_dashboard(request):
    return render(request, 'social_media/social_media_dashboard.html')

