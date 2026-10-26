"""A local cap-transition trial must not change the ordinary default mesh."""

import pytest

from plush_pattern_lab.patterns.transition_profile import cap_offset_weight


def test_default_is_bitwise_identical_full_panel_offset():
    assert all(cap_offset_weight(j, 65, 0) == 1.0 for j in range(65))


@pytest.mark.parametrize("rows", [2, 4, 8])
def test_cap_transition_symmetric_and_unit_bounded(rows):
    values = [cap_offset_weight(j, 65, rows) for j in range(65)]
    assert values[0] == values[-1] == 0
    assert values[rows] == values[64 - rows] == 1
    assert values == pytest.approx(list(reversed(values)), abs=1e-15)
    assert all(0 <= value <= 1 for value in values)


@pytest.mark.parametrize("j,total,transition", [
    (0, 24, 4),
    (65, 65, 2),
    (-1, 65, 2),
    (10, 65, -1),
    (10, 65, 9),
    (True, 65, 2),
    (10, 65, False),
])
def test_reject_invalid_geometry_inputs(j, total, transition):
    with pytest.raises(ValueError):
        cap_offset_weight(j, total, transition)
