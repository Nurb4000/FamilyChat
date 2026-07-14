# Family Chat

A private, family-oriented chat and forum application built with Flask. Perfect for keeping families connected with organized discussions, event planning, and private messaging. Without the overhead, secutity risks, and flood of garbage you get with most social media these days.

## Features

### Core Functionality
- **Organized Rooms**: Create and manage discussion rooms for different topics. Some defaults to get you starte
  - Family Events
  - General Discussion
  - News
  - Music
  - The Zoo (pets and animals)
  - Technology

- **Posts & Replies**: Threaded discussions with rich content support
  - Text posts with titles
  - Image attachments (PNG, JPG, JPEG, GIF)
  - Automatic image resizing for optimal display
  - Pagination for large discussion threads

- **Private Messaging**: Direct communication between family members
  - One-on-one private message rooms
  - Message history with timestamps
  - Image support in messages

- **User Management**
  - Self-signup with admin approval (optional)
  - User profiles with email addresses
  - Account enable/disable functionality
  - Password change functionality

- **Admin Panel**: Comprehensive administrative controls
  - User management (add, edit, delete, approve/reject)
  - Room creation and management
  - Post and reply deletion
  - Private room permission controls
  - User authorization for restricted rooms

### Security Features
- Secure password hashing using Werkzeug's PBKDF2
- CSRF protection on all forms
- Input validation and sanitization
- Session-based authentication
- Email format validation
- File upload security (extension validation, directory traversal prevention)

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Clone or download the project**
   ```bash
   cd FamilyChat
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the application**
   
   The application requires a secret key for session management. You can either:
   
   **Option A: Set environment variable (recommended for production)**
   ```bash
   export SECRET_KEY="your-secure-random-key-here"
   # or on Windows:
   set SECRET_KEY=your-secure-random-key-here
   ```
   
   **Option B: Use auto-generated key (development only)**
   The app will generate a new random key each run if no SECRET_KEY is provided.

5. **Initialize the database**
   ```bash
   python database.py
   ```
   This creates:
   - SQLite database (`family_chat.db`)
   - Default admin account (username: `admin`, password: `admin`)
   - Default discussion rooms

## Configuration

Edit `config.py` to customize:

```python
# Database path
DATABASE_URL = 'sqlite:///family_chat.db'

# Upload settings
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_IMAGE_SIZE = (800, 600)  # Maximum dimensions for resized images

# Pagination
POSTS_PER_PAGE = 10
REPLIES_PER_PAGE = 15

# Self-signup (set to False to require admin-created accounts)
SELF_SIGNUP_ENABLED = True
```

## Usage

### Starting the Server

```bash
python app.py
```

The application will start on `http://0.0.0.0:7000`

### Default Login

- **Username**: `admin`
- **Password**: `admin`

**Important**: Change the admin password immediately after first login!

### User Flow

1. **Login** with your credentials
2. **Browse rooms** from the main dashboard
3. **Create posts** in any room (click "Create New Post")
4. **Reply to posts** at the bottom of each post
5. **Send private messages** via the private message system
6. **Upload images** with posts, replies, and messages

### Admin Features

Access the admin panel by logging in as an administrator:

- **Manage Users**: View, edit, delete, approve/reject users
- **Create Rooms**: Add new discussion rooms
- **Edit Rooms**: Modify room names, descriptions, and permissions
- **Delete Content**: Remove posts or replies (deletes all associated replies)
- **Room Permissions**: Control access to private rooms

## Project Structure

```
FamilyChat/
├── app.py                 # Main application file
├── config.py              # Configuration settings
├── database.py            # Database initialization and setup
├── models.py              # SQLAlchemy database models
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
├── README.md             # This file
├── static/
│   ├── style.css         # Application styles
│   ├── logo.jpg          # Site logo
│   ├── logo2.jpg         # Alternative logo
│   └── uploads/          # User-uploaded images
└── templates/            # HTML templates
    ├── base.html         # Base template
    ├── login.html        # Login page
    ├── signup.html       # Registration page
    ├── index.html        # Main dashboard
    ├── room.html         # Room view
    ├── post.html         # Post detail view
    ├── messages.html     # Private messages list
    ├── message.html      # Individual message room
    ├── admin.html        # Admin panel
    └── ...               # Other templates
```

## Security Notes

### For Production Deployment

1. **Set a strong SECRET_KEY**: Generate a cryptographically secure random string
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Disable self-signup** if you want to control account creation:
   ```python
   SELF_SIGNUP_ENABLED = False
   ```

3. **Use a production web server**: This app uses Flask's development server. For production, use:
   - Gunicorn
   - uWSGI
   - Waitress (Windows)

4. **Enable HTTPS**: Always use HTTPS in production to encrypt data in transit

5. **Regular backups**: Back up your `family_chat.db` file regularly

### Current Security Measures

- ✅ CSRF protection on all forms
- ✅ Secure password hashing (PBKDF2)
- ✅ Input validation and sanitization
- ✅ File upload security checks
- ✅ Session-based authentication
- ✅ Email format validation

## Troubleshooting

### Database Issues
If you encounter database errors, try:
```bash
# Delete the old database and recreate
rm family_chat.db
python database.py
```

### Upload Problems
- Ensure the `static/uploads/` directory exists and is writable
- Check file size limits in your web server configuration
- Verify image formats are supported (PNG, JPG, JPEG, GIF)

### Login Issues
- Default credentials: `admin` / `admin`
- If accounts are disabled, check admin panel
- Self-signup accounts require admin approval by default

## Customization

### Changing Default Rooms
Edit the `default_rooms` list in `database.py` to customize initial rooms.

### Modifying Appearance
Edit `static/style.css` to change colors, fonts, and layout.

### Adding Features
The modular structure makes it easy to add:
- New room types
- Additional user roles
- Email notifications
- Rich text editing
- File sharing beyond images

## License

This is a family project. Feel free to use and modify as needed for your family's communication needs.


---

**Enjoy keeping your family connected!** 🏠💬


Some screenshots

<img width="1125" height="649" alt="image" src="https://github.com/user-attachments/assets/98bc0403-0cd4-494e-a863-058070f820e5" />
<img width="1166" height="663" alt="image" src="https://github.com/user-attachments/assets/494752ec-cc4b-435c-a0e7-73a049d535a1" />
<img width="1224" height="610" alt="image" src="https://github.com/user-attachments/assets/aba01a6a-dfec-42e6-9443-0d6e9ab423d4" />




