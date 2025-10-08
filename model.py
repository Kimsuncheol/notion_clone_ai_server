from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal, Union
from datetime import datetime
from enum import Enum

class Message(BaseModel):
    role: str
    content: str
    # updatedAt: datetime | None = None


class SummaryChatRequest(BaseModel):
    content: str
    chat_history: List[Message]

class EmailNotification(BaseModel):
    comment_notification: bool
    like_notification: bool


class Appearance(BaseModel):
    appearance: Literal['light', 'dark', 'system']


class UserSettings(BaseModel):
    display_name: Optional[str] = None
    short_bio: Optional[str] = None
    email: str
    github: str
    email_notification: EmailNotification
    appearance: Appearance
    my_notes_title: str


class LikeUser(BaseModel):
    id: str
    uid: str
    email: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    bio: Optional[str] = None
    joined_at: datetime


class SkillsType(BaseModel):
    id: str
    name: str
    title: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class TagType(BaseModel):
    id: str
    user_id: Optional[List[str]] = None
    name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Comment(BaseModel):
    id: str
    parent_comment_id: Optional[str] = None
    note_id: str
    author: str
    author_email: str
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    comments: Optional[List['Comment']] = None


class MySeries(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class FirebaseNoteContent(BaseModel):
    id: str
    page_id: str
    title: str
    content: str
    description: Optional[str] = None
    tags: Optional[List[TagType]] = None
    series: Optional[MySeries] = None
    author_id: str
    author_email: Optional[str] = None
    author_name: Optional[str] = None
    is_public: Optional[bool] = None
    is_published: Optional[bool] = None
    thumbnail_url: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    like_users: Optional[List[LikeUser]] = None
    original_location: Optional[Dict[str, bool]] = None
    comments: Optional[List[Comment]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    recently_open_date: Optional[datetime] = None


class CustomUserProfile(BaseModel):
    id: str
    user_id: str
    email: str
    bio: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    skills: Optional[List[SkillsType]] = None
    liked_notes: Optional[List[FirebaseNoteContent]] = None
    recently_read_notes: Optional[List[FirebaseNoteContent]] = None
    tags: Optional[List[TagType]] = None
    series: Optional[List[MySeries]] = None
    followers_count: int
    followers: Optional[List['CustomUserProfile']] = None
    following_count: int
    following: Optional[List['CustomUserProfile']] = None
    post_count: int
    joined_at: datetime
    updated_at: Optional[datetime] = None
    uid: str
    email_verified: bool
    is_anonymous: bool
    phone_number: Optional[str] = None
    photo_url: Optional[str] = None
    provider_id: str
    introduction: Optional[str] = None
    user_settings: Optional[UserSettings] = None
    # Firebase UserProfile fields
    display_name: Optional[str] = None


class MyPostComment(BaseModel):
    id: str
    text: str
    author: str
    author_email: str
    timestamp: datetime


class MyPost(BaseModel):
    id: str
    title: str
    thumbnail: str
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    recently_open_date: Optional[datetime] = None
    description: Optional[str] = None
    author_email: str
    author_name: str
    is_published: bool
    trashed_at: datetime
    comments: List[MyPostComment]
    # From FirebaseNoteContent
    tags: Optional[List[TagType]] = None
    series: Optional[MySeries] = None
    author_id: str
    thumbnail_url: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    like_users: Optional[List[LikeUser]] = None


class PublicNote(BaseModel):
    id: str
    title: str
    author_id: str
    author_email: Optional[str] = None
    author_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    publish_content: Optional[str] = None
    thumbnail: Optional[str] = None
    is_published: Optional[bool] = None
    tags: Optional[List[TagType]] = None


class FavoriteNote(BaseModel):
    id: str
    author_id: str
    note_id: str  # Parent note ID
    note_title: str  # Parent note title
    added_at: datetime


class FileUploadProgress(BaseModel):
    progress: int = Field(..., ge=0, le=100)  # 0-100
    download_url: Optional[str] = None
    error: Optional[str] = None


class TrendingItem(BaseModel):
    id: str
    title: str
    description: str
    image_url: Optional[str] = None
    category: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    author_avatar: Optional[str] = None
    tags: Optional[List[str]] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None


class TagTypeForTagsCollection(TagType):
    notes: List[FirebaseNoteContent]
    post_count: int


class DraftedNote(BaseModel):
    id: str
    title: str
    content: str
    author_id: str
    author_email: str
    author_name: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    tags: Optional[List[TagType]] = None


class SmallTabbarItem(BaseModel):
    label: str
    value: str
    path: Optional[str] = None


class SupportConversation(BaseModel):
    id: str
    type: Literal['contact', 'bug', 'feedback']
    user_email: str
    user_name: str
    user_id: str
    status: Literal['active', 'closed']
    last_message: str
    last_message_at: datetime
    created_at: datetime
    unread_count: int  # For admin to track unread messages
    typing: Optional[List[str]] = None  # user emails
    admin_present: Optional[bool] = None
    admin_last_seen: Optional[datetime] = None


class SupportMessage(BaseModel):
    id: str
    conversation_id: str
    text: str
    sender: Literal['user', 'admin', 'system']
    sender_email: str
    sender_name: str
    timestamp: datetime
    is_read: bool


class NotificationItem(BaseModel):
    id: str
    user_id: str
    type: Literal['workspace_invitation', 'member_added', 'member_removed', 'role_changed']
    title: str
    message: str
    data: Dict[str, Any]
    is_read: bool
    created_at: datetime


class FollowRelationship(BaseModel):
    follower_id: str  # User who is following
    following_id: str  # User being followed
    follower_email: str
    following_email: str
    follower_name: str
    following_name: str
    created_at: datetime


# Enable forward references for self-referencing models
Comment.model_rebuild()
CustomUserProfile.model_rebuild()