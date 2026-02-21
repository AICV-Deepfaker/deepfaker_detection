import shutil
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import UploadFile


@contextmanager
def save_temp_file(upload_file: UploadFile):
    assert upload_file.filename is not None
    filename = Path(upload_file.filename)
    with TemporaryDirectory() as temp_dir:
        temp_path = temp_dir / filename
        with open(temp_path, "wb") as temp_file:
            shutil.copyfileobj(upload_file.file, temp_file)

        yield temp_path
