import pytest

from tagwerk.contracts import NAMES, ContractError, fixture, validate


@pytest.mark.parametrize("name", NAMES)
def test_fixture_matches_contract(name):
    validate(name, fixture(name))


def test_bad_data_rejected():
    bad = fixture("structured")
    bad["work_done"][0]["evidence"] = "rumour"
    with pytest.raises(ContractError):
        validate("structured", bad)
