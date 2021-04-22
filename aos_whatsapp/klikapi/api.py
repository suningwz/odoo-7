from odoo import _
from odoo.exceptions import Warning, UserError
import json
import requests
import html2text
import datetime

class KlikApi(object):
    def __init__(self, klik_key, klik_secret, **kwargs):
        self.APIUrl = 'https://klikodoo.id/api/wa/'
        self.klik_key = klik_key or ''
        self.klik_secret = klik_secret or ''
    
    def auth(self):
        #if not self.klik_key and not self.klik_secret:
        #    raise UserError(_('Warning! Please add Key and Secret Whatsapp API on General Settings'))
        try:
            requests.get(self.APIUrl+'status/'+self.klik_key+'/'+self.klik_secret, headers={'Content-Type': 'application/json'})
        except (requests.exceptions.HTTPError,
                requests.exceptions.RequestException,
                requests.exceptions.ConnectionError) as err:
            raise Warning(_('Error! Could not connect to Whatsapp account. %s')% (err))
    
    def logout(self):
        url = self.APIUrl + 'logout'
        data = {}
        data['instance'] = self.klik_key
        data['key'] = self.klik_secret
        data_s = {
            'params' : data
        }
        req = requests.post(url, json=data_s, headers={'Content-Type': 'application/json'})
        res = json.loads(req.text)
        return res['result']
    
    def get_request(self, method, data):
        url = self.APIUrl + 'get/' + self.klik_key +'/' + self.klik_secret + '/' + method
        data_req = requests.get(url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
        res = json.loads(data_req.text)
        return res.get('result') and res['result'] or {}
    
    def post_request(self, method, data):
        url = self.APIUrl + 'post/'
        data= json.loads(data)
        data['instance'] = self.klik_key
        data['key'] = self.klik_secret
        data['method'] = method
        data_s = {
            'params' : data
        }
        request = requests.post(url, json=data_s, headers={'Content-Type': 'application/json'})
        if request.status_code == 200:
            message1 = json.loads(request.text)
            message = message1.get('result').get('message')
            chatID = message.get('id') and message.get('id').split('_')[1]
            return {'chatID': chatID, 'message': message}
        else:
            return {'message': {'sent': False, 'message': 'Error'}}
    
    def get_phone(self, method, phone):
        url = self.APIUrl + 'post/' + self.klik_key + '/'+self.klik_secret +'/'+ method + '/' + phone
        data = requests.get(url, headers={'Content-Type': 'application/json'})
        res = json.loads(data.text)
        return res.get('result') and res['result'] or {}