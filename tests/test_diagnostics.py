import pytest
from bridge.diagnostics import run_diagnostic,ALLOWED_OPERATIONS
@pytest.mark.parametrize("op",sorted(ALLOWED_OPERATIONS))
def test_allowed_ops(op):assert isinstance(run_diagnostic(op),dict)
def test_no_shell():
 with pytest.raises(ValueError):run_diagnostic("shell",{"command":"id"})
def test_no_args():
 with pytest.raises(ValueError):run_diagnostic("system_info",{"x":1})
