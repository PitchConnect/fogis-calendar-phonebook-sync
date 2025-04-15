# Implement User Authentication and Authorization

## Description

Currently, the application doesn't have user authentication for API endpoints, which could be a security concern for a production deployment. This issue outlines the implementation of a comprehensive authentication and authorization system.

## Technical Specifications

### 1. Authentication System

**Recommended Approach:**
- **Primary: OAuth2 with Google** - Leverage existing Google integration
- **Alternative: JWT-based authentication** - For non-Google authentication scenarios

**Authentication Flow:**
1. User authenticates with Google OAuth2
2. Application receives access token and user information
3. Application creates/updates local user record
4. Application issues a session token (JWT) for subsequent requests
5. Client includes JWT in Authorization header for all API requests

**JWT Structure:**
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user@example.com",
    "name": "User Name",
    "iat": 1516239022,
    "exp": 1516242622,
    "roles": ["user", "admin"],
    "permissions": ["read:calendar", "write:calendar"]
  },
  "signature": "..."
}
```

**Token Management:**
- Token expiration: 1 hour for access tokens
- Refresh token expiration: 30 days
- Token revocation endpoint for logout
- Token refresh endpoint for extending sessions

### 2. Authorization System

**Role-Based Access Control (RBAC):**
- **User Roles:**
  - `guest`: Can view public information only
  - `user`: Can view their own data and perform basic operations
  - `admin`: Can manage all data and users

**Permission-Based Access Control:**
- Fine-grained permissions:
  - `read:calendar`: Can view calendar events
  - `write:calendar`: Can create/update calendar events
  - `read:contacts`: Can view contacts
  - `write:contacts`: Can create/update contacts
  - `admin:users`: Can manage users
  - `admin:system`: Can configure system settings

**Access Control Implementation:**
- Decorator-based approach for route protection
- Middleware for JWT validation and role/permission extraction
- Configuration-driven permission mapping

### 3. Security Considerations

**OWASP Security Best Practices:**
- Protection against CSRF attacks
- XSS prevention
- Rate limiting for authentication endpoints
- Secure cookie handling
- HTTPS enforcement

**Sensitive Data Handling:**
- Secure storage of tokens
- No sensitive data in logs
- Proper error handling to prevent information leakage

### 4. User Management

**User Data Model:**
```python
class User:
    email: str  # Primary identifier
    name: str
    picture: str  # Profile picture URL
    roles: List[str]
    permissions: List[str]
    created_at: datetime
    last_login: datetime
    is_active: bool
```

**User Operations:**
- User registration (automatic with OAuth)
- User profile management
- Role and permission assignment (admin only)
- Account deactivation/reactivation

## Implementation Steps

### 1. Set Up Authentication Dependencies

1. Install required packages:
   ```bash
   pip install flask-jwt-extended authlib requests
   ```

2. Configure OAuth with Google:
   ```python
   # In app.py or auth.py
   from authlib.integrations.flask_client import OAuth

   oauth = OAuth(app)
   google = oauth.register(
       name='google',
       client_id=os.getenv('GOOGLE_CLIENT_ID'),
       client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
       access_token_url='https://accounts.google.com/o/oauth2/token',
       access_token_params=None,
       authorize_url='https://accounts.google.com/o/oauth2/auth',
       authorize_params=None,
       api_base_url='https://www.googleapis.com/oauth2/v1/',
       client_kwargs={'scope': 'openid email profile'},
   )
   ```

3. Configure JWT:
   ```python
   # In app.py or auth.py
   from flask_jwt_extended import JWTManager

   app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
   app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
   app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
   jwt = JWTManager(app)
   ```

### 2. Implement Authentication Endpoints

1. Create login endpoint:
   ```python
   @app.route('/login')
   def login():
       redirect_uri = url_for('authorize', _external=True)
       return google.authorize_redirect(redirect_uri)

   @app.route('/authorize')
   def authorize():
       token = google.authorize_access_token()
       user_info = google.get('userinfo').json()

       # Create or update user in database
       user = upsert_user(user_info)

       # Create JWT tokens
       access_token = create_access_token(
           identity=user['email'],
           additional_claims={
               'name': user['name'],
               'roles': user['roles'],
               'permissions': user['permissions']
           }
       )
       refresh_token = create_refresh_token(identity=user['email'])

       # Set cookies or return tokens
       response = jsonify(login='success')
       set_access_cookies(response, access_token)
       set_refresh_cookies(response, refresh_token)
       return response
   ```

2. Create logout endpoint:
   ```python
   @app.route('/logout', methods=['POST'])
   @jwt_required()
   def logout():
       response = jsonify(logout='success')
       unset_jwt_cookies(response)
       return response
   ```

3. Create token refresh endpoint:
   ```python
   @app.route('/refresh', methods=['POST'])
   @jwt_refresh_token_required
   def refresh():
       current_user = get_jwt_identity()
       user = get_user_by_email(current_user)

       access_token = create_access_token(
           identity=current_user,
           additional_claims={
               'name': user['name'],
               'roles': user['roles'],
               'permissions': user['permissions']
           }
       )

       response = jsonify(refresh='success')
       set_access_cookies(response, access_token)
       return response
   ```

### 3. Implement Authorization Middleware

1. Create a decorator for role-based access control:
   ```python
   def role_required(roles):
       def wrapper(fn):
           @wraps(fn)
           def decorator(*args, **kwargs):
               verify_jwt_in_request()
               claims = get_jwt_claims()

               if not set(roles).intersection(set(claims.get('roles', []))):
                   return jsonify(msg='Insufficient permissions'), 403

               return fn(*args, **kwargs)
           return decorator
       return wrapper
   ```

2. Create a decorator for permission-based access control:
   ```python
   def permission_required(permissions):
       def wrapper(fn):
           @wraps(fn)
           def decorator(*args, **kwargs):
               verify_jwt_in_request()
               claims = get_jwt_claims()

               if not set(permissions).intersection(set(claims.get('permissions', []))):
                   return jsonify(msg='Insufficient permissions'), 403

               return fn(*args, **kwargs)
           return decorator
       return wrapper
   ```

3. Apply decorators to routes:
   ```python
   @app.route('/api/calendar', methods=['GET'])
   @permission_required(['read:calendar'])
   def get_calendar_events():
       # Implementation
       pass

   @app.route('/api/calendar', methods=['POST'])
   @permission_required(['write:calendar'])
   def create_calendar_event():
       # Implementation
       pass

   @app.route('/api/users', methods=['GET'])
   @role_required(['admin'])
   def get_users():
       # Implementation
       pass
   ```

### 4. Implement User Management

1. Create user data model:
   ```python
   # In models.py or user.py
   class User:
       def __init__(self, email, name, picture=None):
           self.email = email
           self.name = name
           self.picture = picture
           self.roles = ['user']  # Default role
           self.permissions = ['read:calendar', 'read:contacts']  # Default permissions
           self.created_at = datetime.utcnow()
           self.last_login = datetime.utcnow()
           self.is_active = True

       def to_dict(self):
           return {
               'email': self.email,
               'name': self.name,
               'picture': self.picture,
               'roles': self.roles,
               'permissions': self.permissions,
               'created_at': self.created_at.isoformat(),
               'last_login': self.last_login.isoformat(),
               'is_active': self.is_active
           }
   ```

2. Create user repository:
   ```python
   # In repositories.py or user_repository.py
   class UserRepository:
       def __init__(self, db_path='data/users.json'):
           self.db_path = db_path
           os.makedirs(os.path.dirname(db_path), exist_ok=True)
           if not os.path.exists(db_path):
               with open(db_path, 'w') as f:
                   json.dump({}, f)

       def get_by_email(self, email):
           with open(self.db_path, 'r') as f:
               users = json.load(f)
               return users.get(email)

       def save(self, user):
           with open(self.db_path, 'r') as f:
               users = json.load(f)

           users[user.email] = user.to_dict()

           with open(self.db_path, 'w') as f:
               json.dump(users, f)

       def upsert_user(self, user_info):
           email = user_info['email']
           user_dict = self.get_by_email(email)

           if user_dict:
               # Update existing user
               user = User(
                   email=email,
                   name=user_info.get('name', user_dict['name']),
                   picture=user_info.get('picture', user_dict['picture'])
               )
               user.roles = user_dict['roles']
               user.permissions = user_dict['permissions']
               user.created_at = datetime.fromisoformat(user_dict['created_at'])
               user.last_login = datetime.utcnow()
               user.is_active = user_dict['is_active']
           else:
               # Create new user
               user = User(
                   email=email,
                   name=user_info.get('name', ''),
                   picture=user_info.get('picture', '')
               )

           self.save(user)
           return user.to_dict()
   ```

3. Create user management endpoints:
   ```python
   @app.route('/api/users', methods=['GET'])
   @role_required(['admin'])
   def get_users():
       user_repo = UserRepository()
       with open(user_repo.db_path, 'r') as f:
           users = json.load(f)
       return jsonify(list(users.values()))

   @app.route('/api/users/<email>', methods=['GET'])
   @jwt_required()
   def get_user(email):
       current_user = get_jwt_identity()
       claims = get_jwt_claims()

       # Users can view their own profile, admins can view any profile
       if current_user != email and 'admin' not in claims.get('roles', []):
           return jsonify(msg='Insufficient permissions'), 403

       user_repo = UserRepository()
       user = user_repo.get_by_email(email)

       if not user:
           return jsonify(msg='User not found'), 404

       return jsonify(user)

   @app.route('/api/users/<email>/roles', methods=['PUT'])
   @role_required(['admin'])
   def update_user_roles(email):
       data = request.get_json()
       roles = data.get('roles', [])

       user_repo = UserRepository()
       user_dict = user_repo.get_by_email(email)

       if not user_dict:
           return jsonify(msg='User not found'), 404

       user = User(
           email=user_dict['email'],
           name=user_dict['name'],
           picture=user_dict['picture']
       )
       user.roles = roles
       user.permissions = user_dict['permissions']
       user.created_at = datetime.fromisoformat(user_dict['created_at'])
       user.last_login = datetime.fromisoformat(user_dict['last_login'])
       user.is_active = user_dict['is_active']

       user_repo.save(user)

       return jsonify(user.to_dict())
   ```

### 5. Implement Security Measures

1. Add CSRF protection:
   ```python
   from flask_wtf.csrf import CSRFProtect

   csrf = CSRFProtect(app)
   ```

2. Add rate limiting:
   ```python
   from flask_limiter import Limiter
   from flask_limiter.util import get_remote_address

   limiter = Limiter(
       app,
       key_func=get_remote_address,
       default_limits=["200 per day", "50 per hour"]
   )

   # Apply stricter limits to authentication endpoints
   @app.route('/login')
   @limiter.limit("10 per minute")
   def login():
       # Implementation
       pass
   ```

3. Add secure headers:
   ```python
   from flask_talisman import Talisman

   talisman = Talisman(
       app,
       content_security_policy={
           'default-src': '\'self\'',
           'img-src': '*',
           'script-src': ['\'self\'', 'https://apis.google.com'],
           'style-src': ['\'self\'', '\'unsafe-inline\''],
       },
       force_https=True  # Redirect HTTP to HTTPS
   )
   ```

## Testing the Implementation

1. **Unit Tests:**
   - Test JWT token generation and validation
   - Test role and permission checks
   - Test user repository operations

2. **Integration Tests:**
   - Test authentication flow with Google OAuth
   - Test protected endpoints with various roles
   - Test token refresh and logout

3. **Security Tests:**
   - Test for common vulnerabilities (CSRF, XSS)
   - Test rate limiting
   - Test token expiration and revocation

## Documentation

1. Update API documentation with:
   - Authentication requirements
   - Available endpoints
   - Required permissions for each endpoint

2. Create user documentation explaining:
   - How to log in
   - How to manage user roles (for admins)
   - Security best practices

## Acceptance Criteria

- [ ] Users can authenticate using Google OAuth
- [ ] API endpoints are protected based on roles and permissions
- [ ] JWT tokens are properly generated, validated, and refreshed
- [ ] User management functionality is implemented
- [ ] Security measures are in place (CSRF protection, rate limiting, etc.)
- [ ] Comprehensive tests verify the authentication and authorization system
- [ ] Documentation is updated with authentication and authorization details

## Resources

- [Flask-JWT-Extended Documentation](https://flask-jwt-extended.readthedocs.io/)
- [Authlib Documentation](https://docs.authlib.org/)
- [Google OAuth2 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [JWT.io](https://jwt.io/) - For debugging JWT tokens
