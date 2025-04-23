from flask import Flask, render_template, jsonify, request, session
import sqlite3
import random
from flask_cors import CORS
from flask_session import Session

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
CORS(app)

DB_PATH = 'sgu_fragen.db'

def get_random_question():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM fragen ORDER BY RANDOM() LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'id': row[0],
            'frage': row[1],
            'antworten': {
                'a': row[2],
                'b': row[3],
                'c': row[4],
                'd': row[5]
            },
            'richtige_antwort': row[6]
        }
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/frage')
def frage():
    falsch_ids = session.get('wiederholen', [])
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if falsch_ids:
        id_str = ','.join('?' for _ in falsch_ids)
        cursor.execute(f"SELECT * FROM fragen WHERE id IN ({id_str}) ORDER BY RANDOM() LIMIT 1", falsch_ids)
    else:
        cursor.execute("SELECT * FROM fragen ORDER BY RANDOM() LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        frage = {
            'id': row[0],
            'frage': row[1],
            'antworten': {
                'a': row[2],
                'b': row[3],
                'c': row[4],
                'd': row[5]
            },
            'richtige_antwort': row[6]
        }
        session['letzte_frage'] = frage
        return jsonify(frage)
    return jsonify({'error': 'Keine Frage gefunden'})

@app.route('/api/antwort', methods=['POST'])
def antwort():
    daten = request.get_json()
    user_antwort = daten.get('antwort')
    frage = session.get('letzte_frage')
    if not frage:
        return jsonify({'error': 'Keine Frage in der Session'}), 400
    richtig = frage['richtige_antwort'] == user_antwort
    wiederholen = session.get('wiederholen', [])
    if not richtig and frage['id'] not in wiederholen:
        wiederholen.append(frage['id'])
    elif richtig and frage['id'] in wiederholen:
        wiederholen.remove(frage['id'])
    session['wiederholen'] = wiederholen
    return jsonify({'richtig': richtig, 'korrekt': frage['richtige_antwort']})

@app.route('/api/reset', methods=['POST'])
def reset():
    session['wiederholen'] = []
    return jsonify({'status': 'reset'})

if __name__ == '__main__':
    app.run(debug=True)
