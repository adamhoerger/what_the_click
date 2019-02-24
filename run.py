from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import sys
import serial
import twitter
import random
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

tty = str(sys.argv[1])
app = Flask(__name__)
tweet = False
cipher = True
last_update = None
last_refresh_time = None
last_mention_id = None
last_tag_id = None
enmess = ""
demess = ""
needans = False
counter = 0

#with open('status_ids.txt') as f:
#    ids = f.read().split('\n')
#    if len(ids) == 2:
#        last_mention_id = ids[0]
#        if last_mention_id == "":
#            last_mention_id = None
#        last_tag_id = ids[1]
#        if last_tag_id == "":
#            last_tag_id = None

with open('keys.txt') as f:
    keys = f.read().split('\n')
    consumer_key = keys[0]
    consumer_secret = keys[1]
    access_key = keys[2]
    access_secret = keys[3]
    api = twitter.Api(consumer_key = consumer_key, consumer_secret = consumer_secret, access_token_key = access_key, access_token_secret = access_secret)

phrase = list()
with open('cipherBank.txt') as f:
    phrase = f.read().split('\n')
    
#print(str(phrase))
phrase = phrase[0:len(phrase)-1]
#print(str(phrase))

ser = serial.Serial('/dev/'+tty, 9600)

alphabet = "ABCDEFGHIJKLMNOPQRSRUVWXYZ1234567890"

def makeKey():
    temp = alphabet
    cipherKey = ""
    for i in range(0, len(temp)-1):
        randIndex = random.randint(0, len(temp)-2)
        cipherKey += temp[randIndex]
        temp = temp[:randIndex]+temp[randIndex+1:]
    return cipherKey.strip()

def encrypt(sent_to_encrypt):
    encrypt = ""
    cipherKey = makeKey()
    for i in range(0, len(sent_to_encrypt)):
        if sent_to_encrypt[i].upper() in alphabet:
            encrypt += cipherKey[alphabet.index(sent_to_encrypt[i].upper())]
        elif sent_to_encrypt[i] == " ":
            encrypt += " "
        else:
            continue
    return encrypt

def refresh():
    if not tweet:
        return
    now = datetime.now()
    print('Refreshing')
    if(last_refresh_time is None or (now - last_refresh_time > timedelta(minutes = 1))):
        global last_mention_id
        global last_tag_id
        global counter
        tags = api.GetSearch('#whattheclick', since_id = last_tag_id)
        print("tags:")
        for tg in tags:
            print(tg.text)
        #tags.sort(key = id, reverse = True)
        if (len(tags) > 0):
            #recent_tag = min(tags, key_func = lambda x: x.id)
            recent_tag = tags[0]
            last_tag_id = recent_tag.id
#            with open('status_ids.txt', 'w') as f:
#                f.write("{}\n{}".format(last_mention_id, last_tag_id))
            rt = api.PostRetweet(recent_tag.id)
            print(rt.text)
            ser.write('c')
            counter += 1
        mentions = api.GetMentions(since_id = last_mention_id)
        print("mentions:")
        for me in mentions:
            print(me.text)
        #mentions.sort(key = id, reverse = True)
        index = len(mentions) - 1
        while(index >= 0 and not ('click' in mentions[index].text.lower())):
            index -= 1
        if (index >= 0):
            #recent_mention = min(mentions, key_func = lambda x: x.id)
            recent_mention = mentions[index]
            last_mention_id = recent_mention.id
#            with open('status_ids.txt', 'w') as f:
#                f.write("{}\n{}".format(last_mention_id, last_tag_id))
            rt = api.PostRetweet(recent_mention.id)
            print(rt.text)
            ser.write('c')
            counter += 1
        


scheduler = BackgroundScheduler()
job = scheduler.add_job(refresh, 'interval', minutes = 1)
scheduler.start()

def click(resp, cipher_mess = None):
    global counter
    global last_update
    global cipher
    counter+=1
    ser.write('c')
    resp.message("Clicked Pen")

    if(tweet):
        recent = datetime.now()
        if(last_update is  None or (recent - last_update) > timedelta(0, 0, 0, 0, 1)):
            last_update = recent 
            message = 'Pen clicked on {0} at {1}.'.format(last_update.strftime('%B %d, %Y'), last_update.strftime('%I:%M %p'))
            if not cipher_mess is None:
                message = message + '\nCipher Solved: {}'.format(cipher_mess)
            status = api.PostUpdate(message)
            print(status.text)
            resp.message("Tweet sent")
        else:
            resp.message("Please wait to send another tweet")
    return True

@app.route("/sms", methods=['POST', 'GET'])
def parser():
    global tweet
    global last_update
    global last_refresh_time
    global api
    global cipher
    global needans
    global enmess
    global demess
    command = str(request.values.get('Body'))
    resp = MessagingResponse()
    
    if(needans):
        if command.lower() == demess.lower():
            resp.message("Congratulations you have decrypted the message")
            click(resp, "{0}->{1}".format(enmess, demess))
            needans = False
        else:
            resp.message("Sorry, try again\n"+enmess)
    elif command == "Port":
        resp.message(tty)
    elif command == "Tweet":
        tweet = not tweet
        resp.message("Tweeting set to "+str(tweet))
    elif command == "Cypher":
        cipher = not cipher;
        resp.message("Cypher set to "+str(cipher));
    elif command == "Click": 
        if(cipher):
            demess = phrase[random.randint(0, len(phrase)-1)]
            print("demess: "+demess)
            enmess = encrypt(demess)
            resp.message("You must decrypt the following message to click the pen:\n"+enmess)
            needans = True
        else:
            click(resp)
    elif command == "Total clicks":
        resp.message("The pen has been clicked "+str(counter)+" times.")
    else:
        resp.message("Invalid Command\nValid commands include:\nPort\nTweet\nCypher\nTotal clicks\nClick")
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
