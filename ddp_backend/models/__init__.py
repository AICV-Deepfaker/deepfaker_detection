from .models import (
    Result,
    Source,
    Token,
    Video,
)

from .alert import Alert
from .user import User
from .report import DeepReport, FastReport

for next_model in [DeepReport, FastReport, Result, Source, Token, Video, Alert, User]:
    next_model.model_rebuild()

__all__ = [
    'Alert',
    'DeepReport',
    'FastReport',
    'Result',
    'Source',
    'Token',
    'User',
    'Video',
]