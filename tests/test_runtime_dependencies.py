import fastmcp


def test_fastmcp_import():
    assert fastmcp is not None
    assert hasattr(fastmcp, "__version__")
    assert isinstance(fastmcp.__version__, str)
    assert len(fastmcp.__version__) > 0
