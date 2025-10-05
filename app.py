from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 데이터 저장을 위한 JSON 파일
DATA_FILE = 'data.json'

def load_data():
    """데이터 파일에서 정보를 로드합니다."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"stocks": [], "transactions": []}

def save_data(data):
    """데이터를 파일에 저장합니다."""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    """메인 페이지 - Stock 분석과 동일"""
    return render_template('stock_analysis.html')

@app.route('/stock-analysis')
def stock_analysis():
    """Stock 분석 페이지"""
    return render_template('stock_analysis.html')

@app.route('/tax-analysis')
def tax_analysis():
    """Tax 분석 페이지"""
    return render_template('tax_analysis.html')

@app.route('/economy-trade')
def economy_trade():
    """Economy & Trade 페이지"""
    return render_template('economy_trade.html')

@app.route('/favicon.ico')
def favicon():
    """파비콘 서빙"""
    return send_from_directory(os.path.join(app.root_path, 'static', 'images'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    """주식 목록 조회"""
    data = load_data()
    return jsonify(data['stocks'])

@app.route('/api/stocks', methods=['POST'])
def add_stock():
    """새 주식 추가"""
    data = load_data()
    stock_data = request.json
    
    # 새 주식 객체 생성
    new_stock = {
        'id': len(data['stocks']) + 1,
        'name': stock_data.get('name'),
        'symbol': stock_data.get('symbol'),
        'quantity': int(stock_data.get('quantity', 0)),
        'price': float(stock_data.get('price', 0)),
        'added_date': datetime.now().isoformat()
    }
    
    data['stocks'].append(new_stock)
    save_data(data)
    
    return jsonify(new_stock), 201

@app.route('/api/stocks/<int:stock_id>', methods=['PUT'])
def update_stock(stock_id):
    """주식 정보 수정"""
    data = load_data()
    
    for stock in data['stocks']:
        if stock['id'] == stock_id:
            stock_data = request.json
            stock['name'] = stock_data.get('name', stock['name'])
            stock['symbol'] = stock_data.get('symbol', stock['symbol'])
            stock['quantity'] = int(stock_data.get('quantity', stock['quantity']))
            stock['price'] = float(stock_data.get('price', stock['price']))
            
            save_data(data)
            return jsonify(stock)
    
    return jsonify({'error': 'Stock not found'}), 404

@app.route('/api/stocks/<int:stock_id>', methods=['DELETE'])
def delete_stock(stock_id):
    """주식 삭제"""
    data = load_data()
    
    for i, stock in enumerate(data['stocks']):
        if stock['id'] == stock_id:
            deleted_stock = data['stocks'].pop(i)
            save_data(data)
            return jsonify(deleted_stock)
    
    return jsonify({'error': 'Stock not found'}), 404

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    """거래 내역 조회"""
    data = load_data()
    return jsonify(data['transactions'])

@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    """새 거래 추가"""
    data = load_data()
    transaction_data = request.json
    
    # 새 거래 객체 생성
    new_transaction = {
        'id': len(data['transactions']) + 1,
        'stock_id': transaction_data.get('stock_id'),
        'type': transaction_data.get('type'),  # 'buy' or 'sell'
        'quantity': int(transaction_data.get('quantity', 0)),
        'price': float(transaction_data.get('price', 0)),
        'date': transaction_data.get('date', datetime.now().isoformat())
    }
    
    data['transactions'].append(new_transaction)
    save_data(data)
    
    return jsonify(new_transaction), 201

@app.route('/api/portfolio/summary')
def portfolio_summary():
    """포트폴리오 요약 정보"""
    data = load_data()
    
    total_value = 0
    total_profit = 0
    
    for stock in data['stocks']:
        stock_value = stock['quantity'] * stock['price']
        total_value += stock_value
        
        # 거래 내역에서 수익/손실 계산
        stock_transactions = [t for t in data['transactions'] if t['stock_id'] == stock['id']]
        
        for transaction in stock_transactions:
            if transaction['type'] == 'buy':
                total_profit -= transaction['quantity'] * transaction['price']
            elif transaction['type'] == 'sell':
                total_profit += transaction['quantity'] * transaction['price']
    
    return jsonify({
        'total_value': total_value,
        'total_profit': total_profit,
        'total_stocks': len(data['stocks'])
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# Vercel용 WSGI 애플리케이션
app.wsgi_app = app.wsgi_app
