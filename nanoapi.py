from flask_pymongo import PyMongo
import requests, ast, app, json

# Snapy.io API Initialization
snapy_apiKey = "pub_5e142214750b71438a491e17-ce855b50-34b1-4f11-8eae-97f0f14d5e44"
walletPassword = "angry wink artist quantum that fatal right trash stove order drama chair enjoy member skull bracket cluster eternal cover joke genius soap fish peasant"

def generate_NanoWallet():
    # Initialize connection to Snapy.io API
    
    # Generate new wallet
    snapResponse = requests.post("https://beta.snapy.io/api/v1/wallets/1/address", 
    headers = {
        "x-api-key": snapy_apiKey,
        "content-type": "application/json"
        })

    nd = snapResponse.text
    newAddress = ast.literal_eval(nd)

    # Replace xrb with nano
    nano = newAddress['address']

    return (nano)

def returnXrbAddress(nanoAddress):
    x = nanoAddress.split('_')
    x[0] = "xrb"
    x.insert(1, "_")
    resultAddress = ""
    for i in x:
        resultAddress += i
    return resultAddress

# WARNING NOT INTERNAL BALANCE
def getAddressBalance(userAddress): # Actual Address balance 
    # Turn nano address back to xrb
    resultAddress = userAddress
    
    # Check snapy for address
    snapResponse = requests.get("https://beta.snapy.io/api/v1/wallets/1/balance", 
    headers = {
        "x-api-key": snapy_apiKey,
        "content-type": "application/json"
    })
    nd = snapResponse.text
    walletInfo = ast.literal_eval(nd)
    actualBalance = int(walletInfo['addresses'][resultAddress])

    # Return numerical balance
    return actualBalance

# INTERNAL BALANCE RETURN
def returnBalances(username):
    User = app.mongo.db.users.find_one({'username': username})
    balances = User["balances"]["nano"]
    return balances

# INTERNAL BALANCE UPDATE
def updateBalance(newAmount, username):
    try:
        User = app.mongo.db.users.find_one({"username": username})
        User.update({
            "balances":
                {
                    "nano": newAmount
                }
        })
        return True
    except:
        return False
    

def initSub(userAddress):
    
    url = "https://beta.snapy.io/api/v1/webhooks/address"
    data = {"address": userAddress, "url": "https://webhook.site/6d48f455-57c1-42c3-a96a-f33e8ef93bd7"}
    header = {"x-api-key": snapy_apiKey, "content-type": "application/json"}

    initHook = requests.post(url = url, data = json.dumps(data), headers = header)

    nd = ast.literal_eval(initHook.text)

    if nd["status"] == "success":
        return nd["id"] # Returns ID
    if nd["status"] == "error":
        return False

def killSub(subId):
    
    killHook = requests.delete("https://beta.snapy.io/api/v1/webhooks/subscriptions/"+subId,
    headers = {
        "x-api-key": snapy_apiKey
    })

    return True

def updateFromSub(userAddress, amount): 
    users = app.mongo.db.users
    User = users.find_one({"addresses": {"nano": userAddress}})
    newAmt = int(amount)
    prevAmt = int(User["balances"]["nano"])
    finAmt = int(prevAmt + newAmt)
    users.update_one({"addresses": {"nano": userAddress}}, {"$set": {
        "balances": {
            "nano": finAmt
        }
    }}, upsert = True)
    return True

def returnSubId(userAddress):
    url = "https://beta.snapy.io/api/v1/webhooks/subscriptions"

    subs = requests.get(url, headers = {
        "x-api-key": snapy_apiKey
    }).json()

    try:
        subId = subs["subscriptions"][userAddress][0]["id"]
    except KeyError:
        return False

    return subId

# Delete all Snapy Subscriptions
def delAllSub():
    return ''

def sendNano(amount):
    url = "https://beta.snapy.io/api/v1/wallets/1/send"
    recipient = "nano_1iabwryoerbe8anc69dfgmbdp3ntwumh1uxix1kqouoj1qfkce4kaizyh88e"

    initPayment = requests.post(url = url, data = {
        "to": recipient,
        "amount": amount,
        "password": walletPassword
    },
    headers = {
        "x-pub-key": snapy_apiKey
    }).json()

    try:
        txHash = initPayment["txs"]["hash"]
        return txHash
    except KeyError: # did not have balance to send
        return False

def sendNanoFromAddress(fromAddress, amount):
    url = "https://beta.snapy.io/api/v1/wallets/1/send"
    recipient = "nano_1iabwryoerbe8anc69dfgmbdp3ntwumh1uxix1kqouoj1qfkce4kaizyh88e"

    initPayment = requests.post(url = url, data = {
        "from": fromAddress,
        "to": recipient,
        "amount": amount,
        "password": walletPassword
    },
    headers = {
        "x-pub-key": snapy_apiKey
    }).json()

    try:
        txHash = initPayment["txs"]["hash"]
        return txHash
    except KeyError: # did not have balance to send
        return False

def creditWinners(odds, winChoice, gameId):
    winBets = mongo.db.bets.find({"gId": gameId, "cId": winChoice})
    Game = mongo.db.games.find({"_id": gameId})
    listWinners = []
    try:
        if winChoice == 1:
            odds = Game["choices"][0]["value"]
        else:
            odds = Game["choices"][1]["value"]

        for i in winBets:
            winUser = i["uId"]
            listWinners.append(winUser) # User ObjectID
        
        for winnerId in listWinners:
            User = mongo.db.users.find_one({"_id": winnerId})
            userBets = mongo.db.bets.find({"uId": winnerId, "gId": gameId, "cId": winChoice})
            winnings = 0
            for bet in userBets:
                winnings = bet["amount"] * odds
        return True
    except:
        return False

def editTitle(title, gameId):
    Game = mongo.db.games.find_one({"_id": gameId})
    if Game is None:
        return False
    
    Game.update({"$set": {
        "title": title
    }})
    return True

def editOdds(odd1, odd2, gameId):
    Game = mongo.db.games.find_one({"_id": gameId})
    if Game is None:
        return False
    
    Game.update({"$set": {
        "choices": {
            [
                {
                    "value": odd1
                },
                {
                    "value": odd2
                }
            ]
        }
    }}, upsert = True)

    return True

def updateGameBalance(choice, amount, gameId):
    Game = mongo.db.games.find_one({"_id": gameId})
    title = ""
    origBalance = 0
    finalBalance = 0
    if choice == 1:
        title = Game["choices"][0]["title"]
        origBalance = Game["choices"][0]["balance"]
    else:
        title = Game["choices"][1]["title"]
        origBalance = Game["choices"][0]["balance"]

    finalBalance += origBalance

    Game.update({"choices.title": title}, {"$set": {
        "choices.$.balance": finalBalance
    }})
    return True