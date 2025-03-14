from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/entrance_LPR', methods=['POST'])
def send_message():
    data = request.json
    current_time = datetime.now().strftime("%H:%M %d/%m/%Y")
    vehicle_info = {
        'license_plate': data.get('license_plate', ''),
        'vehicle_owner': data.get('vehicle_owner', ''),
        'entry_time': current_time
    }

    if all(k in vehicle_info and vehicle_info[k] for k in ['license_plate', 'vehicle_owner']):
        socketio.emit('vehicle_info', vehicle_info)
        return jsonify({
            'status': 'Vehicle information sent successfully',
            'data': vehicle_info
        }), 200
    return jsonify({'error': 'Incomplete vehicle information'}), 400

@app.route('/exit_LPR', methods=['POST'])
def send_data_exit():
    data = request.json
    current_time = datetime.now().strftime("%H:%M %d/%m/%Y")
    exit_vehicle_info = {
        'license_plate': data.get('license_plate', ''),
        'vehicle_owner': data.get('vehicle_owner', ''),
        'exit_time': current_time
    }

    if all(k in exit_vehicle_info and exit_vehicle_info[k] for k in ['license_plate', 'vehicle_owner']):
        socketio.emit('vehicle_exit', exit_vehicle_info)
        return jsonify({
            'status': 'Vehicle exit information sent successfully',
            'data': exit_vehicle_info
        }), 200
    return jsonify({'error': 'Incomplete vehicle information'}), 400

@socketio.on('connect')
def handle_connect():
    print("A client connected!")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)