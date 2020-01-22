from flask import Flask, request, session, jsonify, redirect, url_for, make_response
from flask_pymongo import PyMongo
from bson import BSON, json_util
from decimal import Decimal
import nanoapi, ast, sys, bcrypt, json

### NOTES #########################################
# Need to use better thing than vanilla session 
# to secure withdrawal
# and other functions
#
# To be tested through test_app.py as of 8/01/2020
###################################################

# MONGO DB COLLECTIONS ############################
# users, games, bets
###################################################

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb+srv://wenzani:testPassword@wenzani-rwc9d.mongodb.net/test?retryWrites=true&w=majority"
# For debug purposes only, protect after
app.config['SECRET_KEY'] = 'the random string'  

# db connection
mongo = PyMongo(app)

@app.route('/api/v1')
def index(): # Return Games Separated Through Categories
    if "username" in session:
        return make_response(jsonify(response = 'user logged in', status = 200), 200)
    return make_response(jsonify(response = 'sportsbook api v1', status = 200), 200)

# BOOKIE routes - last priority

@app.route('/api/v1/bookie/login', methods=['POST'])
def bookie_login(): # Bookie Login Endpoint
    if request.headers['bookie'] == "True":
        session['bookie'] = 'iamabookie'
    return makeresponse(jsonify(response = "success", status = 200), 200)

# USER routes

# Finished and Debugged
@app.route('/api/v1/user/profile')
def display_profile(): # Bet history, total winnings
    if "username" in session:
        
        # Initialize MongoDB
        User = mongo.db.users.find_one({"username": session["username"]})
        
        # For refactoring, check GET BET route
        try:
            amt = int(request.headers["amount"])
            userBets = mongo.db.bets.find({"uId": User["_id"]})[0:amt]
        except KeyError:
            # 10 records returned by default
            userBets = mongo.db.bets.find({"uId": User["_id"]})[0:10]
        
        listBets = []

        for bet in userBets:
            listBets.append(bet)
        
        return make_response(json.dumps(listBets, default=json_util.default), 200)

    return make_response(jsonify(response = "user must be logged in to view", status = 400), 400)

# Not yet tested
@app.route('/api/v1/webhooks/subscription', methods=["POST"])
def receive_notif():
    snapyData = request.json
    userAddress = snapyData["address"]
    userAmount = snapyData["amount"]
    if nanoapi.updateFromSub(userAddress, userAmount):
        
        User = mongo.db.users.find_one({"addresses": {"nano": userAddress}})

        subId = nanoapi.returnSubId(userAddress)
        if subId == False:
            return make_response(jsonify(response = "error", status = 400), 400)
        nanoapi.killSub(subId)

        # Move NANO to Owner Wallet
        nanoapi.sendNano(userAmount)

        newBalance = nanoapi.returnBalances(User["username"])

        return make_response(jsonify(response = "success", address = userAddress, balance = newBalance , status = 200), 200)

    return make_response(jsonify(response = "error", status = 400), 400)

# Finished and Debugged
@app.route('/api/v1/user/wallet', methods=['GET', 'POST'])
def display_balance(): # Update user balance, available, locked and promo
    
    # Only display balance if user is logged in
    if "username" in session:
        # Search MongoDB for user balances
        # For depositing
        if request.method == "GET":
            users = mongo.db.users
            User = users.find_one({'username': session['username']})
            
            # Return balances as 
            if request.headers['curr'] == 'nano':
                initSnapy = nanoapi.initSub(User["addresses"]["nano"])
                balance = nanoapi.returnBalances(session["username"])
                if initSnapy == False:
                    return make_response(jsonify(response = "connection active", currency = "nano", address = User["addresses"]["nano"], balance = User["balances"]["nano"], status = 200), 200) 
                
                return make_response(jsonify(response = "connection initiated", currency = "nano", address = User["addresses"]["nano"], balance = balance, status = 200), 200)
        
        if request.method == "POST":
            if request.headers["appOp"] == "withdraw":
                raw = request.json 
                User = mongo.db.users.find_one({"username": session["username"]})

                amount = raw["amount"]
                recipient = raw["recipient"]

                return make_response(jsonify(response = "withdrawal successful", status = 200), 200)
            else:
                return make_response(jsonify(response = "invalid operation", status = 400), 400)

    # Forbidden if not logged in
    return jsonify(response = "Not logged in", status = 403)

# Finished and Debugged
@app.route('/api/v1/user/wallet/new', methods=['POST'])
def create_userAddress():
    # Check if session is active    
    if "username" in session:
        # Select user collection in MongoDB
        users = mongo.db.users
        User = users.find_one({'username': session['username']})
        
        # Determine currency for address recreation
        try:
            # Can only make 1 address, can be changed; but, to be safe.
            if request.headers['curr'] == 'nano': # NANO
                try:
                    checker = User["addresses"]["nano"]
                    return make_response(jsonify(response = "address already exists", address = checker, status = 400), 400)
                except KeyError:
                    newAddy = nanoapi.generate_NanoWallet()
                    # print(newAddy, file=sys.stderr)

                    # Update the user's data
                    users.update_one({'username': session['username']}, {'$set': 
                    {
                        'addresses': 
                            {
                                'nano': newAddy
                            }
                    }})
                    return make_response(jsonify(response = newAddy, status = 201), 201)

        # Client did not specify currency
        except KeyError:
            return make_response(jsonify(response = "specify currency to create address, if doesn't exist", status = 400), 400)

    # Unexpected 
    return make_response(jsonify(response = 'Forbidden', status = 403), 403)

# Finished and Debugged
@app.route('/api/v1/user/register', methods=['POST', 'GET'])
def create_user(): # Create user through header, input into MongoDB
    
    if request.method == 'GET':
        return jsonify(response='User register endpoint working.', status=200)
    
    # Request Method POST

    users = mongo.db.users
    existing_user = users.find_one({'username' : request.json['username']})

    if existing_user is None:
        # Hash password using bcrypt
        hashpass = bcrypt.hashpw(request.json['password'].encode('utf-8'), bcrypt.gensalt())
        username = request.json['username']

        # Store inside database
        # We probably need a schema for this, might be hard to add new features after
        # See Mongodb $update docs for any modifications or additions after launch
        nanoAddress = nanoapi.generate_NanoWallet()
        users.insert({
            'username': username, 
            'password': hashpass,
            'addresses': {
                "nano": nanoAddress
            },
            'balances': {
                "nano": 0
            } 
            })
        
        # Add username into session
        session['username'] = request.json['username']

        return make_response(jsonify(response = "user created and logged in", status = 201), 201)

    return make_response(jsonify(response = 'User already exists', status = 400), 400)

# Finished and Debugged
@app.route('/api/v1/user/login', methods=['POST'])
def user_login():

    # Check if user is already logged in
    if "username" in session:
        return make_response(jsonify(response = "user already logged in", status = 200), 200)
    # Access Database
    users = mongo.db.users
    # Confirm if user exists within database
    loginUser = users.find_one({'username': request.json['username']})
    
    if loginUser:
        # Username exists
        if bcrypt.hashpw(request.json['password'].encode('utf-8'), loginUser['password']) == loginUser['password']:
            # Password confirmation successful
            session['username'] = request.json['username']

            return jsonify(response = "login successful", status = 200)
        
        # Password is incorrect
        return (jsonify(response = "wrong username/password", status = 403), 403)

    # Username did not exist    
    return (jsonify(response = "wrong username/password", status = 403), 403)

# Finished and Debugged
@app.route('/api/v1/user/logout')
def user_logout():
    # Remove user from current session
    if "username" in session:
        for key in list(session.keys()):
            if key != '_flashes':
                session.pop(key)
        return make_response(jsonify(response = "user logged out", status = 200), 200)
    # User is currently not logged in
    return make_response(jsonify(response = "user not logged in", status = 400), 400)

# GAMES route

@app.route('/api/v1/games/manage', methods=['POST'])
def manage_games():
    if "bookie" in session:

        data = request.json
        gameId = data["_id"]

        if request.headers["appOp"] == "editOdds": # Pass odds and _id ObjectID of game
            # Insert function for editing odds values
            # Decimal Odds 
            odd1 = data["odd1"]
            odd2 = data["odd2"]
            if nanoapi.editOdds(odd1, odd2, gameId):
                return make_response(jsonify(response = "success", status = 200), 200)
            return make_response(jsonify(response = "error", status = 400), 400)

        if request.headers["appOp"] == "editTitle":
            # Insert function for editing title 
            title = data["title"]
            if nanoapi.editGameTitle(title, gameId):
                return make_response(jsonify(response = "success", status = 200), 200)
            return make_response(jsonify(response = "error", status = 400), 400)

        if request.headers["appOp"] == "endGame":
            winner = data["winner"]
            # Insert function for making game inactive
            if nanoapi.endGame(winChoice, gameId):
                # Insert function for crediting winners
                if nanoapi.creditWinners(winner, gameId):
                    return make_response(jsonify(response = "success", status = 200), 200)
            return make_response(jsonify(response = "error", status = 400), 400)

    return make_response(jsonify(response = "error", status = 400), 400)

# Finished and Debugged
@app.route('/api/v1/games', methods=['GET', 'POST'])
def games_route():
    
    # Games
    # Title, Game Date, bet1, bet2, odds1, odds2, balance1, balance2, available
    # Title = String
    # Game date = date
    # bet1, bet2 = String
    # odds1, odds2 = decimal

    games = mongo.db.games
    # Iterate through all available games
    if request.method == 'POST':

        if 'bookie' in session:
            # Expecting {"title": "title", "date": 'date', '}
            gameData = request.json

            games.insert({
                'title': gameData["title"],
                'active': True, 
                'date': gameData["date"],
                'desc': gameData["desc"], # Game description
                'choices': [
                    { # Choice 1
                        'title': gameData["choice1"],
                        'value': gameData["odds1"],
                        'balance': 0
                    },
                    { # Choice 2
                        'title': gameData["choice2"],
                        'value': gameData["odds2"],
                        'balance': 0
                    }
                ]
            })

            return make_response(jsonify(response = 'game: '+gameData['title']+' added to database', status = 201), 201)

    if request.method == 'GET':
        # Initialize list of games
        listGames = []
        # Get amount argument from GET Request
        amt = request.args.get('amount')
        
        # Default
        if amt is None:
            amt = 5

        cur = games.find()[0:int(amt)]

        # Add all games into list of games
        for i in cur:
            listGames.append(i)
        
        # Dump JSON into response
        return make_response(jsonify(data = json.loads(json.dumps(listGames, default=json_util.default)), status = 200), 200)
    
    # Not logged in
    return make_response(jsonify(response = 'forbidden', status = 403), 403)
        

# BET Routes

@app.route('/api/v1/bets', methods=['GET','POST'])
def new_bet():
    if request.method == 'POST':
        # Check if user is logged in
        if "username" in session:

            # Get data from Mongodb
            User = mongo.db.users.find_one({'username': session['username']})
            userId = User.get('_id')

            # Get data from request
            gameId = request.json['gameId']
            Game = mongo.db.games.find_one({"_id": gameId})

            betAmt = int(request.json['betAmt'])
            currency = request.json['currency'] # Either "nano" or "btc"

            # Refactor later, might have to add schema to bets
            # Squatter validators
            choice = request.json['choiceId']
            if choice != 1 or 2:
                return make_response(jsonify(response = "invalid bet choice", status = 400), 400)
            if Game == None:
                return make_response(jsonify(response = "invalid game", status = 400), 400)
            if Game['active'] == False:
                return make_response(jsonify(response = "game closed", status = 400), 400)
            
            # Reduce balance from user balance and transfer to bet balance
            userBalance = int(User["balances"]["nano"])
            newBalance = userBalance - betAmt
            # Credit balance of game
            if updateGameBalance(choice, betAmt, gameId) is False:
                return make_response(jsonify(response = "Error in placing bet", status = 400), 400)

            if nanoapi.updateBalance(newBalance, session["username"]):
                # Only open bets connection after conditional to save resources against user mistakes
                bets = mongo.db.bets
                # Insert into MongoDB bets Collection
                _id = bets.insert({
                    "gId": gameId,
                    "uId": userId,
                    "cId": choice, # 1 or 2
                    "curr": currency,
                    "amount": betAmt,
                    "active": True
                })

                # Update Bet timestamp
                date = bets.update_one({'_id': _id}, {'$currentDate': {
                    "date": {'$type': 'date'} # Timestamp type in MongoDB
                }}, upsert = True) # Insert if not already there
                Bet = bets.find_one({'_id': _id})

                # Echo bet ID and game ID
                return make_response(jsonify(response = "Bet successfully placed",timestamp = str(Bet['date']), betId = str(_id), gameId = gameId, status = 201), 201)
            
            else:
                return make_response(jsonify(response = "Error in placing bet", status = 400), 400)

    if request.method == 'GET':
        if "username" in session:

            bets = mongo.db.bets
            User = mongo.db.users.find_one({"username": session["username"]})
            uId = User["_id"]
            
            # Amount management
            amt = request.args.get('amount')

            if amt != None:
                if amt > 50:
                    return make_response(jsonify(response = "amount must be less than or equal to 50.", status = 400), 400)
                activeBets = bets.find({"uId": uId})[0:amt]
            
            activeBets = bets.find({"uId": uId})[0:10]
            listBets = []

            for bet in activeBets:
                listBets.append(bet)

            # Successful retrieval
            return make_response(jsonify(data = json.loads(json.dumps(listBets, default=json_util.default)), status = 200), 200)

        # Not Logged In
        return make_response(jsonify(response = 'must be logged in to view', status = 403), 403)

    # Wrong method
    return make_response(jsonify(response = "something went wrong", status=405), 405)