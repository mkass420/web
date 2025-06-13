from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json
from sqlalchemy import func

app = Flask(__name__, 
    static_url_path='',
    static_folder='static',
    template_folder='templates'
)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///beer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class BeerConsumption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64), nullable=False)
    username = db.Column(db.String(128), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/track-beer', methods=['POST'])
def track_beer():
    data = request.get_json()
    print('Received data:', data)
    if not data or 'user_id' not in data or 'amount' not in data or 'username' not in data:
        print('Invalid data received')
        return jsonify({'error': 'Неверные данные'}), 400
    user_id = data['user_id']
    username = data['username']
    try:
        amount = float(data['amount'])
    except Exception:
        return jsonify({'error': 'Некорректное количество'}), 400
    now = datetime.now()
    consumption = BeerConsumption(user_id=user_id, username=username, amount=amount, date=now.date(), timestamp=now)
    db.session.add(consumption)
    db.session.commit()
    print(f'Saved to DB: {user_id}, {username}, {amount}, {now}')
    return jsonify({'success': True})

@app.route('/api/get-today-consumption')
def get_today_consumption():
    user_id = request.args.get('user_id')
    print(f'Getting today consumption for user: {user_id}')
    if not user_id:
        return jsonify({'error': 'Не указан ID пользователя'}), 400
    today = datetime.now().date()
    entries = BeerConsumption.query.filter_by(user_id=user_id, date=today).all()
    total_amount = sum(entry.amount for entry in entries)
    result_entries = [
        {'amount': entry.amount, 'time': entry.timestamp.isoformat()} for entry in entries
    ]
    return jsonify({'total_amount': total_amount, 'entries': result_entries})

@app.route('/api/get-all-consumption')
def get_all_consumption():
    user_id = request.args.get('user_id')
    print(f'Getting all consumption for user: {user_id}')
    if not user_id:
        return jsonify({'error': 'Не указан ID пользователя'}), 400
    entries = BeerConsumption.query.filter_by(user_id=user_id).order_by(BeerConsumption.date).all()
    # Группируем по дате
    stats = {}
    for entry in entries:
        date_str = entry.date.isoformat()
        stats.setdefault(date_str, 0)
        stats[date_str] += entry.amount
    # Преобразуем в список для фронта
    stats_list = [{'date': k, 'total': v} for k, v in stats.items()]
    return jsonify({'days': stats_list})

@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory('static/images', filename)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico')

@app.route('/api/rating-today')
def rating_today():
    today = datetime.now().date()
    results = db.session.query(
        BeerConsumption.user_id,
        BeerConsumption.username,
        func.sum(BeerConsumption.amount).label('total')
    ).filter(BeerConsumption.date == today) \
     .group_by(BeerConsumption.user_id, BeerConsumption.username) \
     .order_by(func.sum(BeerConsumption.amount).desc()) \
     .limit(10).all()
    rating = [
        {'user_id': r.user_id, 'username': r.username, 'total': r.total} for r in results
    ]
    return jsonify({'rating': rating})

@app.route('/api/rating-total')
def rating_total():
    results = db.session.query(
        BeerConsumption.user_id,
        BeerConsumption.username,
        func.sum(BeerConsumption.amount).label('total')
    ).group_by(BeerConsumption.user_id, BeerConsumption.username) \
     .order_by(func.sum(BeerConsumption.amount).desc()) \
     .limit(10).all()
    rating = [
        {'user_id': r.user_id, 'username': r.username, 'total': r.total} for r in results
    ]
    return jsonify({'rating': rating})

if __name__ == '__main__':
    app.run(host='::', port=5000) 