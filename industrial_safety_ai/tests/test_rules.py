from rules import normalize_class_name, get_event_rule, is_loggable_incident


def test_normalize_aliases():
    assert normalize_class_name("no hardhat") == "no_helmet"
    assert normalize_class_name("No-Hardhat") == "no_helmet"
    assert normalize_class_name("safety vest") == "safety_vest"
    assert normalize_class_name("person") == "person"


def test_normalize_unknown_label_passes_through():
    assert normalize_class_name("forklift") == "forklift"


def test_fire_is_critical():
    rule = get_event_rule("fire")
    assert rule["severity"] == "Critical"


def test_person_is_not_loggable():
    assert not is_loggable_incident("person")


def test_no_helmet_is_loggable():
    assert is_loggable_incident("no_helmet")
