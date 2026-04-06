import os
import pytest
from PIL import Image


def test_get_image_dims_returns_width_and_height(tmp_path):
    path = str(tmp_path / 'test.jpg')
    Image.new('RGB', (300, 200), color='red').save(path)

    from helpers import get_image_dims
    w, h = get_image_dims(path)
    assert w == 300
    assert h == 200


def test_get_image_dims_returns_none_for_missing_file(tmp_path):
    from helpers import get_image_dims
    result = get_image_dims(str(tmp_path / 'nonexistent.jpg'))
    assert result == (None, None)


def test_get_image_dims_returns_none_for_corrupt_file(tmp_path):
    path = str(tmp_path / 'corrupt.jpg')
    with open(path, 'wb') as f:
        f.write(b'not an image')
    from helpers import get_image_dims
    assert get_image_dims(path) == (None, None)
