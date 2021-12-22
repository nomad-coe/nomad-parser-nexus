"""Test cases for readers used for the DataConverter"""

import glob
import importlib
from typing import List

import pytest

from nexusparser.tools.dataconverter.readers.base_reader import BaseReader


def get_reader(reader_name: str = None, reader_path: str = None) -> BaseReader:
    """Helper function to get the reader object from it's given name"""
    spec = importlib.util.spec_from_file_location(  # type: ignore[attr-defined]
        f"{reader_name}_reader.py", reader_path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[attr-defined]
    spec.loader.exec_module(module)
    return module.READER


def get_readers() -> List:
    """Helper function for parametrizing reader objects"""
    readers = []
    for reader_filename in get_readers_file_names():
        reader_name = reader_filename[reader_filename.rindex("/") + 1:-(len("_reader.py")):]
        readers.append(get_reader(reader_name, reader_filename))
    return readers


def get_readers_file_names() -> List[str]:
    """Helper function to parametrize paths of all the reader Python files"""
    return glob.glob("nexusparser/tools/dataconverter/readers/*.py")


@pytest.mark.parametrize("reader_filename", get_readers_file_names())
def test_is_valid_reader_name(reader_filename):
    """Test to check if all readers have a valid name"""
    assert reader_filename[-(len("_reader.py")):] == "_reader.py"


@pytest.mark.parametrize("reader", get_readers())
def test_if_readers_are_children_of_base_reader(reader):
    """Test to verify that all readers are children of BaseReader"""
    if reader.__name__ != "BaseReader":
        assert isinstance(reader(), BaseReader)


@pytest.mark.parametrize("reader", get_readers())
def test_has_correct_read_func(reader):
    """Test if all readers have a valid read function implemented"""
    assert callable(reader.read)
    if reader.__name__ != "BaseReader":
        read_data = reader().read(template={"henh": "2"}, file_paths=())
        assert isinstance(read_data, dict)