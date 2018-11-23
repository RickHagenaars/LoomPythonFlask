from flask import Flask
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime, os, json

# Database connection string.
DATABASE_URI = 'postgres://ggwlaqyx:TsVyUX3Yi07gtpo-feZqI96EcckH7a-v@elmer.db.elephantsql.com:5432/ggwlaqyx'

# Define the maximum of key value pairs which will be sent from the LOOM node or LOOM hub.
MAX_KEY_VALUE_PAIRS = 32

# Define the LOOM keys which should be ignored.
IGNORE_KEYS = [ 'devid', 'tabID' ]

# Define generic keys which should be stored with each sub measurement.
GENERIC_KEYS = [ 'deviceID', 'sheetID' ]

app = Flask(__name__, static_url_path='')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# db.create_all()
# db.session.commit()

class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device = db.Column(db.String(100), unique=False, nullable=False)
    timestamp = db.Column(DateTime, default=datetime.datetime.utcnow)
    type = db.Column(db.String(100), unique=False, nullable=False)
    value = db.Column(db.String(100), unique=False, nullable=False)

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'device'         : self.device,
           'timestamp'      : self.timestamp.isoformat(),
           'type'           : self.type,
           'value'          : self.value
       }

    @property
    def getDevice(self):
        """Return device from measurement"""
        return self.device

    @property
    def getType(self):
        """Return type from measurement"""
        return self.type

measurements = [];

# On IBM Cloud Cloud Foundry, get the port number from the environment variable PORT.
# When running this app on the local machine, default the port to 8000.
port = int(os.getenv('PORT', 8000))

@app.route('/')
def root():
    return app.send_static_file('index.html')

@app.route('/devices', methods=['GET'])
def get_devices():
    query = db.session.query(Measurement).distinct(Measurement.device)
    return jsonify([i.getDevice for i in query.all()])

@app.route('/types', methods=['GET'])
def get_types():
    query = db.session.query(Measurement).distinct(Measurement.type)

    # Apply optional filters.
    if request.args.get('device'): 
        query = query.filter_by(device='%s' % request.args.get('device'))

    return jsonify([i.getType for i in query.all()])

@app.route('/measurements', methods=['GET'])
def get_measurements():
    query = Measurement.query

    # Apply optional filters.
    if request.args.get('device'): 
        query = query.filter_by(device='%s' % request.args.get('device'))
    if request.args.get('type'): 
        query = query.filter_by(type='%s' % request.args.get('type'))

    return jsonify([i.serialize for i in reversed(query.order_by(Measurement.timestamp.desc()).limit(500).all())])

@app.route('/pushingbox', methods=['GET'])
def insert():
    generic = {}

    # Extract generic keys from query params.
    for i in range(MAX_KEY_VALUE_PAIRS):
        if request.args.get('key%s' % i) and request.args.get('key%s' % i) in GENERIC_KEYS:
            generic[request.args.get('key%s' % i)] = request.args.get('val%s' % i)

    # Extract measurement values.
    for i in range(MAX_KEY_VALUE_PAIRS):
        if request.args.get('key%s' % i) and request.args.get('key%s' % i) not in IGNORE_KEYS and request.args.get('key%s' % i) not in GENERIC_KEYS:
            measurement = Measurement(device="%s_%s" % (generic['sheetID'], generic['deviceID']), type=request.args.get('key%s' % i), value=request.args.get('val%s' % i))
            db.session.add(measurement)

    # Commit all measurements to database.
    db.session.commit()
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)