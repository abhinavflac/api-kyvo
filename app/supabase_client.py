from supabase import create_client
import os

def get_supabase():
    url = os.getenv("SUPABASE_URL", "https://cvxucebfdsaboqukemqb.supabase.co")
    key = os.getenv("SUPABASE_KEY", "sb_publishable_6-vilPYxlWpMdQBtJMlwig_9TTJv-kI")
    return create_client(url, key)