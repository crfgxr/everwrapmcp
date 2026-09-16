from experiments.baseline import CASES

def test_cases_have_unique_names():
    assert len({case[0] for case in CASES}) == len(CASES)

def test_leak_checks_are_present_in_inputs():
    for _, source, forbidden in CASES:
        assert all(value in source for value in forbidden)

def test_utility_control_exists():
    assert any(not forbidden for _, _, forbidden in CASES)
