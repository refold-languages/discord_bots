import nltk 
import logging
import argparse

###logging.critical('Field one has this value:' + fieldOne[0])

nltk.download('punkt')

from nltk import word_tokenize,sent_tokenize

from nltk.stem.lancaster import LancasterStemmer
stemmer = LancasterStemmer()

import numpy as np 
import tflearn
import tensorflow as tf
import random
import json
import pickle
from discord.ext import commands

with open("intents.json", encoding="utf-8") as file:
    data = json.load(file)

try:
    with open("data.pickle","rb") as f:
        words, labels, training, output = pickle.load(f)

except:
    words = []
    labels = []
    docs_x = []
    docs_y = []
    for intent in data["intents"]:
        for pattern in intent["patterns"]:
            wrds = nltk.word_tokenize(pattern)
            words.extend(wrds)
            docs_x.append(wrds)
            docs_y.append(intent["tag"])
            
        if intent["tag"] not in labels:
            labels.append(intent["tag"])


    words = [stemmer.stem(w.lower()) for w in words if w != "?"]
    words = sorted(list(set(words)))
    labels = sorted(labels)

    training = []
    output = []
    out_empty = [0 for _ in range(len(labels))]

    for x, doc in enumerate(docs_x):
        bag = []

        wrds = [stemmer.stem(w.lower()) for w in doc]

        for w in words:
            if w in wrds:
               bag.append(1)
            else:
              bag.append(0)
    
        output_row = out_empty[:]
        output_row[labels.index(docs_y[x])] = 1
        
        training.append(bag)
        output.append(output_row)

    training = np.array(training)
    output = np.array(output)
    
    with open("data.pickle","wb") as f:
        pickle.dump((words, labels, training, output), f)



net = tflearn.input_data(shape=[None, len(training[0])])
net = tflearn.fully_connected(net, 8)
net = tflearn.fully_connected(net, 8)
net = tflearn.fully_connected(net, len(output[0]), activation="softmax")
net = tflearn.regression(net)

model = tflearn.DNN(net)
model.fit(training, output, n_epoch=1000, batch_size=8, show_metric=True)
model.save("model.tflearn")

try:
    model.load("model.tflearn")
except:
    model.fit(training, output, n_epoch=1000, batch_size=8, show_metric=True)
    model.save("model.tflearn")


def bag_of_words(s, words):
    bag = [0 for _ in range(len(words))]

    s_words = nltk.word_tokenize(s)
    s_words = [stemmer.stem(word.lower()) for word in s_words]

    for se in s_words:
        for i, w in enumerate(words):
            if w == se:
                bag[i] = 1
    
    return np.array(bag)


import discord

class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    async def on_message(self, message):

################################################################################################################
############################################ Public Sections ###################################################
################################################################################################################

        # Check and Make ssure it's' in Basic QA Bot Channel
        if message.channel.name == 'beginner-questions' or message.channel.name == 'methodology-qa' or message.channel.name == 'language-general' or message.channel.name == 'off-topic':
            ## make sure not respondding to it's own message
            if message.author.id == self.user.id:
                return
            ## set user to be used in role selection    
            user = message.author
            if discord.utils.get(user.roles, name="Admin") is not None or discord.utils.get(user.roles, name="Mod") is not None or discord.utils.get(user.roles, name="Helper") is not None:
                if message.content.startswith('!bot'):
                    ###########################################################################
                    ####### This get's the correct answer before eventually sending it to chat
                    ###########################################################################
                    ##make message but without the ! bot call marker
                    inp = message.content
                    inp = inp[5:]
                    ##this is where copy paste from below starts and starts finding answers
                    result = model.predict([bag_of_words(inp, words)])[0]
                    result_index = np.argmax(result)
                    tag = labels[result_index]
                    
                    if result[result_index] > 0.7:
                        for tg in data["intents"]:
                            if tg['tag'] == tag:
                                responses = tg['responses']
                                fieldOne = tg['Field-1']
                                fieldTwo = tg['Field-2']
                                fieldThree = tg['Field-3']
                                fieldFour = tg['Field-4']
                                fieldFive = tg['Field-5']
                                fieldSix = tg['Field-6']
                                RelatedQ = tg['Related-Q']
                                theTag = tg['tag']
                                embed = 0

                                    #### Make the embed if there is no resource field 1 ####
                                if fieldOne[0] == "" and RelatedQ != "":
                                        embed=discord.Embed(title="Related Questions:", description=RelatedQ, color=0x6544e9)
                                        embed.set_footer(text="I am only useable by Admins, mods, and helpers in this channel. If you want to ask me a question, please visit #🤖basic-qa-bot. You do not need to type !bot in that channel.".format(RelatedQ))
                                        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/856984019337609236/862729433265864784/Refold-Japanese.png")
                                    #### Make embed if there is a field 1 resource ####
                                if fieldOne[0] != "":
                                    embed=discord.Embed(title="Additional Resources:", description="", color=0x6544e9)
                                    embed.set_footer(text="I am only useable by Admins, mods, and helpers in this channel. If you want to ask me a question, please visit #🤖basic-qa-bot. You do not need to type !bot in that channel.".format(RelatedQ))
                                    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/856984019337609236/862729433265864784/Refold-Japanese.png")
                                    embed.add_field(name=fieldOne[0], value="[{}]({})".format(fieldOne[1], fieldOne[2]), inline=True)
                                    if fieldTwo[0] != "":
                                        embed.add_field(name=fieldTwo[0], value="[{}]({})".format(fieldTwo[1], fieldTwo[2]), inline=True)
                                        if fieldThree[0] != "":
                                            embed.add_field(name=fieldThree[0], value="[{}]({})".format(fieldThree[1], fieldThree[2]), inline=True)
                                            if fieldFour[0] != "":
                                                embed.add_field(name=fieldFour[0], value="[{}]({})".format(fieldFour[1], fieldFour[2]), inline=True)
                                                if fieldFive[0] != "":
                                                    embed.add_field(name=fieldFive[0], value="[{}]({})".format(fieldFive[1], fieldFive[2]), inline=True)
                                                    if fieldSix[0] != "":
                                                        embed.add_field(name=fieldSix[0], value="[{}]({})".format(fieldSix[1], fieldSix[2]), inline=True)
                                    if RelatedQ != "": 
                                        embed.add_field(name="Related Questions", value=RelatedQ, inline=False)

                    ###########################################################################
                    ####### This sends the answer collected above as a reply or as a message
                    ###########################################################################
                    ## check if message is replying to another user or not
                    reference = message.reference
                    if reference is None:
                        bot_response=random.choice(responses)
                        await message.reply(bot_response.format(message))
                        if fieldOne[0] != "" or RelatedQ != "":
                            await message.channel.send(embed=embed)
                        return
                    else:
                        bot_response=random.choice(responses)
                        await reference.resolved.reply(bot_response.format(message))
                        if fieldOne[0] != "" or RelatedQ != "":
                            await message.channel.send(embed=embed)
                        return

################################################################################################################
############################################ Q&A Bot Section ###################################################
################################################################################################################

        # Check and Make ssure it's' in Basic QA Bot Channel
        if message.channel.name != '🤖basic-qa-bot':
            return
        # we do not want the bot to reply to itself
        elif message.author.id == self.user.id:
            return

        else:
           inp = message.content
           result = model.predict([bag_of_words(inp, words)])[0]
           result_index = np.argmax(result)
           tag = labels[result_index]
           
           if result[result_index] > 0.7:
               for tg in data["intents"]:
                   if tg['tag'] == tag:
                       responses = tg['responses']
                       fieldOne = tg['Field-1']
                       fieldTwo = tg['Field-2']
                       fieldThree = tg['Field-3']
                       fieldFour = tg['Field-4']
                       fieldFive = tg['Field-5']
                       fieldSix = tg['Field-6']
                       RelatedQ = tg['Related-Q']
                       theTag = tg['tag']
                       embed = 0

                        #### Make the embed if there is no resource field 1 ####
                       if fieldOne[0] == "" and RelatedQ != "":
                            embed=discord.Embed(title="Related Questions:", description=RelatedQ, color=0x6544e9)
                            embed.set_footer(text="If this did not answer your question, please ask again a different way or come back later. My answers should improve over time.".format(RelatedQ))
                            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/856984019337609236/862729433265864784/Refold-Japanese.png")
                        #### Make embed if there is a field 1 resource ####
                       if fieldOne[0] != "":
                           embed=discord.Embed(title="Additional Resources:", description="", color=0x6544e9)
                           embed.set_footer(text="If this did not answer your question, please ask again a different way or come back later. My answers should improve over time.".format(RelatedQ))
                           embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/856984019337609236/862729433265864784/Refold-Japanese.png")
                           embed.add_field(name=fieldOne[0], value="[{}]({})".format(fieldOne[1], fieldOne[2]), inline=True)
                           if fieldTwo[0] != "":
                               embed.add_field(name=fieldTwo[0], value="[{}]({})".format(fieldTwo[1], fieldTwo[2]), inline=True)
                               if fieldThree[0] != "":
                                   embed.add_field(name=fieldThree[0], value="[{}]({})".format(fieldThree[1], fieldThree[2]), inline=True)
                                   if fieldFour[0] != "":
                                       embed.add_field(name=fieldFour[0], value="[{}]({})".format(fieldFour[1], fieldFour[2]), inline=True)
                                       if fieldFive[0] != "":
                                           embed.add_field(name=fieldFive[0], value="[{}]({})".format(fieldFive[1], fieldFive[2]), inline=True)
                                           if fieldSix[0] != "":
                                               embed.add_field(name=fieldSix[0], value="[{}]({})".format(fieldSix[1], fieldSix[2]), inline=True)
                           if RelatedQ != "": 
                            embed.add_field(name="Related Questions", value=RelatedQ, inline=False)
                   

                       
               bot_response=random.choice(responses)
               await message.reply(bot_response.format(message))
               if fieldOne[0] != "" or RelatedQ != "":
                await message.channel.send(embed=embed)
    
           else:
               await message.channel.send("I'm sorry. I have not been taught an answer to this question yet. Please ask a different way or try again later. I will hopefully be taught this soon.\n Until then try <#778822272081330177>, <#778820943459778570>, <#778821128436318218> or the most appropriate channel. Don't forget to tag your questions with !q to make them easy for mods and helpers to find.   ".format(message))

client = MyClient()
parser = argparse.ArgumentParser(description='Japanese Chat Bot')
parser.add_argument('auth_key', type=str, help='the key to authenticate this discord bot with discord')
args = parser.parse_args()
client.run(args.auth_key)