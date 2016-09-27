from . import app
from . import brisbane


def send_confirm_new_user_message(tenant, user, token):
    # TODO: Should we send this in a different process?
    t = app.config['TENANTS'][tenant]
    confirm_url = t['confirm_address_url'] % {'token': token}
    params = {'name': t['name'], 'url': t['url'], 'confirm_url': confirm_url}
    with connect_smtp() as mailer:
        mailer.send({
            'to': [user],
            'from': t['email'],
            'subject': 'Welcome - Confirm email address',
            'text': CONFIRM_ADDRESS_TEXT_TEMPLATE % params,
            'html': CONFIRM_ADDRESS_HTML_TEMPLATE % params,
        })


def send_password_reset_message(tenant, user, token):
    # TODO: Should we send this in a different process?
    t = app.config['TENANTS'][tenant]
    confirm_url = t['password_reset_url'] % {'token': token}
    params = {'name': t['name'], 'url': t['url'], 'confirm_url': confirm_url}
    with connect_smtp() as mailer:
        mailer.send({
            'to': [user],
            'from': t['email'],
            'subject': 'Forgot password',
            'text': PASSWORD_RESET_TEXT_TEMPLATE % params,
            'html': PASSWORD_RESET_HTML_TEMPLATE % params,
        })


def send_address_change_message(tenant, user, token):
    # TODO: Should we send this in a different process?
    t = app.config['TENANTS'][tenant]
    confirm_url = t['address_change_url'] % {'token': token}
    params = {'name': t['name'], 'url': t['url'], 'confirm_url': confirm_url}
    with connect_smtp() as mailer:
        mailer.send({
            'to': [user],
            'from': t['email'],
            'subject': 'Forgot password',
            'text': ADDRESS_CHANGE_TEXT_TEMPLATE % params,
            'html': ADDRESS_CHANGE_HTML_TEMPLATE % params,
        })


CONFIRM_ADDRESS_TEXT_TEMPLATE = '''
Welcome to the %(name)s (%(url)s) site. Please open this link to confirm your
address and use your new account: %(confirm_url)s.
'''

CONFIRM_ADDRESS_HTML_TEMPLATE = '''
<p>Welcome to the <a href="%(name)s">%(url)s</a> site.</p>
<p>
  Please use this <a href="%(confirm_url)s">link</a> to confirm your address
  and use your new account: <a href="%(confirm_url)s">%(confirm_url)s</a>.
</p>
'''

PASSWORD_RESET_TEXT_TEMPLATE = '''
It seems you've forgotten you password for the %(name)s (%(url)s) site.
Please open this link to reset your password: %(confirm_url)s.
'''

PASSWORD_RESET_HTML_TEMPLATE = '''
<p>
    It seems you've forgotten your password for the
    <a href="%(name)s">%(url)s</a> site.
</p>
<p>
  Please open this <a href="%(confirm_url)s">link</a> to reset your password:
  <a href="%(confirm_url)s">%(confirm_url)s</a>.
</p>
'''

ADDRESS_CHANGE_TEXT_TEMPLATE = '''
Congratulations on your new email address. Please confirm your new address
on %(name)s (%(url)s) by opening this link: %(confirm_url)s
'''

ADDRESS_CHANGE_HTML_TEMPLATE = '''
<p>
    Congratulations on your new email address. Please confirm your new address
    on <a href="%(name)s">%(url)s</a> site by clicking this link:
    <a href="%(confirm_url)s">%(confirm_url)s</a>.
</p>
'''


def connect_smtp():
    return brisbane.connect(
        app.config['SMTP_HOST'],
        app.config['SMTP_PORT'],
        app.config['SMTP_USERNAME'],
        app.config['SMTP_PASSWORD'],
        app.config['SMTP_SECURE'])
