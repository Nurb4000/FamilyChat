# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, g  
from markupsafe import escape
from sqlalchemy import create_engine, desc, Column, String, and_  
from sqlalchemy.orm import sessionmaker, joinedload  
from models import Base, User, Room, Post, Reply, room_user_association, PrivateMessageRoom, PrivateMessage
from database import init_database  
from config import Config  
import os  
from PIL import Image  
import uuid  
from werkzeug.utils import secure_filename  
from datetime import datetime  
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
app = Flask(__name__)  
csrf = CSRFProtect(app)
app.config.from_object(Config)
# **Initialize database**
engine = init_database()  
Session = sessionmaker(bind=engine)  
def get_db_session():  
    return Session()  
def login_required(f):  
    def wrapper(*args, **kwargs):  
        if 'user_id' not in session:  
            return redirect(url_for('login'))  
        return f(*args, **kwargs)  
    wrapper.__name__ = f.__name__  
    return wrapper  
def admin_required(f):  
    def wrapper(*args, **kwargs):  
        if 'user_id' not in session or not session.get('is_admin'):  
            flash('Access denied. Admin privileges required.')  
            return redirect(url_for('index'))  
        return f(*args, **kwargs)  
    wrapper.__name__ = f.__name__  
    return wrapper  
def allowed_file(filename):
    if not filename:
        return False
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in Config.ALLOWED_EXTENSIONS:
        return False
    # Prevent directory traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    return True

def validate_email(email):
    """Basic email format validation"""
    if not email or '@' not in email:
        return False
    local, domain = email.rsplit('@', 1)
    if not local or not domain:
        return False
    if '.' not in domain:
        return False
    # Prevent SQL injection via email field
    if ';' in email or '--' in email or "'" in email:
        return False
    return True

def resize_image(image_path, max_size):  
    """Resize image while maintaining aspect ratio"""  
    with Image.open(image_path) as img:  
        img.thumbnail(max_size, Image.LANCZOS)  
        img.save(image_path)
# **Password hashing functions (secure)**
def hash_password(password):
    """Hash a password using Werkzeug's secure method (pbkdf2)"""
    return generate_password_hash(password)
def verify_password(password, hashed_password):
    """Verify a password against its hash"""
    return check_password_hash(hashed_password, password)
# **Store previous_last_seen BEFORE updating it**
@app.before_request  
def store_previous_last_seen():  
    g.previous_last_seen = None  
    if 'user_id' in session and request.endpoint not in ['static', 'login', 'logout', 'signup']:  
        db_session = get_db_session()  
        try:  
            user = db_session.query(User).filter_by(id=session['user_id']).first()  
            if user:  
                g.previous_last_seen = user.last_seen  
            # **Update last_seen for next time**  
            user.last_seen = datetime.utcnow()  
            db_session.commit()  
        finally:  
            db_session.close()  
def is_user_authorized_for_room(user_id, room_id):
    """Check if user has access to a private room"""
    db_session = get_db_session()
    try:
        room = db_session.query(Room).filter_by(id=room_id).first()
        if not room:
            return False
        if not room.private:
            return True
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            return False
        return room in user.authorized_rooms
    finally:
        db_session.close()
def get_accessible_rooms(user_id):
    """Get all rooms accessible to a user (public + private rooms they're authorized for)"""
    db_session = get_db_session()
    try:
        public_rooms = db_session.query(Room).filter_by(private=False).order_by(Room.sort_order, Room.name).all()
        user = db_session.query(User).filter_by(id=user_id).first()
        if user:
            private_rooms = db_session.query(Room).filter(
                and_(Room.private == True, Room.id.in_(
                    db_session.query(room_user_association.c.room_id).filter_by(user_id=user_id)
                ))
            ).order_by(Room.sort_order, Room.name).all()
            accessible_rooms = public_rooms + private_rooms
        else:
            accessible_rooms = public_rooms
        return accessible_rooms
    finally:
        db_session.close()
def get_all_rooms():
    """Get all rooms for admin use"""
    db_session = get_db_session()
    try:
        return db_session.query(Room).order_by(Room.sort_order, Room.name).all()
    finally:
        db_session.close()
def get_private_message_rooms(user_id):
    """Get all private message rooms for a user"""
    db_session = get_db_session()
    try:
        return db_session.query(PrivateMessageRoom).filter(
            (PrivateMessageRoom.user1_id == user_id) | (PrivateMessageRoom.user2_id == user_id)
        ).all()
    finally:
        db_session.close()
def get_private_message_room(user1_id, user2_id):
    """Get or create a private message room between two users"""
    db_session = get_db_session()
    try:
        room = db_session.query(PrivateMessageRoom).filter(
            ((PrivateMessageRoom.user1_id == user1_id) & (PrivateMessageRoom.user2_id == user2_id)) |
            ((PrivateMessageRoom.user1_id == user2_id) & (PrivateMessageRoom.user2_id == user1_id))
        ).first()
        if not room:
            room = PrivateMessageRoom(user1_id=user1_id, user2_id=user2_id)
            db_session.add(room)
            db_session.commit()
        return room
    finally:
        db_session.close()
@app.route('/')  
def index():  
    if 'user_id' not in session:  
        return redirect(url_for('login'))  
    db_session = get_db_session()  
    try:  
        user = db_session.query(User).filter_by(id=session['user_id']).first()  
        last_seen = g.previous_last_seen if hasattr(g, 'previous_last_seen') and g.previous_last_seen else user.last_login if user else datetime.utcnow()  
        if session.get('is_admin'):
            rooms = get_all_rooms()
        else:
            rooms = get_accessible_rooms(session['user_id'])
        rooms = [room for room in rooms if not room.is_private_message_room]
        room_new_post_counts = {}  
        for room in rooms:  
            room_new_post_counts[room.id] = sum(  
                1 for post in room.posts  
                if post.created_at > last_seen  
            )  
    finally:  
        db_session.close()  
    return render_template('index.html', rooms=rooms, room_new_post_counts=room_new_post_counts)  
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        db_session = get_db_session()
        try:
            user = db_session.query(User).filter_by(username=username).first()
            # Use constant-time comparison to prevent timing attacks
            if user and verify_password(password, user.password) and user.enabled:
                session['user_id'] = user.id
                session['username'] = user.username
                session['is_admin'] = user.is_admin
                user.last_login = datetime.utcnow()
                if user.last_seen == datetime(2000, 1, 1, 0, 0, 0):
                    user.last_seen = datetime.utcnow()
                db_session.commit()
                return redirect(url_for('index'))
            else:
                if user and not user.enabled:
                    flash('Account is disabled. Please contact an administrator.')
                elif user and user.pending:
                    flash('Account is pending approval. Please contact an administrator.')
                else:
                    flash('Invalid username or password')
                return redirect(url_for('login'))
        finally:
            db_session.close()
    return render_template('login.html')  
@app.route('/signup', methods=['GET', 'POST'])  
def signup():  
    if not Config.SELF_SIGNUP_ENABLED:  
        flash('Self-signup is currently disabled.')  
        return redirect(url_for('login'))  
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip()

        # Input validation
        if not username or len(username) < 3 or len(username) > 50:
            flash('Username must be between 3 and 50 characters.')
            return redirect(url_for('signup'))
        if not password or len(password) < 4:
            flash('Password must be at least 4 characters.')
            return redirect(url_for('signup'))
        if not validate_email(email):
            flash('Please enter a valid email address.')
            return redirect(url_for('signup'))

        db_session = get_db_session()
        try:
            existing_user = db_session.query(User).filter_by(username=username).first()
            if existing_user:
                flash('Username already exists')
                return redirect(url_for('signup'))
            new_user = User(
                username=username,
                password=hash_password(password),
                email=email,
                pending=True
            )
            db_session.add(new_user)
            db_session.commit()
            flash('Account created successfully. Please wait for admin approval.')
            return redirect(url_for('login'))
        except Exception:
            db_session.rollback()
            flash('An error occurred creating your account. Please try again.')
            return redirect(url_for('signup'))
        finally:
            db_session.close()
    return render_template('signup.html')  
@app.route('/logout')  
def logout():  
    session.clear()  
    return redirect(url_for('login'))  
@app.route('/room/<int:room_id>')  
def room(room_id):  
    if 'user_id' not in session:  
        return redirect(url_for('login'))
    if not is_user_authorized_for_room(session['user_id'], room_id):
        if not session.get('is_admin'):
            flash('Access denied. You do not have permission to view this room.')
            return redirect(url_for('index'))
    db_session = get_db_session()  
    try:  
        page = request.args.get('page', 1, type=int)  
        per_page = Config.POSTS_PER_PAGE  
        start = (page - 1) * per_page  
        end = start + per_page  
        room_with_posts = db_session.query(Room).options(  
            joinedload(Room.posts).joinedload(Post.user),  
            joinedload(Room.posts).joinedload(Post.replies)  
        ).filter_by(id=room_id).first()  
        last_seen = g.previous_last_seen if hasattr(g, 'previous_last_seen') and g.previous_last_seen else datetime(2000, 1, 1, 0, 0, 0)  
        new_post_count = sum(1 for post in room_with_posts.posts if post.created_at > last_seen)  
        post_new_reply_counts = {}  
        for post in room_with_posts.posts:  
            post_new_reply_counts[post.id] = sum(  
                1 for reply in post.replies  
                if reply.created_at > last_seen  
            )  
        new_posts = [post for post in room_with_posts.posts if post.created_at > last_seen]  
        oldest_new_post = min(new_posts, key=lambda p: p.created_at) if new_posts else None  
        if new_posts and not request.args.get('scroll_to'):  
            return redirect(url_for('room', room_id=room_id, scroll_to=oldest_new_post.id))  
        total_posts = len(room_with_posts.posts)  
        paginated_posts = room_with_posts.posts[start:end]  
        total_pages = (total_posts + per_page - 1) // per_page if total_posts > 0 else 1  
        has_prev = page > 1  
        has_next = page < total_pages  
        prev_url = url_for('room', room_id=room_id, page=page - 1) if has_prev else None  
        next_url = url_for('room', room_id=room_id, page=page + 1) if has_next else None  
    finally:  
        db_session.close()  
    if not room_with_posts:  
        flash('Room not found')  
        return redirect(url_for('index'))  
    return render_template('room.html',  
        room=room_with_posts,  
        posts=paginated_posts,  
        new_post_count=new_post_count,  
        post_new_reply_counts=post_new_reply_counts,  
        pagination={  
            'page': page,  
            'total_pages': total_pages,  
            'has_prev': has_prev,  
            'has_next': has_next,  
            'prev_url': prev_url,  
            'next_url': next_url  
        })  
@app.route('/post/<int:post_id>')  
def post(post_id):  
    if 'user_id' not in session:  
        return redirect(url_for('login'))  
    db_session = get_db_session()  
    try:  
        page = request.args.get('page', 1, type=int)  
        per_page = Config.REPLIES_PER_PAGE  
        start = (page - 1) * per_page  
        end = start + per_page  
        post = db_session.query(Post).options(  
            joinedload(Post.user),  
            joinedload(Post.room),  
            joinedload(Post.replies).joinedload(Reply.user)  
        ).filter_by(id=post_id).first()  
        last_seen = g.previous_last_seen if hasattr(g, 'previous_last_seen') and g.previous_last_seen else datetime(2000, 1, 1, 0, 0, 0)  
        replies = db_session.query(Reply).filter_by(post_id=post_id).order_by(Reply.created_at).all()  
        total_replies = len(replies)  
        paginated_replies = replies[start:end]  
        total_pages = (total_replies + per_page - 1) // per_page if total_replies > 0 else 1  
        has_prev = page > 1  
        has_next = page < total_pages  
        prev_url = url_for('post', post_id=post_id, page=page - 1) if has_prev else None  
        next_url = url_for('post', post_id=post_id, page=page + 1) if has_next else None  
        new_replies = [reply for reply in replies if reply.created_at > last_seen]  
        oldest_new_reply = min(new_replies, key=lambda r: r.created_at) if new_replies else None  
        if new_replies and not request.args.get('scroll_to'):  
            return redirect(url_for('post', post_id=post_id, scroll_to=oldest_new_reply.id))  
    finally:  
        db_session.close()  
    if not post:  
        flash('Post not found')  
        return redirect(url_for('index'))  
    return render_template('post.html',  
        post=post,  
        replies=paginated_replies,  
        oldest_new_reply_id=oldest_new_reply.id if oldest_new_reply else None,  
        pagination={  
            'page': page,  
            'total_pages': total_pages,  
            'has_prev': has_prev,  
            'has_next': has_next,  
            'prev_url': prev_url,  
            'next_url': next_url  
        })  
@app.route('/create_post/<int:room_id>', methods=['GET', 'POST'])  
@login_required  
def create_post(room_id):  
    if request.method == 'POST':  
        title = request.form['title']  
        content = request.form['content']  
        image = request.files.get('image')  
        image_filename = None  
        if image and allowed_file(image.filename):  
            filename = secure_filename(image.filename)  
            ext = filename.rsplit('.', 1)[1].lower()  
            image_filename = str(uuid.uuid4()) + '.' + ext  
            image_path = os.path.join(Config.UPLOAD_FOLDER, image_filename)  
            image.save(image_path)  
            resize_image(image_path, Config.MAX_IMAGE_SIZE)  
        db_session = get_db_session()  
        try:  
            post = Post(  
                title=title,  
                content=content,  
                image_filename=image_filename,  
                created_by=db_session.query(User).filter_by(id=session['user_id']).first().id,  
                room_id=room_id  
            )  
            db_session.add(post)  
            db_session.commit()  
        finally:  
            db_session.close()  
        return redirect(url_for('room', room_id=room_id))  
    db_session = get_db_session()  
    try:  
        room = db_session.query(Room).filter_by(id=room_id).first()  
    finally:  
        db_session.close()  
    return render_template('create_post.html', room=room)  
@app.route('/create_reply/<int:post_id>', methods=['POST'])  
@login_required  
def create_reply(post_id):  
    if request.method == 'POST':  
        content = request.form['content']  
        image = request.files.get('reply_image')  
        image_filename = None  
        if image and allowed_file(image.filename):  
            filename = secure_filename(image.filename)  
            ext = filename.rsplit('.', 1)[1].lower()  
            image_filename = str(uuid.uuid4()) + '.' + ext  
            image_path = os.path.join(Config.UPLOAD_FOLDER, image_filename)  
            image.save(image_path)  
            resize_image(image_path, Config.MAX_IMAGE_SIZE)  
        db_session = get_db_session()  
        try:  
            reply = Reply(  
                content=content,  
                image_filename=image_filename,  
                created_by=db_session.query(User).filter_by(id=session['user_id']).first().id,  
                post_id=post_id  
            )  
            db_session.add(reply)  
            db_session.commit()  
        finally:  
            db_session.close()  
        return redirect(url_for('post', post_id=post_id))  
@app.route('/create_room', methods=['GET', 'POST'])  
@login_required  
def create_room():  
    if not session.get('is_admin'):  
        flash('You do not have permission to create rooms')  
        return redirect(url_for('index'))  
    if request.method == 'POST':  
        name = request.form['name']
        description = request.form['description']
        private = 'private' in request.form
        sort_order = request.form.get('sort_order', 0, type=int)
        db_session = get_db_session()  
        try:  
            room = Room(  
                name=name,  
                description=description,  
                private=private,  
                sort_order=sort_order,
                created_by=db_session.query(User).filter_by(id=session['user_id']).first().id  
            )  
            db_session.add(room)  
            db_session.commit()  
        finally:  
            db_session.close()  
        flash('Room created successfully')  
        return redirect(url_for('index'))  
    return render_template('create_room.html')  
# **Private messaging routes**
@app.route('/messages')
@login_required
def messages():
    db_session = get_db_session()
    try:
        message_rooms = get_private_message_rooms(session['user_id'])
        rooms_with_users = []
        last_seen = g.previous_last_seen if hasattr(g, 'previous_last_seen') and g.previous_last_seen else datetime.utcnow()
        for room in message_rooms:
            if room.user1_id == session['user_id']:
                other_user = db_session.query(User).filter_by(id=room.user2_id).first()
            else:
                other_user = db_session.query(User).filter_by(id=room.user1_id).first()
            
            # Count unread messages
            unread_count = sum(1 for msg in room.messages if msg.sender_id != session['user_id'] and not msg.read)
            
            rooms_with_users.append({
                'room': room,
                'other_user': other_user,
                'unread_count': unread_count
            })
    finally:
        db_session.close()
    return render_template('messages.html', rooms_with_users=rooms_with_users)
@app.route('/message/<int:room_id>')
@login_required
def message(room_id):
    db_session = get_db_session()
    try:
        room = db_session.query(PrivateMessageRoom).filter_by(id=room_id).first()
        if not room:
            flash('Room not found')
            return redirect(url_for('messages'))
        if session['user_id'] not in [room.user1_id, room.user2_id]:
            flash('Access denied')
            return redirect(url_for('messages'))
        # Get the other user in this room
        if room.user1_id == session['user_id']:
            other_user = db_session.query(User).filter_by(id=room.user2_id).first()
        else:
            other_user = db_session.query(User).filter_by(id=room.user1_id).first()
        # Expunge other_user to prevent expiration on session close
        if other_user:
            db_session.expunge(other_user)
        # Get messages, eager-loading the sender relationship
        messages = db_session.query(PrivateMessage).options(
            joinedload(PrivateMessage.sender)
        ).filter_by(room_id=room_id).order_by(PrivateMessage.created_at).all()
        # Mark messages as read
        for message in messages:
            if message.sender_id != session['user_id'] and not message.read:
                message.read = True
        db_session.commit()
        # CRITICAL: Fully materialize sender objects before expunging
        for msg in messages:
            # Force load sender.username (or any sender attribute) to prevent refresh
            _ = msg.sender.username
            db_session.expunge(msg)
    finally:
        db_session.close()
    return render_template('message.html', room=room, other_user=other_user, messages=messages)
# **New route for selecting a user to send a message to**
@app.route('/send_message', methods=['GET', 'POST'])
@login_required
def send_message_select_user():
    """Show a list of users to select for sending a message"""
    db_session = get_db_session()
    try:
        if request.method == 'POST':
            user_id = request.form.get('user_id')
            if user_id:
                return redirect(url_for('send_message', user_id=user_id))
        other_users = db_session.query(User).filter(User.id != session['user_id']).order_by(User.username).all()
    finally:
        db_session.close()
    return render_template('send_message_select.html', other_users=other_users)
@app.route('/send_message/<int:user_id>', methods=['GET', 'POST'])
@login_required
def send_message(user_id):
    if request.method == 'POST':
        content = request.form['content']
        image = request.files.get('image')
        image_filename = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            ext = filename.rsplit('.', 1)[1].lower()
            image_filename = str(uuid.uuid4()) + '.' + ext
            image_path = os.path.join(Config.UPLOAD_FOLDER, image_filename)
            image.save(image_path)
            resize_image(image_path, Config.MAX_IMAGE_SIZE)
        room = get_private_message_room(session['user_id'], user_id)
        db_session = get_db_session()
        try:
            message = PrivateMessage(
                content=content,
                image_filename=image_filename,
                sender_id=session['user_id'],
                room_id=room.id
            )
            db_session.add(message)
            db_session.commit()
        finally:
            db_session.close()
        return redirect(url_for('message', room_id=room.id))
    # GET request - show form
    db_session = get_db_session()
    try:
        other_user = db_session.query(User).filter_by(id=user_id).first()
        if not other_user:
            flash('User not found')
            return redirect(url_for('messages'))
        room = get_private_message_room(session['user_id'], user_id)
    finally:
        db_session.close()
    return render_template('send_message.html', other_user=other_user, room=room)
# **Admin routes**
@app.route('/admin')  
@admin_required  
def admin():  
    return render_template('admin.html')  
@app.route('/admin/users')  
@admin_required  
def admin_users():  
    db_session = get_db_session()  
    try:  
        users = db_session.query(User).order_by(User.username).all()  
    finally:  
        db_session.close()  
    return render_template('admin_users.html', users=users)  
@app.route('/admin/pending_users')  
@admin_required  
def admin_pending_users():  
    db_session = get_db_session()  
    try:  
        users = db_session.query(User).filter_by(pending=True).order_by(User.created_at).all()  
    finally:  
        db_session.close()  
    return render_template('admin_pending_users.html', users=users)  
@app.route('/admin/users/add', methods=['GET', 'POST'])  
@admin_required  
def admin_add_user():  
    if request.method == 'POST':  
        username = request.form['username']  
        password = request.form['password']  
        email = request.form.get('email', '')  
        is_admin = 'is_admin' in request.form  
        enabled = 'enabled' in request.form  # FIXED: was 'request_form'
        db_session = get_db_session()  
        try:  
            existing_user = db_session.query(User).filter_by(username=username).first()  
            if existing_user:  
                flash('Username already exists')  
                return redirect(url_for('admin_add_user'))  
            new_user = User(  
                username=username,  
                password=hash_password(password),  
                email=email,  
                is_admin=is_admin,  
                enabled=enabled  
            )  
            db_session.add(new_user)  
            db_session.commit()  
            flash('User created successfully')  
            return redirect(url_for('admin_users'))  
        finally:  
            db_session.close()  
    return render_template('admin_add_user.html')  
@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])  
@admin_required  
def admin_edit_user(user_id):  
    db_session = get_db_session()  
    try:  
        user = db_session.query(User).filter_by(id=user_id).first()  
        if not user:  
            flash('User not found')  
            return redirect(url_for('admin_users'))  
        if request.method == 'POST':  
            username = request.form['username']  
            password = request.form['password']  
            email = request.form.get('email', '')  
            is_admin = 'is_admin' in request.form  
            enabled = 'enabled' in request.form  # FIXED: was 'request_form'  
            existing_user = db_session.query(User).filter_by(username=username).first()  
            if existing_user and existing_user.id != user_id:  
                flash('Username already exists')  
                return redirect(url_for('admin_edit_user', user_id=user_id))  
            user.username = username  
            user.email = email  
            if password:  
                user.password = hash_password(password)  
            user.is_admin = is_admin  
            user.enabled = enabled  
            db_session.commit()  
            flash('User updated successfully')  
            return redirect(url_for('admin_users'))  
    finally:  
        db_session.close()  
    return render_template('admin_edit_user.html', user=user)  
@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])  
@admin_required  
def admin_delete_user(user_id):  
    db_session = get_db_session()  
    try:  
        user = db_session.query(User).filter_by(id=user_id).first()  
        if not user:  
            flash('User not found')  
            return redirect(url_for('admin_users'))  
        if user.username == 'admin' or user.id == session['user_id']:  
            flash('Cannot delete admin user or yourself')  
            return redirect(url_for('admin_users'))  
        db_session.delete(user)  
        db_session.commit()  
        flash('User deleted successfully')  
    finally:  
        db_session.close()  
    return redirect(url_for('admin_users'))  
@app.route('/admin/users/approve/<int:user_id>', methods=['POST'])  
@admin_required  
def admin_approve_user(user_id):  
    db_session = get_db_session()  
    try:  
        user = db_session.query(User).filter_by(id=user_id).first()  
        if not user:  
            flash('User not found')  
            return redirect(url_for('admin_pending_users'))  
        user.pending = False  
        user.enabled = True  
        db_session.commit()  
        flash('User approved successfully')  
    finally:  
        db_session.close()  
    return redirect(url_for('admin_pending_users'))  
@app.route('/admin/users/reject/<int:user_id>', methods=['POST'])  
@admin_required  
def admin_reject_user(user_id):  
    db_session = get_db_session()  
    try:  
        user = db_session.query(User).filter_by(id=user_id).first()  
        if not user:  
            flash('User not found')  
            return redirect(url_for('admin_pending_users'))  
        db_session.delete(user)  
        db_session.commit()  
        flash('User rejected and deleted successfully')  
    finally:  
        db_session.close()  
    return redirect(url_for('admin_pending_users'))  
# **New admin features**
@app.route('/admin/posts/delete/<int:post_id>', methods=['POST'])  
@admin_required  
def admin_delete_post(post_id):  
    db_session = get_db_session()  
    try:  
        post = db_session.query(Post).filter_by(id=post_id).first()  
        if not post:  
            flash('Post not found')  
            return redirect(url_for('index'))  
        replies = db_session.query(Reply).filter_by(post_id=post_id).all()  
        for reply in replies:  
            if reply.image_filename:  
                image_path = os.path.join(Config.UPLOAD_FOLDER, reply.image_filename)  
                if os.path.exists(image_path):  
                    os.remove(image_path)  
            db_session.delete(reply)  
        if post.image_filename:  
            image_path = os.path.join(Config.UPLOAD_FOLDER, post.image_filename)  
            if os.path.exists(image_path):  
                os.remove(image_path)  
        db_session.delete(post)  
        db_session.commit()  
        flash('Post and associated replies deleted successfully')  
    finally:  
        db_session.close()  
    return redirect(url_for('room', room_id=post.room_id))  
@app.route('/admin/replies/delete/<int:reply_id>', methods=['POST'])  
@admin_required  
def admin_delete_reply(reply_id):  
    db_session = get_db_session()  
    try:  
        reply = db_session.query(Reply).filter_by(id=reply_id).first()  
        if not reply:  
            flash('Reply not found')  
            return redirect(url_for('index'))  
        if reply.image_filename:  
            image_path = os.path.join(Config.UPLOAD_FOLDER, reply.image_filename)  
            if os.path.exists(image_path):  
                os.remove(image_path)  
        db_session.delete(reply)  
        db_session.commit()  
        flash('Reply deleted successfully')  
    finally:  
        db_session.close()  
    return redirect(url_for('post', post_id=reply.post_id))  
@app.route('/admin/rooms/delete/<int:room_id>', methods=['POST'])  
@admin_required  
def admin_delete_room(room_id):  
    db_session = get_db_session()  
    try:  
        room = db_session.query(Room).filter_by(id=room_id).first()  
        if not room:  
            flash('Room not found')  
            return redirect(url_for('index'))  
        posts = db_session.query(Post).filter_by(room_id=room_id).all()  
        for post in posts:  
            replies = db_session.query(Reply).filter_by(post_id=post.id).all()  
            for reply in replies:  
                if reply.image_filename:  
                    image_path = os.path.join(Config.UPLOAD_FOLDER, reply.image_filename)  
                    if os.path.exists(image_path):  
                        os.remove(image_path)  
                    db_session.delete(reply)  
            if post.image_filename:  
                image_path = os.path.join(Config.UPLOAD_FOLDER, post.image_filename)  
                if os.path.exists(image_path):  
                    os.remove(image_path)  
                db_session.delete(post)  
        db_session.delete(room)  
        db_session.commit()  
        flash('Room and all associated posts and replies deleted successfully')  
    finally:  
        db_session.close()  
    return redirect(url_for('index'))  
# **New admin route for editing rooms**
@app.route('/admin/rooms/edit/<int:room_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_room(room_id):
    db_session = get_db_session()
    try:
        room = db_session.query(Room).filter_by(id=room_id).first()
        if not room:
            flash('Room not found')
            return redirect(url_for('index'))
        if request.method == 'POST':
            room.name = request.form['name']
            room.description = request.form['description']
            room.private = 'private' in request.form
            room.sort_order = request.form.get('sort_order', 0, type=int)
            db_session.commit()
            flash('Room updated successfully')
            return redirect(url_for('index'))
        return render_template('admin_edit_room.html', room=room)
    finally:
        db_session.close()
# **New confirmation routes**
@app.route('/admin/posts/delete_confirm/<int:post_id>', methods=['GET'])  
@admin_required  
def admin_delete_post_confirm(post_id):  
    db_session = get_db_session()  
    try:  
        post = db_session.query(Post).filter_by(id=post_id).first()  
        if not post:  
            flash('Post not found')  
            return redirect(url_for('index'))  
        return render_template('admin_delete_post.html', post=post)  
    finally:  
        db_session.close()  
@app.route('/admin/replies/delete_confirm/<int:reply_id>', methods=['GET'])  
@admin_required  
def admin_delete_reply_confirm(reply_id):  
    db_session = get_db_session()  
    try:  
        reply = db_session.query(Reply).filter_by(id=reply_id).first()  
        if not reply:  
            flash('Reply not found')  
            return redirect(url_for('index'))  
        return render_template('admin_delete_reply.html', reply=reply)  
    finally:  
        db_session.close()  
@app.route('/admin/rooms/delete_confirm/<int:room_id>', methods=['GET'])  
@admin_required  
def admin_delete_room_confirm(room_id):  
    db_session = get_db_session()  
    try:  
        room = db_session.query(Room).filter_by(id=room_id).first()  
        if not room:  
            flash('Room not found')  
            return redirect(url_for('index'))  
        return render_template('admin_delete_room.html', room=room)  
    finally:  
        db_session.close()  
# **New admin routes for private room management**
@app.route('/admin/rooms/<int:room_id>/permissions', methods=['GET', 'POST'])
@admin_required
def admin_room_permissions(room_id):
    db_session = get_db_session()
    try:
        room = db_session.query(Room).filter_by(id=room_id).first()
        if not room:
            flash('Room not found')
            return redirect(url_for('index'))
        if request.method == 'POST':
            action = request.form.get('action')
            user_id = request.form.get('user_id')
            if action == 'add':
                user = db_session.query(User).filter_by(id=user_id).first()
                if user and user not in room.authorized_users:
                    room.authorized_users.append(user)
                    db_session.commit()
                    flash('User added to room permissions')
            elif action == 'remove':
                user = db_session.query(User).filter_by(id=user_id).first()
                if user and user in room.authorized_users:
                    room.authorized_users.remove(user)
                    db_session.commit()
                    flash('User removed from room permissions')
            return redirect(url_for('admin_room_permissions', room_id=room_id))
        all_users = db_session.query(User).order_by(User.username).all()
        authorized_user_ids = [user.id for user in room.authorized_users]
    finally:
        db_session.close()
    return render_template('admin_room_permissions.html', room=room, all_users=all_users, authorized_user_ids=authorized_user_ids)
# **User password change**
@app.route('/change_password', methods=['GET', 'POST'])  
@login_required  
def change_password():  
    if request.method == 'POST':  
        old_password = request.form['old_password']  
        new_password = request.form['new_password']  
        confirm_password = request.form['confirm_password']  
        db_session = get_db_session()  
        try:  
            user = db_session.query(User).filter_by(id=session['user_id']).first()  
            if not user:  
                flash('User not found')  
                return redirect(url_for('index'))  
            if not verify_password(old_password, user.password):  
                flash('Current password is incorrect')  
                return redirect(url_for('change_password'))  
            if new_password != confirm_password:  
                flash('New passwords do not match')  
                return redirect(url_for('change_password'))  
            user.password = hash_password(new_password)  
            db_session.commit()  
            flash('Password changed successfully')  
            return redirect(url_for('index'))  
        finally:  
            db_session.close()  
    return render_template('change_password.html')  
# **Serve uploaded images**
@app.route('/uploads/<path:filename>')  
def uploaded_file(filename):  
    return send_from_directory(Config.UPLOAD_FOLDER, filename)  
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=7000)