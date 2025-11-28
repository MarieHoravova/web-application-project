import sqlite3
from typing import Dict, Any, List, Optional

from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST

from repositories.ContactMessageRepository import(
    create_contact_message as repo_create_contact_message,
    get_contact_message_by_id as repo_get_contact_message_by_id,
    list_contact_messages as repo_list_contact_messages,
)



class ContactMessageService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_contact_message(self, name: str, email: str, message: str):
        return repo_create_contact_message(self.conn, name, email, message)

    def get_contact_message_by_id(self, msg_id: int) -> Optional[Dict[str, Any]]:
        return repo_get_contact_message_by_id(self.conn, msg_id)

    def list_contact_messages(self, current_user_role: int, name: Optional[str] = None) -> List[Dict[str, Any]]:
        if current_user_role not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
            raise PermissionError("Pouze admin nebo recepce mohou zobrazit zprávy z kontaktu")
        return repo_list_contact_messages(self.conn, name=name)