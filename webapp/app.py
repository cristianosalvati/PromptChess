import os
import sys
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.services import LoginService, SessionManager

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'promptchess-dev-key-change-in-prod')
CORS(app)

login_service = None
session_manager = None

def get_login_service():
    global login_service
    if login_service is None:
        login_service = LoginService()
    return login_service

def get_session_manager():
    global session_manager
    if session_manager is None:
        session_manager = SessionManager()
    return session_manager


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'session_token' not in session:
            return redirect(url_for('login'))
        
        ls = get_login_service()
        validation = ls.validate_session(session['session_token'])
        
        if not validation['valid']:
            session.clear()
            flash('Session expired. Please login again.', 'warning')
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    if 'session_token' in session:
        return redirect(url_for('menu'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter username and password.', 'error')
            return render_template('login.html')
        
        ls = get_login_service()
        result = ls.authenticate(username, password)
        
        if result['success']:
            session['session_token'] = result['session_token']
            session['username'] = result['username']
            session['user_id'] = result['user_id']
            return redirect(url_for('menu'))
        else:
            flash(result['error'], 'error')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        email = request.form.get('email', '').strip() or None
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        ls = get_login_service()
        result = ls.register_user(username, password, email)
        
        if result['success']:
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash(result['error'], 'error')
    
    return render_template('register.html')


@app.route('/logout')
def logout():
    if 'session_token' in session:
        ls = get_login_service()
        ls.logout(session['session_token'])
    
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/menu')
@login_required
def menu():
    username = session.get('username', 'Player')
    
    sm = get_session_manager()
    recent_games = sm.get_user_sessions(username)
    
    ls = get_login_service()
    profile = ls.get_user_profile(username)
    
    return render_template('menu.html', 
                         username=username,
                         profile=profile,
                         recent_games=recent_games)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    username = session.get('username')
    ls = get_login_service()
    
    if request.method == 'POST':
        display_name = request.form.get('display_name', '').strip()
        
        if display_name:
            ls.update_profile(username, {'display_name': display_name})
            flash('Profile updated successfully.', 'success')
    
    user_profile = ls.get_user_profile(username)
    return render_template('profile.html', profile=user_profile)


@app.route('/game/new', methods=['POST'])
@login_required
def new_game():
    username = session.get('username')
    user_id = session.get('user_id')
    
    sm = get_session_manager()
    game_session = sm.create_game_session(user_id, username)
    
    return redirect(url_for('game', session_id=game_session.session_id))


@app.route('/game/<session_id>')
@login_required
def game(session_id):
    sm = get_session_manager()
    game_session = sm.get_session(session_id)
    
    if not game_session:
        flash('Game session not found.', 'error')
        return redirect(url_for('menu'))
    
    if game_session.username != session.get('username'):
        flash('Access denied.', 'error')
        return redirect(url_for('menu'))
    
    return render_template('game.html', 
                         session_id=session_id,
                         board_state=game_session.board_state,
                         current_turn=game_session.current_turn,
                         move_history=game_session.move_history)


@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'service': 'PromptChess Webapp'
    })


@app.route('/api/game/<session_id>/move', methods=['POST'])
@login_required
def api_make_move(session_id):
    sm = get_session_manager()
    game_session = sm.get_session(session_id)
    
    if not game_session:
        return jsonify({'success': False, 'error': 'Game session not found'}), 404
    
    if game_session.username != session.get('username'):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    if game_session.current_turn != 'white':
        return jsonify({'success': False, 'error': 'Not your turn'}), 400
    
    data = request.get_json() or {}
    piece = data.get('piece', 'P')
    from_sq = data.get('from_sq', '')
    to_sq = data.get('to_sq', '')
    
    if not from_sq or not to_sq:
        return jsonify({'success': False, 'error': 'Missing move coordinates'}), 400
    
    import json as json_module
    game_session.record_move({
        'piece': piece,
        'from': from_sq,
        'to': to_sq
    })
    
    prompt = f'''
Mossa dei Bianchi: {piece} {from_sq}-{to_sq}
Stato scacchiera attuale:
{json_module.dumps(game_session.board_state, indent=2)}

Proponi la tua mossa per i Neri e aggiorna lo stato della scacchiera.
Rispondi in JSON con: neri, bianchi, mossa_proposta, commento_giocatore, messaggio_avversario.
'''
    
    try:
        ai_response = game_session.send_to_llm(prompt, model='gpt-4.1-nano', temperature=0.7)
        
        try:
            parsed = json_module.loads(ai_response)
            ai_move = parsed.get('mossa_proposta', '')
            ai_comment = parsed.get('commento_giocatore', '')
            ai_message = parsed.get('messaggio_avversario', '')
            
            if 'neri' in parsed and 'bianchi' in parsed:
                game_session.board_state = {
                    'neri': parsed['neri'],
                    'bianchi': parsed['bianchi']
                }
            
            if ai_move:
                parts = ai_move.replace('-', ' ').split()
                if len(parts) >= 2:
                    game_session.record_move({
                        'piece': 'p',
                        'from': parts[0],
                        'to': parts[1] if len(parts) > 1 else parts[0],
                        'ai_message': ai_message
                    })
            
            sm.save_session(game_session)
            
            return jsonify({
                'success': True,
                'ai_move': ai_move,
                'ai_comment': ai_comment,
                'ai_message': ai_message,
                'board_state': game_session.board_state,
                'current_turn': game_session.current_turn,
                'move_history': game_session.move_history
            })
            
        except json_module.JSONDecodeError:
            return jsonify({
                'success': False,
                'error': 'AI returned invalid JSON',
                'raw_response': ai_response[:500]
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/game/<session_id>/state')
@login_required
def api_game_state(session_id):
    sm = get_session_manager()
    game_session = sm.get_session(session_id)
    
    if not game_session:
        return jsonify({'success': False, 'error': 'Game session not found'}), 404
    
    if game_session.username != session.get('username'):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'board_state': game_session.board_state,
        'current_turn': game_session.current_turn,
        'move_history': game_session.move_history,
        'status': game_session.status
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
