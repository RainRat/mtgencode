from lib.cardlib import Card

def test_station_false_positive_substring():
    # Words containing 'station' should not trigger the 'Station' mechanic
    texts = [
        "This is a manifestation of power.",
        "The devastation was absolute.",
        "Aestation is not a word but tests the prefix.",
        "Playing with fire leads to workstation safety issues."
    ]
    for text in texts:
        card = Card({"name": "Test", "types": ["Sorcery"], "text": text})
        assert "Station" not in card.mechanics, f"Incorrectly found 'Station' in: {text}"

def test_station_true_positive_boundaries():
    # 'Station' as a standalone word (with punctuation) should be detected
    texts = [
        "Station.",
        "When this enters, Station.",
        "Activate: Station - Draw a card.",
        "The Station is open."
    ]
    for text in texts:
        card = Card({"name": "Test", "types": ["Artifact"], "text": text})
        assert "Station" in card.mechanics, f"Failed to find 'Station' in: {text}"

def test_station_artifact_validation_robustness():
    # Artifacts with 'manifestation' in text should NOT be exempt from P/T check
    # because they don't have the 'Station' mechanic.
    card_json = {
        "name": "Manifestation Artifact",
        "types": ["Artifact"],
        "text": "This is a manifestation."
        # No PT
    }
    # Should be valid (artifacts don't need PT usually)
    card = Card(card_json)
    assert card.valid

    # However, if it were somehow a creature but missing PT,
    # it shouldn't be saved by the 'station' loophole if it's just 'manifestation'.
    # Note: Artifact Creature needs PT.
    card_json_creature = {
        "name": "Manifestation Creature",
        "types": ["Artifact", "Creature"],
        "text": "This is a manifestation."
        # Missing PT
    }
    card_creature = Card(card_json_creature)
    assert not card_creature.valid, "Artifact creature without PT was incorrectly validated due to 'manifestation' substring."

def test_station_artifact_validation_true_loophole():
    # True Station artifacts ARE exempt from P/T check if they are NOT creatures.
    # Actually, the logic in fields_check_valid says:
    # if iscreature: needs PT.
    # elif isartifact and 'station' in text: pass (valid without PT)
    # else: if has PT: invalid.

    # So an Artifact (non-creature) with 'station' is valid without PT (normal anyway)
    # The loophole is more about allowing them to exist without being flagged as invalid
    # if they have P/T? No, wait.

    # Let's re-read the logic:
    # if iscreature:
    #    if field_pt not in fields: return False
    # elif isartifact and 'station' in text:
    #    pass
    # else:
    #    if field_pt in fields: return False

    # This means a Station Artifact (non-creature) is allowed to HAVE P/T.
    card_json_with_pt = {
        "name": "Summoning Station",
        "types": ["Artifact"],
        "text": "Station.",
        "power": "2",
        "toughness": "2"
    }
    card = Card(card_json_with_pt)
    assert card.valid, "Station artifact with PT should be valid."

    # A non-Station artifact with PT should be INVALID.
    card_json_normal_with_pt = {
        "name": "Sol Ring",
        "types": ["Artifact"],
        "text": "Add {C}{C}.",
        "power": "0",
        "toughness": "1"
    }
    card_normal = Card(card_json_normal_with_pt)
    assert not card_normal.valid, "Normal artifact with PT should be invalid."

    # A manifestation artifact with PT should be INVALID (not a station).
    card_json_manifest_with_pt = {
        "name": "Manifestation",
        "types": ["Artifact"],
        "text": "Manifestation.",
        "power": "1",
        "toughness": "1"
    }
    card_manifest = Card(card_json_manifest_with_pt)
    assert not card_manifest.valid, "Manifestation artifact with PT was incorrectly validated as a Station."
