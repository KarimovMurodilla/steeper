"""
This module centralizes the imports for all models to ensure that
relationships between them are properly registered and work seamlessly.
It serves as an entry point for the application's ORM to recognize and manage
table relationships effectively.
"""

# Import all models here

from src.analytics.models import AuditLog as AuditLog
from src.bot.models import AdminBotRole as AdminBotRole, Bot as Bot
from src.communication.models import Chat as Chat, Message as Message
from src.crm.models import TelegramUser as TelegramUser
from src.marketing.models import (
    Broadcast as Broadcast,
    BroadcastDelivery as BroadcastDelivery,
)
from src.user.models import User as User  # Re-export the User model explicitly
from src.workspace.models import Workspace as Workspace
from src.workspace.models import WorkspaceMember as WorkspaceMember
