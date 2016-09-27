import requests
from smtpd import SMTPServer
import Queue
import threading
import asyncore
import re

BASE_URL = 'http://localhost:5006'


def main():
    q = capture_smtp()

    r = requests.post(
        BASE_URL + '/shop/users/',
        json={'username': 'kim@example.com', 'password': 'secret'})
    r.raise_for_status()
    print r.json()

    msg = q.get(timeout=2)
    m = re.search(r'https://shop.milners.ca/confirm-account/(.*)"',
                  msg['data'])
    token = m.group(1)
    print 'confirm token', token

    r = requests.get(BASE_URL + '/shop/confirmation/' + token)
    r.raise_for_status()
    print r.json()

    r = requests.post(BASE_URL + '/shop/confirmation/' + token)
    r.raise_for_status()
    print r.json()

    r = requests.post(
        BASE_URL + '/shop/auth/',
        json={'username': 'kim@example.com', 'password': 'secret'})
    r.raise_for_status()
    token = r.json()['token']
    print token

    for i in xrange(10):
        r = requests.get(BASE_URL + '/shop/auth/' + token)
        r.raise_for_status()
        print r.json()

    r = requests.post(BASE_URL + '/shop/users/kim@example.com/password',
                      json={'old': 'secret', 'new': 'top secret'})
    r.raise_for_status()
    print r.json()

    r = requests.post(BASE_URL + '/shop/password-resets/',
                      json={'username': 'kim@example.com'})
    r.raise_for_status()
    print r.json()
    msg = q.get(timeout=2)
    m = re.search(r'https://shop.milners.ca/reset/(.*)"', msg['data'])
    reset_token = m.group(1)
    print 'reset token:', reset_token
    print msg['to']

    r = requests.get(BASE_URL + '/shop/password-resets/' + reset_token)
    r.raise_for_status()
    print r.json()

    r = requests.post(BASE_URL + '/shop/password-resets/' + reset_token,
                      json={'password': '1234'})
    r.raise_for_status()
    print r.json()

    r = requests.post(
        BASE_URL + '/shop/auth/',
        json={'username': 'kim@example.com', 'password': '1234'})
    r.raise_for_status()
    print r.json()
    token = r.json()['token']

    r = requests.post(
        BASE_URL + '/shop/address-changes/',
        json={'password': '1234',
              'old': 'kim@example.com',
              'new': 'kim@example.ca'})
    r.raise_for_status()
    print r.json()

    msg = q.get(timeout=2)
    m = re.search('https://shop.milners.ca/address-changes/(.*)"', msg['data'])
    token = m.group(1)
    print 'new address token:', token

    r = requests.post(BASE_URL + '/shop/address-changes/' + token)
    r.raise_for_status()
    print r.json()

    r = requests.post(
        BASE_URL + '/shop/auth/',
        json={'username': 'kim@example.ca', 'password': '1234'})
    r.raise_for_status()
    print r.json()


def capture_smtp():
    q = Queue.Queue()

    def work():
        SMTPCaptureServer(q)
        asyncore.loop()

    worker = threading.Thread(target=work)
    worker.daemon = True
    worker.start()
    return q


class SMTPCaptureServer(SMTPServer):
    def __init__(self, q):
        SMTPServer.__init__(self, ('127.0.0.1', 5007), None)
        self.q = q

    def process_message(self, peer, mailfrom, rcpttos, data):
        self.q.put({
            'peer': peer,
            'from': mailfrom,
            'to': rcpttos,
            'data': data
        })


if __name__ == '__main__':
    main()
