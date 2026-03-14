import pytest
import os
import subprocess
import tempfile
import json

def run_decode(args):
    cmd = ["python3", "decode.py"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def test_html_output_dynamic_nav():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tf:
        cards = [
            {"name": "Blue Card", "manaCost": "{U}", "types": ["Enchantment"], "rarity": "Rare"},
            {"name": "Red Card", "manaCost": "{R}", "types": ["Enchantment"], "rarity": "Common"}
        ]
        json.dump(cards, tf)
        tf_path = tf.name

    try:
        out_path = "test_dynamic.html"
        res = run_decode([tf_path, out_path, "--html"])
        if res.returncode != 0:
            print(res.stderr)

        assert os.path.exists(out_path)
        with open(out_path, 'r') as f:
            html = f.read()

        assert '<ul id="nav-bar">' in html
        assert 'href="#blue"' in html
        assert 'href="#red"' in html
        assert 'href="#white"' not in html

        assert 'id="blue"' in html
        assert 'id="red"' in html

    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)
        if os.path.exists("test_dynamic.html"):
            os.remove("test_dynamic.html")

def test_html_output_booster_nav():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tf:
        cards = []
        # Need enough cards for boosters
        for i in range(20):
            cards.append({"name": f"common_{i}", "manaCost": "{W}", "types": ["Enchantment"], "rarity": "Common"})
        for i in range(10):
            cards.append({"name": f"uncommon_{i}", "manaCost": "{U}", "types": ["Enchantment"], "rarity": "Uncommon"})
        for i in range(5):
            cards.append({"name": f"rare_{i}", "manaCost": "{B}", "types": ["Enchantment"], "rarity": "Rare"})
        for i in range(5):
            cards.append({"name": f"land_{i}", "types": ["Land"], "rarity": "Basic Land"})
        json.dump(cards, tf)
        tf_path = tf.name

    try:
        out_path = "test_booster.html"
        run_decode([tf_path, out_path, "--html", "--booster", "2"])

        assert os.path.exists(out_path)
        with open(out_path, 'r') as f:
            html = f.read()

        assert '<ul id="nav-bar">' in html
        assert 'href="#pack_1"' in html
        assert 'href="#pack_2"' in html
        assert 'id="pack_1"' in html

    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)
        if os.path.exists("test_booster.html"):
            os.remove("test_booster.html")

def test_html_output_single_group_no_nav():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tf:
        cards = [
            {"name": "Blue 1", "manaCost": "{U}", "types": ["Enchantment"], "rarity": "Common"},
            {"name": "Blue 2", "manaCost": "{U}", "types": ["Enchantment"], "rarity": "Common"}
        ]
        json.dump(cards, tf)
        tf_path = tf.name

    try:
        out_path = "test_single.html"
        run_decode([tf_path, out_path, "--html"])

        assert os.path.exists(out_path)
        with open(out_path, 'r') as f:
            html = f.read()

        assert '<ul id="nav-bar">' not in html
        assert 'id="blue"' in html

    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)
        if os.path.exists("test_single.html"):
            os.remove("test_single.html")
