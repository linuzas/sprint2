import json
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime
import re
import streamlit as st
import os
# Load environment variables


SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

### -------------------------------------------
### ✅ USER FUNCTIONS
### -------------------------------------------

def get_user(username: str):
    """
    Retrieve a user record from Supabase by username.
    Args:
        username (str): The username to look up.
    Returns:
        dict: User record or None if not found.
    """
    response = supabase.table("users").select("*").eq("username", username).execute()
    if response.data:
        return response.data[0]
    return None


def save_user(username: str, password: str):
    """
    Insert a new user into the 'users' table.
    Args:
        username (str): The user's username.
        password (str): The user's hashed password.
    """
    data = {
        "username": username,
        "password": password,
        "created_at": "now()"
    }
    response = supabase.table("users").insert(data).execute()
    return response


def get_user_id(username: str):
    """
    Get the user ID based on the username.
    Args:
        username (str): The username to look up.
    Returns:
        UUID: User ID or None if not found.
    """
    response = supabase.table("users").select("id").eq("username", username).execute()
    if response.data:
        return response.data[0]["id"]
    return None


def delete_user(username: str):
    """
    Delete a user from the 'users' table.
    Args:
        username (str): The username to delete.
    """
    response = supabase.table("users").delete().eq("username", username).execute()
    return response


### -------------------------------------------
### ✅ CHAT FUNCTIONS
### -------------------------------------------

def save_chat(user_id: str, expert_type: str, messages, description: str):
    """
    Save a new chat into the 'chats' table.
    Args:
        user_id (str): The ID of the user.
        expert_type (str): Type of expert.
        messages (list): List of messages (user + assistant).
        description (str): Short description of the chat.
    Returns:
        dict: The saved chat record.
    """
    data = {
        "user_id": user_id,
        "expert_type": expert_type,
        "messages": json.dumps(messages),
        "description": description,
        "timestamp": "now()"  # Save current timestamp
    }
    response = supabase.table("chats").insert(data).execute()
    return response


def get_user_chats(user_id: str):
    """
    Retrieve all chats for a specific user.
    Args:
        user_id (str): The ID of the user.
    Returns:
        list: List of chat records.
    """
    response = supabase.table("chats").select("*").eq("user_id", user_id).order("timestamp", desc=True).execute()
    return response.data


def update_chat(chat_id: int, updates: dict):
    """
    Update an existing chat in the 'chats' table.
    Args:
        chat_id (int): The ID of the chat to update.
        updates (dict): The fields to update.
    """
    response = supabase.table("chats").update(updates).eq("id", chat_id).execute()
    return response


def delete_chat(chat_id: int):
    """
    Delete a chat by ID.
    Args:
        chat_id (int): The ID of the chat to delete.
    """
    response = supabase.table("chats").delete().eq("id", chat_id).execute()
    return response


    return True
def create_new_chat_session(user_id: str, expert_type: str = "crypto", messages: list = None, description: str = ""):
    """
    Create a new empty chat session and return its ID.
    """
    import uuid
    from datetime import datetime

    if messages is None:
        messages = []

    # Auto-number chat based on existing chats
    existing = supabase.table("chats")\
        .select("id")\
        .eq("user_id", user_id)\
        .execute()

    chat_number = len(existing.data) + 1
    chat_title = description or f"Chat {chat_number}"

    chat_id = str(uuid.uuid4())
    data = {
        "id": chat_id,
        "user_id": user_id,
        "expert_type": expert_type,
        "messages": json.dumps(messages),
        "description": chat_title,
        "timestamp": datetime.utcnow().isoformat()
    }
    response = supabase.table("chats").insert(data).execute()
    return chat_id, response

def load_chat_messages(chat_id: str):
    """
    Load messages from a specific chat session.
    """
    result = supabase.table("chats").select("messages").eq("id", chat_id).single().execute()
    return json.loads(result.data["messages"]) if result.data and "messages" in result.data else []


def update_chat_messages(chat_id: str, messages: list):
    """
    Update the messages in an existing chat.
    """
    return supabase.table("chats").update({
        "messages": json.dumps(messages)
    }).eq("id", chat_id).execute()

def restore_user_session(supabase_client, access_token, refresh_token):
    """
    Re-authenticate user session with Supabase to enable RLS access.
    """
    supabase_client.auth.set_session(
        access_token=access_token,
        refresh_token=refresh_token
    )

def create_new_chat_session(user_id: str, expert_type: str = "crypto", messages: list = None, description: str = ""):
    import uuid
    from datetime import datetime

    if messages is None:
        messages = []

    chat_id = str(uuid.uuid4())

    data = {
        "id": chat_id,
        "conversation_id": chat_id,  # ✅ REQUIRED to satisfy NOT NULL constraint
        "user_id": user_id,
        "expert_type": expert_type,
        "messages": json.dumps(messages),
        "description": description or "New chat",
        "created_at": datetime.utcnow().isoformat()
    }

    response = supabase.table("chats").insert(data).execute()
    return chat_id, response

def get_api_key_for_user(user_id):
    """Get active API key for a user."""
    result = supabase.table("api_keys")\
        .select("api_key, is_active, used, quota")\
        .eq("user_id", user_id)\
        .eq("is_active", True)\
        .single()\
        .execute()

    if result.data:
        return result.data["api_key"]
    return None

