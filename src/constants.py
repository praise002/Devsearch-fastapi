from enum import Enum


class VoteType(Enum):
    up = "Up Vote"
    down = "Down Vote"
    
class UserRole(Enum):
    user = "User"
    admin = "Admin"

