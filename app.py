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

def extract_kapitel(frage_id):
    return frage_id.split('-')[0] if frage_id and '-' in frage_id else None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/kapitel')
def kapitel():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT substr(id, 1, instr(id, '-') - 1) as kapitel FROM fragen ORDER BY kapitel")
    kapitel_liste = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(kapitel_liste)

@app.route('/api/kapitel', methods=['POST'])
def kapitel_setzen():
    daten = request.get_json()
    kapitel = daten.get('kapitel')
    session['kapitel'] = kapitel
    session['wiederholen'] = []
    session['beantwortet'] = []
    session['aktueller_index'] = 0
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM fragen WHERE id LIKE ? ORDER BY id", (kapitel + '-%',))
    session['kapitel_ids'] = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify({'status': 'Kapitel gesetzt'})

@app.route('/api/frage')
def frage():
    kapitel = session.get('kapitel')
    kapitel_ids = session.get('kapitel_ids', [])
    beantwortet = session.get('beantwortet', [])
    wiederholen = session.get('wiederholen', [])

    unbeantwortet = [fid for fid in kapitel_ids if fid not in beantwortet and fid not in wiederholen]

    if unbeantwortet:
        frage_id = unbeantwortet[0]
    elif wiederholen:
        frage_id = wiederholen[0]
    else:
        return jsonify({'error': 'Keine Frage mehr in diesem Kapitel.'})

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM fragen WHERE id = ?", (frage_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        index = kapitel_ids.index(row[0]) if row[0] in kapitel_ids else 0
        frage = {
            'id': row[0],
            'frage': f"{row[0]}: {row[1]}",
            'antworten': {
                'a': row[2],
                'b': row[3],
                'c': row[4],
                'd': row[5]
            },
            'richtige_antwort': row[6],
            'beantwortet': index + 1,
            'gesamt': len(kapitel_ids)
        }
        session['letzte_frage'] = frage
        return jsonify(frage)

    return jsonify({'error': 'Keine Frage gefunden.'})

@app.route('/api/antwort', methods=['POST'])
def antwort():
    daten = request.get_json()
    user_antwort = daten.get('antwort')
    frage = session.get('letzte_frage')

    if not frage:
        return jsonify({'error': 'Keine Frage in der Session'}), 400

    richtig = frage['richtige_antwort'] == user_antwort
    wiederholen = session.get('wiederholen', [])
    beantwortet = session.get('beantwortet', [])

    if not richtig:
        if frage['id'] not in wiederholen:
            wiederholen.append(frage['id'])
    else:
        if frage['id'] not in beantwortet:
            beantwortet.append(frage['id'])
        if frage['id'] in wiederholen:
            wiederholen.remove(frage['id'])

    session['wiederholen'] = wiederholen
    session['beantwortet'] = beantwortet

    return jsonify({
        'richtig': richtig,
        'korrekt': frage['richtige_antwort'],
        'beantwortet': frage['beantwortet'],
        'gesamt': frage['gesamt']
    })

@app.route('/api/reset', methods=['POST'])
def reset():
    session.clear()
    return jsonify({'status': 'reset'})

if __name__ == '__main__':
    app.run(debug=True)
