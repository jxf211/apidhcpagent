from flask import Flask

from dhcp_app import dhcp_app

app = Flask(__name__)
app.register_blueprint(dhcp_app)
