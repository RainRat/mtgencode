import pytest
import json
import os
import shutil
import subprocess
from lib.cardlib import Card

SAMPLE_CARDS_DATA = [
  {
    "artist": "Jonas De Ro",
    "artistIds": [
      "561ebf9e-8d93-4b57-8156-8826d0c19601"
    ],
    "availability": [
      "arena",
      "mtgo",
      "paper"
    ],
    "boosterTypes": [
      "default"
    ],
    "borderColor": "black",
    "colorIdentity": [
      "W"
    ],
    "colors": [],
    "convertedManaCost": 0.0,
    "edhrecSaltiness": 0.31,
    "finishes": [
      "nonfoil",
      "foil"
    ],
    "frameVersion": "2015",
    "hasFoil": True,
    "hasNonFoil": True,
    "identifiers": {
      "scryfallId": "486fbcf9-3a04-47f6-8927-886c2a454499",
      "scryfallIllustrationId": "1646c495-9af8-4fd1-8d16-e11b2b93e1d8",
      "scryfallOracleId": "bc71ebf6-2056-41f7-be35-b2e5c34afa99",
      "tcgplayerProductId": "513368"
    },
    "isReprint": True,
    "language": "English",
    "layout": "normal",
    "legalities": {
      "alchemy": "Legal",
      "brawl": "Legal",
      "commander": "Legal",
      "duel": "Legal",
      "future": "Legal",
      "gladiator": "Legal",
      "historic": "Legal",
      "legacy": "Legal",
      "modern": "Legal",
      "oathbreaker": "Legal",
      "pauper": "Legal",
      "paupercommander": "Legal",
      "penny": "Legal",
      "pioneer": "Legal",
      "predh": "Legal",
      "premodern": "Legal",
      "standard": "Legal",
      "standardbrawl": "Legal",
      "timeless": "Legal",
      "vintage": "Legal"
    },
    "manaValue": 0.0,
    "name": "Plains",
    "number": "268",
    "printings": [
      "WOE"
    ],
    "purchaseUrls": {
      "cardKingdom": "https://mtgjson.com/links/dc16eb8216574a75",
      "cardKingdomFoil": "https://mtgjson.com/links/8f992a7811b7d1a6",
      "tcgplayer": "https://mtgjson.com/links/9ba3e27694f82a3c"
    },
    "rarity": "common",
    "setCode": "WOE",
    "subtypes": [
      "Plains"
    ],
    "supertypes": [
      "Basic"
    ],
    "text": "({T}: Add {W}.)",
    "type": "Basic Land — Plains",
    "types": [
      "Land"
    ],
    "uuid": "ce2a4840-e3d3-5372-8063-ba8a1e3e4e27",
    "variations": [
      "65ab0fa3-4cec-5857-93cf-8c7192a7e56c",
      "ff9bd747-5b27-57a5-9fd1-831349822771"
    ]
  },
  {
    "artist": "Scott Murphy",
    "artistIds": [
      "07c7ac65-dfa6-4273-9c66-ec9d8f3e2226"
    ],
    "availability": [
      "arena",
      "mtgo",
      "paper"
    ],
    "borderColor": "black",
    "colorIdentity": [
      "U"
    ],
    "colors": [
      "U"
    ],
    "convertedManaCost": 1.0,
    "edhrecRank": 3894,
    "edhrecSaltiness": 0.21,
    "finishes": [
      "nonfoil",
      "foil"
    ],
    "frameEffects": [
      "inverted"
    ],
    "frameVersion": "2015",
    "hasFoil": True,
    "hasNonFoil": True,
    "identifiers": {
      "scryfallId": "87c81647-6586-4c9c-93fc-9d5ee40b377b",
      "scryfallIllustrationId": "487f37ab-2a28-4c42-953d-42b7056193b0",
      "scryfallOracleId": "05a039ad-1689-4d13-b393-6c1219583b5d",
      "tcgplayerProductId": "514258"
    },
    "isPromo": True,
    "isReprint": True,
    "isStarter": True,
    "language": "English",
    "layout": "normal",
    "legalities": {
      "brawl": "Legal",
      "commander": "Legal",
      "duel": "Legal",
      "future": "Legal",
      "gladiator": "Legal",
      "historic": "Legal",
      "legacy": "Legal",
      "modern": "Legal",
      "oathbreaker": "Legal",
      "pauper": "Legal",
      "paupercommander": "Legal",
      "pioneer": "Legal",
      "predh": "Legal",
      "premodern": "Legal",
      "standard": "Legal",
      "standardbrawl": "Legal",
      "timeless": "Legal",
      "vintage": "Legal"
    },
    "manaCost": "{U}",
    "manaValue": 1.0,
    "name": "Sleight of Hand",
    "number": "376",
    "originalText": "Look at the top two cards of your library. Put one of them into your hand and the other on the bottom of your library.",
    "printings": [
      "WOE"
    ],
    "promoTypes": [
      "promopack"
    ],
    "purchaseUrls": {
      "cardKingdom": "https://mtgjson.com/links/a6a77b20480ba73c",
      "cardKingdomFoil": "https://mtgjson.com/links/39ba8362241876b6",
      "cardmarket": "https://mtgjson.com/links/f9ca175d16f3aaad",
      "tcgplayer": "https://mtgjson.com/links/a030ca97dd79ff09"
    },
    "rarity": "common",
    "rulings": [
      {
        "date": "2018-12-07",
        "text": "If there is only one card in your library, you put it into your hand."
      },
      {
        "date": "2023-09-01",
        "text": "If there is only one card in your library, you put it into your hand."
      }
    ],
    "setCode": "WOE",
    "subtypes": [],
    "supertypes": [],
    "text": "Look at the top two cards of your library. Put one of them into your hand and the other on the bottom of your library.",
    "type": "Sorcery",
    "types": [
      "Sorcery"
    ],
    "uuid": "0972ac2b-b2f9-5966-ac3b-1215246cb487",
    "variations": [
      "848a81e7-d20e-51e8-a6d9-c74227fa2acb"
    ]
  },
  {
    "artist": "Serena Malyon",
    "artistIds": [
      "d9fee7a6-7c5e-48a5-8639-bba25abc8a06"
    ],
    "availability": [
      "arena",
      "mtgo",
      "paper"
    ],
    "borderColor": "borderless",
    "colorIdentity": [
      "B"
    ],
    "colors": [
      "B"
    ],
    "convertedManaCost": 5.0,
    "edhrecRank": 12019,
    "edhrecSaltiness": 0.43,
    "finishes": [
      "nonfoil",
      "foil"
    ],
    "frameEffects": [
      "inverted"
    ],
    "frameVersion": "2015",
    "hasFoil": True,
    "hasNonFoil": True,
    "identifiers": {
      "scryfallId": "dd6f57de-21af-4c25-8a21-df3a75157939",
      "scryfallIllustrationId": "4abcdc90-4424-4ac1-b283-902274688a3c",
      "scryfallOracleId": "67d66678-a8e6-4f80-bade-1f1daf4b0610",
      "tcgplayerProductId": "509506"
    },
    "isFullArt": True,
    "isStarter": True,
    "language": "English",
    "layout": "normal",
    "leadershipSkills": {
      "brawl": True,
      "commander": False,
      "oathbreaker": True
    },
    "legalities": {
      "brawl": "Legal",
      "commander": "Legal",
      "duel": "Legal",
      "future": "Legal",
      "gladiator": "Legal",
      "historic": "Legal",
      "legacy": "Legal",
      "modern": "Legal",
      "oathbreaker": "Legal",
      "penny": "Legal",
      "pioneer": "Legal",
      "standard": "Legal",
      "standardbrawl": "Legal",
      "timeless": "Legal",
      "vintage": "Legal"
    },
    "loyalty": "5",
    "manaCost": "{3}{B}{B}",
    "manaValue": 5.0,
    "name": "Ashiok, Wicked Manipulator",
    "number": "297",
    "originalText": "If you would pay life while your library has at least that many cards in it, exile that many cards from the top of your library instead.\n+1: Look at the top two cards of your library. Exile one of them and put the other into your hand.\n−2: Create two 1/1 black Nightmare creature tokens with \"At the beginning of combat on your turn, if a card was put into exile this turn, put a +1/+1 counter on this creature.\"\n−7: Target player exiles the top X cards of their library, where X is the total mana value of cards you own in exile.",
    "printings": [
      "WOE"
    ],
    "promoTypes": [
      "boosterfun"
    ],
    "purchaseUrls": {
      "cardKingdom": "https://mtgjson.com/links/962235db7a2dc1bd",
      "cardKingdomFoil": "https://mtgjson.com/links/d392d04180a1f51f",
      "cardmarket": "https://mtgjson.com/links/89128904c809f1d7",
      "tcgplayer": "https://mtgjson.com/links/3b86c8fa58b16e33"
    },
    "rarity": "mythic",
    "rulings": [
      {
        "date": "2023-09-01",
        "text": "Ashiok's first ability doesn't allow you to attempt to pay an amount of life greater than your current life total."
      },
      {
        "date": "2023-09-01",
        "text": "Ashiok, Wicked Nightmare's first ability isn't optional. You can't choose to pay life instead of exiling cards from the top of your library while you control Ashiok, and you can't split the payment between life and cards."
      },
      {
        "date": "2023-09-01",
        "text": "If you would pay life while you control Ashiok and your library does not have at least that many cards in it, you'll just pay life as normal."
      }
    ],
    "securityStamp": "oval",
    "setCode": "WOE",
    "sourceProducts": {
      "foil": [
        "1ff62823-f41c-5334-af14-20c5cc28e84d",
        "3d11e864-79aa-54ed-aa85-81bacfccf3f4",
        "86ab9007-922a-5f13-8ffa-aaa8b775c06c",
        "cd6988ad-afc6-5926-b41e-88be446d9bb7"
      ],
      "nonfoil": [
        "1ff62823-f41c-5334-af14-20c5cc28e84d",
        "3d11e864-79aa-54ed-aa85-81bacfccf3f4",
        "86ab9007-922a-5f13-8ffa-aaa8b775c06c",
        "cd6988ad-afc6-5926-b41e-88be446d9bb7"
      ]
    },
    "subtypes": [
      "Ashiok"
    ],
    "supertypes": [
      "Legendary"
    ],
    "text": "If you would pay life while your library has at least that many cards in it, exile that many cards from the top of your library instead.\n[+1]: Look at the top two cards of your library. Exile one of them and put the other into your hand.\n[−2]: Create two 1/1 black Nightmare creature tokens with \"At the beginning of combat on your turn, if a card was put into exile this turn, put a +1/+1 counter on this token.\"\n[−7]: Target player exiles the top X cards of their library, where X is the total mana value of cards you own in exile.",
    "type": "Legendary Planeswalker — Ashiok",
    "types": [
      "Planeswalker"
    ],
    "uuid": "ea89690e-34ce-5610-9432-8dd06eb27795",
    "variations": [
      "dbdbc120-09cd-59ac-9d1d-1ad7d011ba25"
    ]
  },
  {
    "artist": "Carlos Palma Cruchaga",
    "artistIds": [
      "f0c43e1b-1853-4abc-8a1b-d7dda6c1d592"
    ],
    "availability": [
      "arena",
      "mtgo",
      "paper"
    ],
    "boosterTypes": [
      "default"
    ],
    "borderColor": "black",
    "colorIdentity": [],
    "colors": [],
    "convertedManaCost": 1.0,
    "edhrecRank": 1465,
    "edhrecSaltiness": 0.13,
    "finishes": [
      "nonfoil",
      "foil"
    ],
    "flavorText": "Sometimes, \"as fast as you can\" isn't quite fast enough.",
    "frameVersion": "2015",
    "hasFoil": True,
    "hasNonFoil": True,
    "identifiers": {
      "scryfallId": "09a4578a-7dc6-4da3-93ee-913b10be5740",
      "scryfallIllustrationId": "b55ba2a3-bdb1-4c69-9dc7-7a3b36b9f26c",
      "scryfallOracleId": "10b8d4c7-7553-4d76-b643-d98b80701e13",
      "tcgplayerProductId": "513348"
    },
    "isReprint": True,
    "keywords": [
      "Haste"
    ],
    "language": "English",
    "layout": "normal",
    "legalities": {
      "brawl": "Legal",
      "commander": "Legal",
      "duel": "Legal",
      "future": "Legal",
      "gladiator": "Legal",
      "historic": "Legal",
      "legacy": "Legal",
      "modern": "Legal",
      "oathbreaker": "Legal",
      "pauper": "Legal",
      "paupercommander": "Legal",
      "pioneer": "Legal",
      "standard": "Legal",
      "standardbrawl": "Legal",
      "timeless": "Legal",
      "vintage": "Legal"
    },
    "manaCost": "{1}",
    "manaValue": 1.0,
    "name": "Gingerbrute",
    "number": "246",
    "originalText": "Haste\n{1}: Gingerbrute can't be blocked this turn except by creatures with haste.\n{2}, {T}, Sacrifice Gingerbrute: You gain 3 life.",
    "power": "1",
    "printings": [
      "WOE"
    ],
    "purchaseUrls": {
      "cardKingdom": "https://mtgjson.com/links/b0a4e5c50c1c04ad",
      "cardKingdomFoil": "https://mtgjson.com/links/73b84ba18eaa562b",
      "cardmarket": "https://mtgjson.com/links/632f8da47ecd61ed",
      "tcgplayer": "https://mtgjson.com/links/fcd2c3e713aaa2c4"
    },
    "rarity": "common",
    "rulings": [
      {
        "date": "2019-10-04",
        "text": "Activating Gingerbrute's middle ability after it has become blocked by a creature without haste won't cause it to become unblocked."
      },
      {
        "date": "2024-11-08",
        "text": "Food is an artifact type. Even though it appears on some creatures, it's never a creature type."
      },
      {
        "date": "2024-11-08",
        "text": "If an effect refers to a Food, it means any Food artifact, not just a Food artifact token. For example, you can sacrifice Tough Cookie (an Artifact Creature — Food Golem) to activate Maraleaf Rider's ability (an ability with \"Sacrifice a Food\" in its cost)."
      },
      {
        "date": "2024-11-08",
        "text": "Whatever you do, don't eat the delicious cards."
      },
      {
        "date": "2024-11-08",
        "text": "You can't sacrifice a Food to pay multiple costs. For example, you can't sacrifice a Food token to activate its own ability and also to activate Maraleaf Rider's ability."
      }
    ],
    "setCode": "WOE",
    "sourceProducts": {
      "foil": [
        "1ff62823-f41c-5334-af14-20c5cc28e84d",
        "84528b0f-5ebd-5855-b32c-b718cc35f9e2",
        "86ab9007-922a-5f13-8ffa-aaa8b775c06c",
        "cd6988ad-afc6-5926-b41e-88be446d9bb7"
      ],
      "nonfoil": [
        "1ff62823-f41c-5334-af14-20c5cc28e84d",
        "57bf891f-b602-58c6-8e11-0b6006099568",
        "86ab9007-922a-5f13-8ffa-aaa8b775c06c"
      ]
    },
    "subtypes": [
      "Food",
      "Golem"
    ],
    "supertypes": [],
    "text": "Haste (This creature can attack and {T} as soon as it comes under your control.)\n{1}: This creature can't be blocked this turn except by creatures with haste.\n{2}, {T}, Sacrifice this creature: You gain 3 life.",
    "toughness": "1",
    "type": "Artifact Creature — Food Golem",
    "types": [
      "Artifact",
      "Creature"
    ],
    "uuid": "8532e156-9ec1-5319-ae8f-8fc896c60aaa"
  },
  {
    "artist": "Alayna Danner",
    "artistIds": [
      "bb677b1a-ce51-4888-83d6-5a94de461ff9"
    ],
    "availability": [
      "arena",
      "mtgo",
      "paper"
    ],
    "borderColor": "borderless",
    "colorIdentity": [
      "B",
      "W"
    ],
    "colors": [],
    "convertedManaCost": 0.0,
    "edhrecSaltiness": 0.08,
    "finishes": [
      "nonfoil",
      "foil"
    ],
    "frameEffects": [
      "inverted"
    ],
    "frameVersion": "2015",
    "hasFoil": True,
    "hasNonFoil": True,
    "identifiers": {
      "scryfallId": "8034589b-3b57-49be-b0fd-a306f915d864",
      "scryfallIllustrationId": "5617b553-dbd1-4802-9570-24121ab11aa5",
      "scryfallOracleId": "8b3726f1-20b8-42ec-8f9b-b361515c3f05",
      "tcgplayerProductId": "509500"
    },
    "isFullArt": True,
    "isStarter": True,
    "language": "English",
    "layout": "normal",
    "legalities": {
      "brawl": "Legal",
      "commander": "Legal",
      "duel": "Legal",
      "future": "Legal",
      "gladiator": "Legal",
      "historic": "Legal",
      "legacy": "Legal",
      "modern": "Legal",
      "oathbreaker": "Legal",
      "penny": "Legal",
      "pioneer": "Legal",
      "standard": "Legal",
      "standardbrawl": "Legal",
      "timeless": "Legal",
      "vintage": "Legal"
    },
    "manaValue": 0.0,
    "name": "Restless Fortress",
    "number": "305",
    "originalText": "Restless Fortress enters the battlefield tapped.\n{T}: Add {W} or {B}.\n{2}{W}{B}: Restless Fortress becomes a 1/4 white and black Nightmare creature until end of turn. It's still a land.\nWhenever Restless Fortress attacks, defending player loses 2 life and you gain 2 life.",
    "printings": [
      "WOE"
    ],
    "promoTypes": [
      "boosterfun"
    ],
    "purchaseUrls": {
      "cardKingdom": "https://mtgjson.com/links/504673f56883eb69",
      "cardKingdomFoil": "https://mtgjson.com/links/2fc151284e4dd0c9",
      "cardmarket": "https://mtgjson.com/links/29690d46e1b612b6",
      "tcgplayer": "https://mtgjson.com/links/f68fd08778d2c894"
    },
    "rarity": "rare",
    "rulings": [
      {
        "date": "2023-09-01",
        "text": "If this becomes a creature because of an effect other than its own ability, its last ability will still trigger whenever it attacks."
      },
      {
        "date": "2023-09-01",
        "text": "If this becomes a creature but you haven't controlled it continuously since your most recent turn began, you won't be able to activate its mana ability or attack with it that turn."
      }
    ],
    "securityStamp": "oval",
    "setCode": "WOE",
    "sourceProducts": {
      "foil": [
        "1ff62823-f41c-5334-af14-20c5cc28e84d",
        "3d11e864-79aa-54ed-aa85-81bacfccf3f4",
        "86ab9007-922a-5f13-8ffa-aaa8b775c06c",
        "cd6988ad-afc6-5926-b41e-88be446d9bb7"
      ],
      "nonfoil": [
        "1ff62823-f41c-5334-af14-20c5cc28e84d",
        "3d11e864-79aa-54ed-aa85-81bacfccf3f4",
        "86ab9007-922a-5f13-8ffa-aaa8b775c06c",
        "cd6988ad-afc6-5926-b41e-88be446d9bb7"
      ]
    },
    "subtypes": [],
    "supertypes": [],
    "text": "This land enters tapped.\n{T}: Add {W} or {B}.\n{2}{W}{B}: This land becomes a 1/4 white and black Nightmare creature until end of turn. It's still a land.\nWhenever this land attacks, defending player loses 2 life and you gain 2 life.",
    "type": "Land",
    "types": [
      "Land"
    ],
    "uuid": "1e724296-d370-5b52-8307-00c6acc5ab89",
    "variations": [
      "bac3e0a1-5d81-53cc-9814-2a8d704fd664"
    ]
  }
]

@pytest.fixture
def sample_cards():
    return SAMPLE_CARDS_DATA

def test_encode_decode_loop(sample_cards):
    for card_data in sample_cards:
        # 1. Instantiate Card from JSON
        original_card = Card(card_data)
        assert original_card.valid

        # 2. Encode the card
        encoded_string = original_card.encode()
        assert isinstance(encoded_string, str)

        # 3. Instantiate a new Card from the encoded string
        decoded_card = Card(encoded_string)
        assert decoded_card.valid

        # 4. Optional: Verify a basic attribute
        assert original_card.name == decoded_card.name
        assert original_card.cost.cmc == decoded_card.cost.cmc

def test_output_formats(sample_cards):
    for card_data in sample_cards:
        card = Card(card_data)
        assert isinstance(card.format(), str)
        assert isinstance(card.format(gatherer=True), str)
        assert isinstance(card.format(for_forum=True), str)
        assert isinstance(card.to_mse(), str)

def test_html_creativity_output():
    import struct
    outfile = "tests/test_output.html"
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    all_sets_file = os.path.join(data_dir, "AllSets.json")
    cbow_bin = os.path.join(data_dir, "cbow.bin")
    output_txt = os.path.join(data_dir, "output.txt")
    temp_infile = "tests/temp_sample_cards.json"

    # Write the sample data to a temporary file
    with open(temp_infile, "w") as f:
        json.dump(SAMPLE_CARDS_DATA, f)

    # The creativity feature requires several data files, so we'll create temporary ones
    shutil.copy(temp_infile, all_sets_file)

    # Create dummy cbow.bin and output.txt if they don't exist
    cbow_existed = os.path.exists(cbow_bin)
    output_existed = os.path.exists(output_txt)

    if not cbow_existed:
        header = f"{1:<4}{1:<4}".encode('ascii')
        word = b"test "
        vec = struct.pack('f'*1, 1.0)
        with open(cbow_bin, 'wb') as f:
            f.write(header + word + vec)

    if not output_existed:
        with open(output_txt, 'w') as f:
            f.write("|1test|9test")

    try:
        subprocess.run(["python", "decode.py", temp_infile, outfile, "--html", "--creativity"], check=True)
        assert os.path.exists(outfile)
        with open(outfile, "r") as f:
            content = f.read()
        assert "closest cards" in content
        assert "closest names" in content
    finally:
        if os.path.exists(outfile):
            os.remove(outfile)
        if os.path.exists(all_sets_file):
            os.remove(all_sets_file)
        if os.path.exists(temp_infile):
            os.remove(temp_infile)
        if not cbow_existed and os.path.exists(cbow_bin):
            os.remove(cbow_bin)
        if not output_existed and os.path.exists(output_txt):
            os.remove(output_txt)
