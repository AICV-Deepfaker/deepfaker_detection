from contextlib import contextmanager
from contextvars import ContextVar

from sqlmodel.orm.session import Session


__all__ = ['CRUDBase']
class CRUDBase:
    _is_atomic: ContextVar[bool] = ContextVar("is_atomic", default=False)

    @classmethod
    @contextmanager
    def atomic(cls, db: Session):
        """
        ```python
        with CRUDTable.atomic(db):
            CRUDTable.xxx()
            CRUDAnother.yyy()
        # Data commited here, after context finished
        ```
        """
        if cls._is_atomic.get():
            yield # do nothing
            return

        token = cls._is_atomic.set(True)
        try:
            yield
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            cls._is_atomic.reset(token)

    @classmethod
    def commit_or_flush(cls, db:Session):
        if cls._is_atomic.get():
            db.flush()
        else:
            db.commit()
