from datetime import datetime, timezone
import json
import os
import threading
from typing import Dict, List, Optional

from .models import UserCreate, UserInDB, UserResponse, UserRole, UserUpdate
from .security import hash_password


class UserStore:
    """
    Thread-safe storage for User accounts with initial seeding and persistence.
    """

    def __init__(self, storage_file: Optional[str] = None):
        self._lock = threading.Lock()
        self._users_by_id: Dict[str, UserInDB] = {}
        self._users_by_username: Dict[str, UserInDB] = {}
        self._storage_file = storage_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "users.json"
        )
        self._seed_default_users()

    def _seed_default_users(self):
        """Seed default prototype users if store is empty."""
        with self._lock:
            if self._users_by_id:
                return

            # Default demo credentials (safely hashed via PBKDF2)
            default_seeds = [
                {
                    "user_id": "USR-001",
                    "username": "mospi_officer",
                    "email": "officer.mplads@mospi.gov.in",
                    "full_name": "Dr. Rajeshwar Sharma, IAS",
                    "role": UserRole.MOSPI_OFFICER,
                    "assigned_district": None,
                    "assigned_state": None,
                    "password_raw": "MoSPI@2026",
                    "created_at": datetime(2026, 1, 15, 9, 0, 0, tzinfo=timezone.utc),
                },
                {
                    "user_id": "USR-002",
                    "username": "district_officer_04",
                    "email": "collector.district04@nic.in",
                    "full_name": "Smt. Ananya Deshmukh, IAS",
                    "role": UserRole.DISTRICT_AUTHORITY,
                    "assigned_district": "District-04",
                    "assigned_state": "Maharashtra",
                    "password_raw": "District@2026",
                    "created_at": datetime(2026, 2, 1, 10, 30, 0, tzinfo=timezone.utc),
                },
                {
                    "user_id": "USR-003",
                    "username": "admin_user",
                    "email": "sysadmin.mplads@gov.in",
                    "full_name": "System Administrator",
                    "role": UserRole.ADMIN,
                    "assigned_district": None,
                    "assigned_state": None,
                    "password_raw": "Admin@2026",
                    "created_at": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                },
            ]

            for s in default_seeds:
                hashed, salt = hash_password(s["password_raw"])
                u = UserInDB(
                    user_id=s["user_id"],
                    username=s["username"],
                    email=s["email"],
                    full_name=s["full_name"],
                    role=s["role"],
                    assigned_district=s["assigned_district"],
                    assigned_state=s["assigned_state"],
                    is_active=True,
                    hashed_password=hashed,
                    salt=salt,
                    created_at=s["created_at"],
                )
                self._users_by_id[u.user_id] = u
                self._users_by_username[u.username.lower()] = u

    def get_by_id(self, user_id: str) -> Optional[UserInDB]:
        with self._lock:
            return self._users_by_id.get(user_id)

    def get_by_username(self, username: str) -> Optional[UserInDB]:
        with self._lock:
            return self._users_by_username.get(username.strip().lower())

    def list_all(self) -> List[UserResponse]:
        with self._lock:
            return [
                UserResponse(
                    user_id=u.user_id,
                    username=u.username,
                    email=u.email,
                    full_name=u.full_name,
                    role=u.role,
                    assigned_district=u.assigned_district,
                    assigned_state=u.assigned_state,
                    is_active=u.is_active,
                    created_at=u.created_at,
                )
                for u in sorted(self._users_by_id.values(), key=lambda x: x.created_at)
            ]

    def create_user(self, payload: UserCreate) -> UserResponse:
        with self._lock:
            username_norm = payload.username.strip().lower()
            if username_norm in self._users_by_username:
                raise ValueError(f"Username '{payload.username}' already exists.")

            user_id = f"USR-{len(self._users_by_id) + 1:03d}"
            hashed, salt = hash_password(payload.password)
            now = datetime.now(timezone.utc)

            u = UserInDB(
                user_id=user_id,
                username=payload.username.strip(),
                email=payload.email.strip(),
                full_name=payload.full_name.strip(),
                role=payload.role,
                assigned_district=payload.assigned_district if payload.role == UserRole.DISTRICT_AUTHORITY else None,
                assigned_state=payload.assigned_state if payload.role == UserRole.DISTRICT_AUTHORITY else None,
                is_active=payload.is_active,
                hashed_password=hashed,
                salt=salt,
                created_at=now,
            )

            self._users_by_id[u.user_id] = u
            self._users_by_username[username_norm] = u

            return UserResponse(
                user_id=u.user_id,
                username=u.username,
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                assigned_district=u.assigned_district,
                assigned_state=u.assigned_state,
                is_active=u.is_active,
                created_at=u.created_at,
            )

    def update_user(self, user_id: str, payload: UserUpdate) -> Optional[UserResponse]:
        with self._lock:
            u = self._users_by_id.get(user_id)
            if not u:
                return None

            if payload.full_name is not None:
                u.full_name = payload.full_name.strip()
            if payload.email is not None:
                u.email = payload.email.strip()
            if payload.role is not None:
                u.role = payload.role
                if u.role != UserRole.DISTRICT_AUTHORITY:
                    u.assigned_district = None
                    u.assigned_state = None
            if payload.assigned_district is not None and u.role == UserRole.DISTRICT_AUTHORITY:
                u.assigned_district = payload.assigned_district
            if payload.assigned_state is not None and u.role == UserRole.DISTRICT_AUTHORITY:
                u.assigned_state = payload.assigned_state
            if payload.is_active is not None:
                u.is_active = payload.is_active
            if payload.password:
                hashed, salt = hash_password(payload.password)
                u.hashed_password = hashed
                u.salt = salt

            return UserResponse(
                user_id=u.user_id,
                username=u.username,
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                assigned_district=u.assigned_district,
                assigned_state=u.assigned_state,
                is_active=u.is_active,
                created_at=u.created_at,
            )

    def delete_user(self, user_id: str) -> bool:
        with self._lock:
            u = self._users_by_id.pop(user_id, None)
            if u:
                self._users_by_username.pop(u.username.lower(), None)
                return True
            return False


# Global singleton instance
_USER_STORE: Optional[UserStore] = None


def get_user_store() -> UserStore:
    global _USER_STORE
    if _USER_STORE is None:
        _USER_STORE = UserStore()
    return _USER_STORE
