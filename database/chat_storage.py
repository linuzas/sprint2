import uuid
import json
from datetime import datetime

def create_new_chat(supabase, user_id, messages):
    existing = supabase.table("chats")\
        .select("id")\
        .eq("user_id", user_id)\
        .execute()

    chat_number = len(existing.data) + 1
    description = f"Chat {chat_number}"

    conversation_id = str(uuid.uuid4())
    supabase.table("chats").insert({
        "user_id": user_id,
        "conversation_id": conversation_id,
        "messages": json.dumps(messages),
        "description": description,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    return conversation_id

def update_existing_chat(supabase, conversation_id, messages):
    return supabase.table("chats").update({
        "messages": json.dumps(messages)
    }).eq("conversation_id", conversation_id).execute()

def load_chat(supabase, conversation_id):
    result = supabase.table("chats").select("messages").eq("conversation_id", conversation_id).single().execute()
    return json.loads(result.data["messages"]) if result.data else []

def list_user_chats(supabase, user_id):
    return supabase.table("chats")\
        .select("conversation_id, description, created_at")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True)\
        .execute().data or []

def delete_chat(supabase, conversation_id):
    return supabase.table("chats").delete().eq("conversation_id", conversation_id).execute()
