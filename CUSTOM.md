The purpose of this document, along with csv2json.py and combinejson.py, is to feed your favorite neural-net generated cards back into the next generation of the network, to create a better and better draft environment. Keep in mind that the neural net won’t spit the cards back exactly, but will help it learn what power level is appropriate, what ability is in each color, what mechanics are popular, etc.

- Power level and rarity must be reasonable for draft.
- The cards will be separated from any rulings or reminder text you provide, so they can’t rely on a hypothetical new addition to the comprehensive rules to function. (ie. you can’t define a new keyword)
- You may, however, make a new creature type, counter type, or planeswalker type, as long as the type doesn’t need to have any inherent rules meaning.
- Silver-bordered cards skipped for now.
- Use the latest templating. (ie. “create an x token” rather than “put an x token onto the battlefield”) It will help the network see relations between cards.
- The last field is rarity. Common/Uncommon/Rare/Mythic. I quickly tweaked some of them based on what I think would be good for draft.
- Not every card has to be super clever. Some simple cards that demonstrate the color pie, or make a draft fun, are appreciated.
- You can absolutely tweak any card for flavour, power level, or rarity. Go right ahead.
- If it’s a radical divergence from the existing card, maybe include both (i.e. a common with the simple version of an idea; then a mythic with the idea pushed to the limit.)

Obviously, these are just suggestions of what I think will work best with the neural network. You can fork it if you desire. csv2json.py and combinejson.py are MIT License, just like mtgencode. 

To start the list, I took the top cards from reddit.com/r/custommagic
You may add cards from any source:
- Reddit
- Unused cards from Wizards (ie. great designer search)
- Your original ideas
- Cards from a neural network (possibly with tweaks)

Here is the list. https://docs.google.com/spreadsheets/d/1bYqDoRc6tD6uEchANzDUFZp0xaL4GTgFa4iadXcXRRQ/edit#gid=0 Use the File->Download option to save it as a .csv file.