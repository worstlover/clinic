# messages/serializers.py

from rest_framework import serializers
from .models import Message, MessageRecipient, MessageAttachment
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class MessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttachment
        fields = ['id', 'file', 'file_name', 'uploaded_at']

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True) # برای نمایش پیوست‌ها

    class Meta:
        model = Message
        fields = ['id', 'sender', 'subject', 'body', 'created_at', 'parent_message',
                  'related_visit', 'related_drug_request', 'attachments']

class MessageRecipientSerializer(serializers.ModelSerializer):
    message = MessageSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)

    class Meta:
        model = MessageRecipient
        fields = ['id', 'message', 'recipient', 'is_read', 'read_at']