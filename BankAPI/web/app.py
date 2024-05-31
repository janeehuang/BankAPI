from flask import Flask, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt

app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.BankAPI
users = db["users"]


def user_exist(username):
    if users.count_documents({"username":username}) == 0:
        return False
    else:
        return True


class Register(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]

        if user_exist(username):
            retJson = {
                "status" : 301,
                "msg" : "Invalid username"

            }
            return retJson

        hashed_pw  = bcrypt.hashpw(password.encode("utf8"),bcrypt.gensalt())

        users.insert_one({
            "username" : username,
            "password" : hashed_pw,
            "own" : 0,
            "debt" : 0
        })

        retJson = {
            "status" : 200,
            "msg" : "You've register successfully"
        }
        return retJson


def verify_pw(username, password):
    if not user_exist(username):
        return False

    hashed_pw = users.find({
        "username" : username
    })[0]["password"]

    if bcrypt.hashpw(password.encode("utf8"),hashed_pw) == hashed_pw:
        return True
    else:
        return False


def cash_with_user(username):
    cash = users.find({
        "username":username
    })[0]["own"]
    return cash


def debt_with_user(username):
    debt = users.find({
        "username":username
    })[0]["debt"]
    return debt

def gen_return_dic(status, msg):
    retJson = {
        "status" : status,
        "msg" : msg
    }
    return retJson

def verify_credentials(username, password):
    if not user_exist(username):
        return gen_return_dic(301, "Invalid username"), True

    correct_pw = verify_pw(username, password)

    if not correct_pw:
        return gen_return_dic(302,"Incorrect password"), True
    
    return None, False

def update_account(username, balance):
    users.update_one({
        "username":username
    },{
        "$set" : {
            "own" : balance
        }
    })


def update_debt(username, balance):
    users.update_one({
        "username":username
    },{
        "$set" : {
            "debt" : balance
        }
    })

class Add(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        money = postedData["amount"]

        retJson, error = verify_credentials(username, password)

        if error:
            return retJson

        if money <= 0:
            return gen_return_dic(304,"The money amount entered must be > 0")

        cash = cash_with_user(username)
        money -= 1
        bank_cash = cash_with_user("Bank")
        update_account("Bank", bank_cash + 1)
        update_account(username, cash + money)

        return gen_return_dic(200,"Amount added successfully to account."), True


class Transfer(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        to = postedData["to"]
        money = postedData["amount"]

        retJson, error = verify_credentials(username, password)

        if error:
            return retJson

        cash = cash_with_user(username)
        if cash <= 0:
            return gen_return_dic(304,"You're out of money, please add or take a loan")
        
        if not user_exist(to):
            return gen_return_dic(301,"Recieve username is invalid.")
        
        cash_from = cash_with_user(username)
        cash_to = cash_with_user(to)
        bank_cash = cash_with_user("Bank")

        update_account("Bank", bank_cash + 1)
        update_account(to, cash_to + money-1)
        update_account(username, cash_from - money)


        return gen_return_dic(200, "Amount Transfered successully.")

class Balance(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]

        retJson, error = verify_credentials(username, password)

        if error:
            return retJson

        retJson = users.find({
            "username" : username
        },{
            "password" : 0,
            "_id" :0
        })[0]

        return retJson

class TakeLoan(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        money = postedData["amount"]

        retJson, error = verify_credentials(username, password)

        if error:
            return retJson

        cash = cash_with_user(username)
        debt = debt_with_user(username)
        update_account(username, cash + money)
        update_debt(username, debt + money)

        return gen_return_dic(200, "Loan added to your account.")



class PayLoan(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        money = postedData["amount"]

        retJson, error = verify_credentials(username, password)

        if error:
            return retJson
        
        cash = cash_with_user(username)

        if cash < money:
            return gen_return_dic(303, "Not enough money in your account")

        debt = debt_with_user(username)

        update_account(username, cash - money)
        update_debt(username, debt - money)

        return gen_return_dic(200, "You've successfully paid your loan.")

api.add_resource(Register,"/register")
api.add_resource(Add,"/add")
api.add_resource(Balance,"/balance")
api.add_resource(Transfer,"/transfer")
api.add_resource(TakeLoan,"/takeloan")
api.add_resource(PayLoan,"/payloan")

if __name__ == "__main__":
    app.run(host="0.0.0.0")