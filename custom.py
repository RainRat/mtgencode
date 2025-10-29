import csv

csvfile =open('customcards.csv')
jsonfile=open('customcards.json', 'w') 
spamreader = csv.reader(csvfile)
jsonfile.write("{\"CUS\":{\"cards\": [")
#jsonfile.write("{\"data\":{\"CUS\":{\"cards\": [")
for row in spamreader:
    if row[0]=="name":
        continue
    jsonfile.write("{\"layout\": \"normal\", \"manaCost\": \"" +row[1]+ "\",")
    jsonfile.write("\"name\": \"" +row[0].replace("\"", "")+ "\",")
    temprarity=row[6]
    if temprarity=="R":
     temprarity="rare"
    if temprarity=="U":
     temprarity="uncommon"
    if temprarity=="C":
     temprarity="common"
    if temprarity=="M":
     temprarity="mythic"
    jsonfile.write("\"rarity\": \"" +temprarity+ "\",")
    jsonfile.write("\"text\": \"" +row[4].replace("\\", "\\n").replace ("\"", "\\\"")+ "\",")
    if row[5]!="":
        pt=row[5].split("/")
        jsonfile.write("\"power\": \"" +pt[0]+ "\",")
        jsonfile.write("\"toughness\": \"" +pt[1]+ "\",")

#type is a blob
#supertypes, types, subtypes are lists

#types and maybe supertypes
    typelist=row[2].split(" ")
    if typelist[0]=="Legendary":
        jsonfile.write("\"supertypes\": [\"" +typelist[0]+ "\"],")
        typelist.remove("Legendary")
    jsonfile.write("\"types\": [")
    tempstring=""
    for x in typelist:
        tempstring=tempstring+("\""+x+ "\",")
    jsonfile.write(tempstring[:-1]+"],")

#subtypes
    if row[3]!="":
        jsonfile.write("\"subtypes\": [")
        subtypelist=row[3].split(" ")
        tempstring=""
        for x in subtypelist:
            tempstring=tempstring+("\""+x+ "\",")
        jsonfile.write(tempstring[:-1]+"],")        


#***** create "type"
    fulltypes=row[2]
    if row[3]!="":
        fulltypes=fulltypes+ " — " +row[3]
    jsonfile.write("\"type\": \"" +fulltypes+ "\"},")
    
#jsonfile.write ("], \"name\": \"custom\",\"code\": \"CUS\"}}}")
jsonfile.write ("], \"name\": \"custom\",\"code\": \"CUS\"}}")

        
        
        
        
        
