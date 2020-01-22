import unittest

import os,sys
sys.path.append('..')
import app, nanoapi
import json, requests


baseURL = "http://localhost:5000/api/v1"

class TestApp(unittest.TestCase):

    def setUp(self):
        self.dataBase = app.mongo.db
        pass
    
    def tearDown(self):

        pass

    def testIndex(self):
        res = requests.get(url = baseURL)
        expected = {"response": "sportsbook api v1", "status": 200}
        assert res.json() == expected

    def testRegister(self):
        userName = "username"
        passWord = "password"
        data = {"username": userName,"password": passWord}
        res = requests.post(url = baseURL+"/user/register", data = json.dumps(data))
        User = self.dataBase.users.find_one({"username": userName})

        assert res.json()["status"] == 201
        assert User != None

    def testLogout(self):
        pass

    def testLogin(self):
        pass
        
if __name__ == "__main__":
    unittest.main()