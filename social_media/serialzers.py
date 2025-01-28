from rest_framework import serializers
from .models import *
from accounts.models import CustomUser

class Post_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = '__all__'

class Share_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Share
        fields = '__all__'

class Like_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = '__all__'

class Comment_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'

class Friend_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Friend
        fields = '__all__'

class Block_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = '__all__'

class Report_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'

class Chat_Serializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_photo = serializers.SerializerMethodField()
    receiver_name = serializers.SerializerMethodField()
    receiver_photo = serializers.SerializerMethodField()
    is_sent = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = ['id', 'sender', 'receiver', 'message', 'created_at', 'sender_name', 'sender_photo','receiver_name', 'receiver_photo', 'is_sent']

    def get_sender_name(self, obj):
        """Return sender's full name or username"""
        if hasattr(obj.sender, 'profile') and obj.sender.profile.first_name:
            return f"{obj.sender.profile.first_name} {obj.sender.profile.last_name}".strip()
        return obj.sender.username

    def get_sender_photo(self, obj):
        """Return the sender's profile image full URL"""
        request = self.context.get('request')
        if hasattr(obj.sender, 'profile') and obj.sender.profile.student_photo:
            return request.build_absolute_uri(obj.sender.profile.student_photo.url) if request else obj.sender.profile.student_photo.url
        return None
    
    def get_receiver_name(self, obj):
        """Return receiver's full name or username"""
        if hasattr(obj.receiver, 'profile') and obj.receiver.profile.first_name:
            return f"{obj.receiver.profile.first_name} {obj.receiver.profile.last_name}".strip()
        return obj.receiver.username

    def get_receiver_photo(self, obj):
        """Return the receiver's profile image full URL"""
        request = self.context.get('request')
        if hasattr(obj.receiver, 'profile') and obj.receiver.profile.student_photo:
            return request.build_absolute_uri(obj.receiver.profile.student_photo.url) if request else obj.receiver.profile.student_photo.url
        return "/static/assets/dist/images/def_user.jpg"
    
    def get_is_sent(self, obj):
        """Check if the logged-in user is the sender."""
        request = self.context.get("request")
        return obj.sender == request.user


class CustomUser_Serializer(serializers.ModelSerializer):
    student_photo = serializers.SerializerMethodField()
    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'username', 'email','student_photo'] 

    def get_student_photo(self, obj):
        if hasattr(obj, 'profile') and obj.profile.student_photo:
            return obj.profile.student_photo.url
        return None