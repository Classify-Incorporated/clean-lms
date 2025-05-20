# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from django.utils.timezone import now, localtime
from datetime import datetime
import base64
import uuid
from django.core.files.base import ContentFile
from asgiref.sync import sync_to_async
import mimetypes

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close()
            return
    
        self.receiver_id = self.scope['url_route']['kwargs']['receiver_id']
        self.sender_id = str(self.scope['user'].id)

        ids_sorted = sorted([self.sender_id, self.receiver_id])
        self.room_group_name = f"chat_{ids_sorted[0]}_{ids_sorted[1]}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.set_user_online(self.sender_id)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'presence_update',
                'user_id': self.sender_id,
                'is_online': True
            }
        )

    async def disconnect(self, code):
        await self.set_user_offline(self.sender_id)
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)


        await self.channel_layer.group_send(
            
            self.room_group_name,
            {
                'type': 'presence_update',
                'user_id': self.sender_id,
                'is_online': False,
                "last_seen": now().isoformat()
            }
        )

    @database_sync_to_async
    def get_user_photo(self, user_id):
        from accounts.models import Profile
        try:
            profile = Profile.objects.get(user_id=user_id)
            if profile.student_photo:
                return profile.student_photo.url
        except Profile.DoesNotExist:
            pass
        return "/static/assets/img/def_user.jpg"


    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
       
        message_type = data.get("type")

        if message_type == "ping":
            return

        # 🔹 Case 1: Read Receipt (just update messages as read)
        if message_type == "read_receipt":
            read_ids = await self.mark_messages_as_read()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'read_receipt_notify',
                    'reader_id': self.sender_id,
                    'receiver_id': self.receiver_id,
                    'read_ids': read_ids,
                }
            )
            return
        
        # 🔹 Case 2: Typing Indicator
        if message_type in ["typing", "stop_typing"]:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'user_id': self.sender_id,
                    'is_typing': message_type == "typing"
                }
            )
            return

        
        # 🔹 Case 3: Delete Message
        if message_type == "delete_message":
            message_id = data.get("message_id")
            deleted = await self.delete_message(self.sender_id, message_id)
            if deleted:
                deleted_by_name = self.scope["user"].get_full_name() or "Someone"
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_deleted',
                        'message_id': message_id,
                        'deleter_id': self.sender_id,
                        'deleted_by_name': deleted_by_name
                    }
                )
            return
        

        # 🔹 Case 4: Edit Message
        if message_type == "edit_message":
            message_id = data.get("message_id")
            new_message = data.get("message")
            chat_message = await self.edit_message(message_id, new_message, self.scope["user"])
            if chat_message:
                reply_to = await self.get_reply_info(chat_message)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "message_edited",
                        "message_id": chat_message.id,
                        "new_message": chat_message.message,
                        "sender_id": self.sender_id,
                        "reply_to": reply_to
                    }
                )
            return
        
        if message_type == "add_reaction":
            message_id = data.get("message_id")
            emoji = data.get("emoji")
            await self.add_reaction(message_id, self.scope["user"], emoji)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "reaction_added",
                    "message_id": message_id,
                    "user_id": self.sender_id,
                    "emoji": emoji,
                }
            )
            return

        
        # 🔹 Case 6: Send Message
        message = data.get('message')
        file_data = data.get('file', None)
        reply_to_id = data.get('reply_to')

        chat_data = {
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message": message,
        }

        if not message and not file_data:
            return

        if file_data:
            file_name = file_data.get("name")
            forbidden_extensions = ['exe', 'bat', 'sh', 'cmd', 'js', 'jar', 'msi']
            file_content = file_data.get("data")

            if any(file_name.lower().endswith(ext) for ext in forbidden_extensions):
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": f"❌ Uploading '.{file_name.split('.')[-1]}' files is not allowed."
                }))
                return
            
            mime_type, _ = mimetypes.guess_type(file_name)
            if mime_type is None or mime_type.startswith('application/x-msdownload'):
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "❌ Unsupported file type."
                }))
                return
    
            if file_content and file_name:
                try:
                    file_str = file_content.split(';base64,')[1]
                    decoded_file = base64.b64decode(file_str)
                    file_name_with_uuid = f"{uuid.uuid4().hex}_{file_name}"
                    chat_data["file"] = ContentFile(decoded_file, name=file_name_with_uuid)
                except Exception as e:
                    await self.send(text_data=json.dumps({
                        "type": "error",
                        "message": "❌ Failed to process the file upload."
                    }))
                    return

        # Save the message and get user photos
        chat = await self.save_message(self.sender_id, self.receiver_id, message, chat_data.get("file"), reply_to_id)
        sender_photo = await self.get_user_photo(self.sender_id)

        sender_name = self.scope["user"].get_full_name() or self.scope["user"].username

        try:
            file_url = chat.file.url if chat.file else None
        except ValueError:
            file_url = None

        # Broadcast the message to the WebSocket group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': chat.id,
                'message': chat.message,
                'sender_id': self.sender_id,
                'receiver_id': self.receiver_id,
                'timestamp': chat.created_at.isoformat(),
                'sender_photo': sender_photo,
                'sender_name': sender_name,
                'file': file_url,  # ✅ send actual file URL
                'file_type': chat.file.name.split('.')[-1] if chat.file else None,
                'is_image': chat.file.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')) if chat.file else False,
                "reply_to": await self.get_reply_info(chat)
            }
        )

        await self.channel_layer.group_send(
            f"notify_{self.receiver_id}",
            {
                "type": "notify_message",
                "message": message or "[Attachment]",
                "sender_id": self.sender_id,
                "sender_name": sender_name,
                "unread_count": await self.get_unread_count(self.receiver_id, self.sender_id)
            }
        )


    async def chat_message(self, event):

        timestamp = event['timestamp']
    
        # Convert to local time if it's a datetime string
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                pass  # fallback to original

        formatted_time = localtime(timestamp).strftime('%I:%M %p') if isinstance(timestamp, datetime) else timestamp

        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message_id': event['message_id'],
            'message': event['message'],
            'sender_id': event['sender_id'],
            'receiver_id': event['receiver_id'],
            'formatted_time': formatted_time,
            'sender_photo': event['sender_photo'],
            'sender_name': event['sender_name'],
            'file': event.get('file'),
            'file_type': event.get('file_type'),
            'is_image': event.get('is_image'),
            'reply_to': event.get('reply_to')
        }))

    async def reaction_added(self, event):
        await self.send(text_data=json.dumps({
            "type": "reaction_added",
            "message_id": event["message_id"],
            "user_id": event["user_id"],
            "emoji": event["emoji"]
        }))


    async def read_receipt_notify(self, event):
        if str(self.scope["user"].id) == event["reader_id"]:
            return 
        
        await self.send(text_data=json.dumps({
            'type': 'read_receipt_notify',
            'reader_id': event['reader_id'],
            'receiver_id': event['receiver_id'],
            'read_ids': event['read_ids'],
        }))

    async def presence_update(self, event):
        response = {
            'type': 'presence_update',
            'user_id': event['user_id'],
            'is_online': event['is_online'],
        }

        # Only add last_seen if it's included
        if 'last_seen' in event:
            response['last_seen'] = event['last_seen']

        await self.send(text_data=json.dumps(response))

    async def typing_indicator(self, event):
        # Only send typing event to the receiver
        if str(self.scope["user"].id) == event["user_id"]:
            return

        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'is_typing': event['is_typing']
        }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            "type": "message_deleted",
            "message_id": event["message_id"],
            "deleter_id": event["deleter_id"],
            "deleted_by_name": event["deleted_by_name"],
        }))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps({
            "type": "message_edited",
            "message_id": event["message_id"],
            "new_message": event["new_message"],
            "sender_id": event["sender_id"],
            "reply_to": event.get("reply_to")
        }))


    @database_sync_to_async
    def delete_message(self, sender_id, message_id):
        from .models import Chat
        try:
            message = Chat.objects.get(id=message_id, sender_id=sender_id)
            message.is_deleted = True
            message.save()
            return True
        except Chat.DoesNotExist:
            return False
        
    @database_sync_to_async
    def edit_message(self, message_id, new_text, user):
        from .models import Chat
        try:
            message = Chat.objects.get(id=message_id, sender=user, is_deleted=False)

            if message.sender.id != user.id:
                return None
        
            message.message = new_text
            message.is_edited = True  # ✅ Mark as edited
            message.save()
            return message
        except Chat.DoesNotExist:
            return None
        
    @database_sync_to_async
    def get_reply_info(self, chat):
        if chat.reply_to and chat.reply_to.sender:
            sender = chat.reply_to.sender
            return {
                'id': chat.reply_to.id,
                'message': chat.reply_to.message,
                'sender_name': sender.get_full_name() or sender.username
            }
        return None


    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, message, file=None, reply_to_id=None):
        from accounts.models import CustomUser
        from .models import Chat 

        sender = CustomUser.objects.get(id=sender_id)
        receiver = CustomUser.objects.get(id=receiver_id)
        reply_to = Chat.objects.filter(id=reply_to_id).first() if reply_to_id else None

        # Create new message
        chat = Chat.objects.create(sender=sender, receiver=receiver, message=message, file=file, reply_to=reply_to)

        # ✅ Restore deleted flags for the receiver (only!)
        # Chat.objects.filter(sender=sender, receiver=receiver, deleted_by_receiver=True).update(deleted_by_receiver=False)

        from .models import DeletedConversation
        DeletedConversation.objects.filter(user=receiver, other_user=sender).delete()

        return chat
    
    @database_sync_to_async
    def mark_messages_as_read(self):
        from .models import Chat
        unread = Chat.objects.filter(
            sender_id=self.receiver_id,
            receiver_id=self.sender_id,
            is_read=False,
            is_deleted=False
        )
        read_ids = list(unread.values_list('id', flat=True))
        unread.update(is_read=True)
        return read_ids
    

    @database_sync_to_async
    def set_user_online(self, user_id):
        cache.set(f'user_online_{user_id}', True, timeout=300)  # 5 mins TTL

    @database_sync_to_async
    def set_user_offline(self, user_id):
        cache.delete(f'user_online_{user_id}')

    @database_sync_to_async
    def get_unread_count(self, receiver_id, sender_id):
        from .models import Chat
        return Chat.objects.filter(
            sender_id=sender_id,
            receiver_id=receiver_id,
            is_read=False,
            is_deleted=False
        ).count()
    
    @database_sync_to_async
    def add_reaction(self, message_id, user, emoji):
        from .models import MessageReaction, Chat
        message = Chat.objects.get(id=message_id)

        # Delete any existing reaction by this user to the same message
        MessageReaction.objects.filter(message=message, user=user).delete()

        # Create new reaction
        MessageReaction.objects.create(message=message, user=user, emoji=emoji)



class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close()
            return

        self.user_id = str(self.scope["user"].id)
        self.group_name = f"notify_{self.user_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notify_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "notify_message",
            "message": event["message"],
            "sender_id": event["sender_id"],
            "sender_name": event["sender_name"],
            "unread_count": event.get("unread_count", 1)
        }))

    @database_sync_to_async
    def get_unread_count(self, receiver_id, sender_id):
        from .models import Chat
        return Chat.objects.filter(
            sender_id=sender_id,
            receiver_id=receiver_id,
            is_read=False,
            is_deleted=False
        ).count()
    


class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_id = self.scope["url_route"]["kwargs"]["group_id"]
        self.group_name = f"group_{self.group_id}"

        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close()
            return

        # Optional: validate if the user is a member of the group
        from .models import GroupChat
        group = await database_sync_to_async(GroupChat.objects.get)(id=self.group_id)
        if not await database_sync_to_async(group.members.filter(id=user.id).exists)():
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")  # 👈 Grab the type
        message = data.get("message")
        message_id = data.get("message_id")
        reply_to_id = data.get("reply_to")

        from .models import GroupChat, GroupMessage

        group = await database_sync_to_async(GroupChat.objects.get)(id=self.group_id)

        # 🔥 Handle deletion request
        if msg_type == "delete_message" and message_id:
            try:
                msg = await database_sync_to_async(GroupMessage.objects.get)(id=message_id, sender=self.scope["user"])
                msg.message = ""
                msg.file = None
                msg.is_deleted = True  
                msg.deleted_by = self.scope["user"]  # Store the user who deleted the message
                await database_sync_to_async(msg.save)()

                # Ensure that deleted_by_name is correctly set using `deleted_by.get_full_name()`
                deleted_by_name = msg.deleted_by.get_full_name() if msg.deleted_by else "Someone"

                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "group_message_deleted",
                        "message_id": message_id,
                        "deleted_by_name": deleted_by_name,  # Ensure this field is correctly set
                        "deleter_id": self.scope["user"].id, 
                        "group_id": self.group_id  
                    }
                )
            except GroupMessage.DoesNotExist:
                return
            return


        # 📝 Handle message edit
        if msg_type == "edit_message" and message_id:
            try:
                msg = await database_sync_to_async(GroupMessage.objects.get)(id=message_id, sender=self.scope["user"])
                msg.message = message
                msg.is_edited = True
                await database_sync_to_async(msg.save)()

                reply_to_data = None

                if await database_sync_to_async(lambda: msg.reply_to is not None)():
                    is_deleted = await database_sync_to_async(lambda: msg.reply_to.is_deleted)()
                    if not is_deleted:
                        reply_to_data = {
                            "id": msg.reply_to.id,
                            "message": msg.reply_to.message,
                            "sender_name": await database_sync_to_async(lambda: msg.reply_to.sender.get_full_name())(),
                        }

                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "message_edited",
                        "message_id": msg.id,
                        "new_message": message,
                        "sender_id": self.scope["user"].id,
                        "reply_to": reply_to_data,
                    }
                )
            except GroupMessage.DoesNotExist:
                return
            return

        
        if msg_type == "add_reaction":
            emoji = data.get("emoji")
            message_id = data.get("message_id")
            from .models import GroupMessageReaction

            try:
                message = await database_sync_to_async(GroupMessage.objects.get)(id=message_id)
            except GroupMessage.DoesNotExist:
                return

            # Remove previous reaction by this user if exists
            await database_sync_to_async(GroupMessageReaction.objects.filter(
                message=message, user=self.scope["user"]
            ).delete)()

            # Add new reaction
            reaction = await database_sync_to_async(GroupMessageReaction.objects.create)(
                message=message,
                user=self.scope["user"],
                emoji=emoji
            )

            # Broadcast to group
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "reaction_added",
                    "message_id": message_id,
                    "emoji": emoji,
                    "user_id": self.scope["user"].id
                }
            )
            return


        # 🆕 New message
        if not message and "file" not in data:
            return

         # ✅ Handle reply_to
        reply_to_instance = None
        if reply_to_id:
            try:
                reply_to_instance = await database_sync_to_async(GroupMessage.objects.get)(id=reply_to_id)
            except GroupMessage.DoesNotExist:
                reply_to_instance = None

        # ✅ Correct: only save once, with or without reply_to
        file_data = data.get("file")
        content_file = None
        file_url = None
        is_image = False

        if file_data:
            try:
                file_name = file_data["name"]
                file_type = file_data["type"]
                base64_str = file_data["data"].split(";base64,")[-1]
                decoded_file = base64.b64decode(base64_str)
                content_file = ContentFile(decoded_file, name=file_name)
                is_image = file_type.startswith("image/")
            except Exception as e:
                print("❌ File upload error:", e)

        # 💾 Save message
        msg = await database_sync_to_async(GroupMessage.objects.create)(
            group=group,
            sender=self.scope["user"],
            message=message,
            file=content_file,
            reply_to=reply_to_instance
        )


        sender_photo = await self.get_user_photo(self.scope["user"]) 

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "group_message",
                "message": message,
                "sender_id": self.scope["user"].id,
                "sender_name": self.scope["user"].get_full_name(),
                "sender_photo": sender_photo,
                "timestamp": localtime(msg.created_at).strftime("%I:%M %p").lstrip("0"),
                "group_id": self.group_id,
                "message_id": msg.id,
                "is_sent": True,
                "file": msg.file.url if msg.file else None,         # ✅ Add this
                "is_image": is_image,  
                "reply_to": {
                    "id": reply_to_instance.id,
                    "message": reply_to_instance.message,
                    "sender_name": await database_sync_to_async(lambda: reply_to_instance.sender.get_full_name())(),
                } if reply_to_instance else None,       
             }
        )

        # 🔔 Notify other users
        for user in await database_sync_to_async(lambda: list(group.members.exclude(id=self.scope["user"].id)))():
            await self.channel_layer.group_send(
                f"notify_{user.id}",
                {
                    "type": "notify_message",
                    "message": f"{self.scope['user'].get_full_name()}: {message}",
                    "sender_id": self.scope["user"].id,
                    "sender_name": self.scope["user"].get_full_name(),
                    "group_id": self.group_id,
                    "unread_count": await self.get_unread_group_count(user.id, self.group_id)
                }
            )
            


    async def group_message(self, event):
        from .models import GroupMessage, DeletedGroupConversation
        from django.utils.timezone import localtime

        try:
            msg = await database_sync_to_async(GroupMessage.objects.get)(id=event["message_id"])
        except GroupMessage.DoesNotExist:
            return

        # ✅ Check if the current user deleted the conversation BEFORE this message
        deleted_at = await database_sync_to_async(
            lambda: DeletedGroupConversation.objects.filter(
                user=self.scope["user"], group_id=self.group_id
            ).values_list('deleted_at', flat=True).first()
        )()

        if deleted_at and msg.created_at <= deleted_at:
            return  # ⛔️ Don't send this old message to this user
        
        await self.send(text_data=json.dumps({
            "type": "group_message",
            "message": event["message"],
            "sender_id": event["sender_id"],
            "sender_name": event["sender_name"],
            "sender_photo": event.get("sender_photo"),
            "timestamp": event["timestamp"],
            "group_id": event["group_id"],  # ✅ not self.group_id
            "file": event.get("file"),
            "is_image": event.get("is_image"),
            "message_id": event["message_id"],
            "is_sent": True,
            "reply_to": event.get("reply_to")  # ✅ this is important
        }))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps({
            "type": "message_edited",
            "message_id": event["message_id"],
            "new_message": event["new_message"],
            "sender_id": event["sender_id"],
            "reply_to": event.get("reply_to") 
        }))

    async def group_message_deleted(self, event):
        from .models import GroupChat, GroupMessage

        # Get timestamp of the message (optional but useful for sidebar update)
        try:
            msg = await database_sync_to_async(GroupMessage.objects.get)(id=event["message_id"])
            timestamp = localtime(msg.created_at).strftime("%I:%M %p").lstrip("0")
        except GroupMessage.DoesNotExist:
            timestamp = ""

        await self.send(text_data=json.dumps({
            "type": "message_deleted",
            "message_id": event["message_id"],
            "deleted_by_name": event.get("deleted_by_name", "Someone"),
            "deleter_id": event.get("deleter_id"),  # ✅ Add this line
            "group_id": self.group_id,
            "formatted_time": timestamp
        }))

    async def reaction_added(self, event):
        await self.send(text_data=json.dumps({
            "type": "reaction_added",
            "message_id": event["message_id"],
            "emoji": event["emoji"],
            "user_id": event["user_id"]
        }))



    @database_sync_to_async
    def get_unread_group_count(self, user_id, group_id):
        from .models import GroupMessage
        return GroupMessage.objects.filter(group_id=group_id, is_read=False).exclude(sender_id=user_id).count()
    
    @database_sync_to_async
    def get_user_photo(self, user):
        try:
            profile = user.profile  # if you have OneToOne profile
            if profile.student_photo:
                return profile.student_photo.url
        except:
            pass
        return "/static/assets/img/def_user.jpg"

    