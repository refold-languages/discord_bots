## Allow program to delete files
import os

## Delete the files for program to re calibrate
if os.path.exists("C:\\Users\\Brett\\Desktop\\AI-ChatBot\\checkpoint"):
  os.remove("C:\\Users\\Brett\\Desktop\\AI-ChatBot\\checkpoint")

if os.path.exists("C:\\Users\\Brett\\Desktop\\AI-ChatBot\\data.pickle"):
  os.remove("C:\\Users\\Brett\\Desktop\\AI-ChatBot\\data.pickle")

if os.path.exists("C:\\Users\\Brett\\Desktop\\AI-ChatBot\\model.tflearn.data-00000-of-00001"):
  os.remove("C:\\Users\\Brett\\Desktop\\AI-ChatBot\\model.tflearn.data-00000-of-00001")

if os.path.exists("C:\\Users\\Brett\\Desktop\\AI-ChatBot\\model.tflearn.index"):
  os.remove("C:\\Users\\Brett\\Desktop\\AI-ChatBot\\model.tflearn.index")

if os.path.exists("C:\\Users\\Brett\\Desktop\\AI-ChatBot\\model.tflearn.meta"):
  os.remove("C:\\Users\\Brett\\Desktop\\AI-ChatBot\\model.tflearn.meta")

if os.path.exists("C:\\Users\\Brett\\Desktop\\AI-ChatBot\\intents.json"):
  os.remove("C:\\Users\\Brett\\Desktop\\AI-ChatBot\\intents.json")

## Combine the JSON files here

f1data = f2data = f3data = f4data = f5data = f6data = f7data = f8data = f9data = f10data = f11data = f12data = f13data = f14data = f15data = f99data = "" 
 
#########################################################################
####### Add First JSON - AAATop_howToUseBot.json is the first JSON and must ALWAYS be the first JSON to have formatting fit.
######################################################################### 
with open('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\jsonGroups\\AAATop_howToUseBot.json', encoding='utf-8') as f1: 
  f1data = f1.read() 

with open('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\jsonGroups\\anki.json', encoding='utf-8') as f2: 
  f2data = f2.read() 
f1data += "\n"
f1data += f2data

## Add Another JSON
with open('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\jsonGroups\\beginner.json', encoding='utf-8') as f3: 
  f3data = f3.read()  
f1data += "\n"
f1data += f3data
## Add Another JSON
with open('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\jsonGroups\\content.json', encoding='utf-8') as f4: 
  f4data = f4.read()  
f1data += "\n"
f1data += f4data
## Add Another JSON
with open('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\jsonGroups\\discord.json', encoding='utf-8') as f5: 
  f5data = f5.read()  
f1data += "\n"
f1data += f5data
## Add Another JSON
with open('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\jsonGroups\\grammar.json', encoding='utf-8') as f6: 
  f6data = f6.read()  
f1data += "\n"
f1data += f6data
## Add Another JSON
with open('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\jsonGroups\\immersion.json', encoding='utf-8') as f7: 
  f7data = f7.read()  
f1data += "\n"
f1data += f7data
## Add Another JSON
with open('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\jsonGroups\\misc.json', encoding='utf-8') as f8: 
  f8data = f8.read()  
f1data += "\n"
f1data += f8data
## Add Another JSON
with open('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\jsonGroups\\motivation.json', encoding='utf-8') as f9: 
  f9data = f9.read()  
f1data += "\n"
f1data += f9data
## Add Another JSON
with open('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\jsonGroups\\refold.json', encoding='utf-8') as f10: 
  f10data = f10.read()  
f1data += "\n"
f1data += f10data
## Add Another JSON
with open('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\jsonGroups\\sentenceMining.json', encoding='utf-8') as f11: 
  f11data = f11.read()  
f1data += "\n"
f1data += f11data
## Add Another JSON
with open('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\jsonGroups\\vocabulary.json', encoding='utf-8') as f12: 
  f12data = f12.read()  
f1data += "\n"
f1data += f12data
## Add Another JSON
with open('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\jsonGroups\\output.json', encoding='utf-8') as f13: 
  f13data = f13.read()  
f1data += "\n"
f1data += f13data
## Add Another JSON
with open('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\jsonGroups\\random.json', encoding='utf-8') as f14: 
  f14data = f14.read()  
f1data += "\n"
f1data += f14data
## Add Another JSON
with open('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\jsonGroups\\resourceShare.json', encoding='utf-8') as f15: 
  f15data = f15.read()  
f1data += "\n"
f1data += f15data

#########################################################################
####### Add Another JSON - ZZZBot_kanjiAndKana.json is the last JSON and must ALWAYS be the last JSON to have formatting fit.
######################################################################### 
with open('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\jsonGroups\\ZZZBot_kanjiAndKana.json', encoding='utf-8') as f99: 
  f99data = f99.read()  
f1data += "\n"
f1data += f99data

with open ('C:\\Users\\Brett\\Desktop\\AI-ChatBot\\intents.json', 'a', encoding='utf-8') as f100: 
  f100.write(f1data)

