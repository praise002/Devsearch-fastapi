# DEVSEARCH API

A powerful FastAPI-based platform designed to connect developers worldwide, enabling collaboration, skill-sharing, and project discovery.

## 🚧 PROJECT STATUS: BUILD IN PROGRESS

## 📋 PROJECT ROADMAP

### ✅ Phase 1: Foundation & Setup (COMPLETED)
- ✅ Project structure setup
- ✅ FastAPI application initialization
- ✅ Database models design (User, Profile, Project, Skill, Review, Message, Tag, OTP)
- ✅ SQLModel + SQLAlchemy configuration
- ✅ Alembic migrations setup
- ✅ PostgreSQL database connection
- [x] Basic admin interface with Starlette Admin
- ✅ Static files and templates configuration

### 🔄 Phase 2: Authentication & User Management (IN PROGRESS)
- ✅ User registration endpoint
- ✅ Password hashing utilities
- ✅ User profile auto-creation
- ✅ Email verification system
- ✅ JWT authentication implementation
- ✅ Login/logout endpoints
- ✅ Password reset functionality
- [ ] User profile CRUD operations
- [ ] User role management

### 📅 Phase 3: Core Features (PLANNED)
#### Profile Management
- [ ] Profile picture upload (Cloudinary integration)
- [ ] Skills management (add/remove skills)
- [ ] Social links management
- [ ] Profile visibility settings

#### Project Management
- [ ] Project CRUD operations
- [ ] Project image upload
- [ ] Project search and filtering
- [ ] Project categorization with tags
- [ ] Project slug generation and SEO

#### Review & Rating System
- [ ] Project review endpoints
- [ ] Rating calculation logic
- [ ] Review moderation
- [ ] Vote ratio calculations

### 📅 Phase 4: Communication Features (PLANNED)
- [ ] Inbox system between users
- [ ] Inbox read/unread status

### 📅 Phase 5: Advanced Features (PLANNED)
#### Search & Discovery
- [ ] Advanced project search
- [ ] User/developer search
- [ ] Skill-based recommendations
- [ ] Project recommendation engine

#### API Enhancements
- [ ] Rate limiting implementation
- [ ] API versioning
- [ ] Comprehensive API documentation
- [ ] Error handling improvements
- [ ] Logging and monitoring

### 📅 Phase 6: Testing & Security (PLANNED)
- [ ] Unit tests for all endpoints
- [ ] Integration tests
- [ ] Security audit
- [ ] Input validation enhancements
- [ ] CORS configuration
- [ ] API security headers

### 📅 Phase 7: Deployment & DevOps (PLANNED)
- [ ] Docker containerization
- [ ] CI/CD pipeline setup
- [ ] Production database configuration
- [ ] Environment-specific configurations
- [ ] Health check endpoints
- [ ] Performance monitoring

### 📅 Phase 8: Documentation & Finalization (PLANNED)
- [ ] Complete API documentation
- [ ] Installation guide
- [ ] Deployment guide
- [ ] Contributing guidelines
- [ ] Code cleanup and optimization

## 🛠 Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLModel + SQLAlchemy
- **Migrations**: Alembic
- **Authentication**: JWT (planned)
- **File Storage**: Cloudinary (planned)
- **Admin Interface**: Starlette Admin
- **Testing**: Pytest (planned)
- **Deployment**: Docker (planned)

## 🏗 Current Architecture

```
src/
├── auth/           # Authentication & user management
├── profiles/       # User profiles management
├── projects/       # Project management
├── messaging/      # Communication features
├── common/         # Shared utilities
├── db/            # Database models and configuration
└── tests/         # Test suites
```

## 🚀 Getting Started

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd devsearch-fastapi
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv env
   env\Scripts\activate  # Windows
   # or
   source env/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Create .env file with:
   DATABASE_URL=postgresql://username:password@localhost/dbname
   DOMAIN=localhost:8000
   EMAIL_OTP_EXPIRE_MINUTES=5
   ```

5. **Run migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start the application**
   ```bash
   uvicorn src:app --reload
   ```

7. **Access the application**
   - API Documentation: http://localhost:8000/api/v1/docs
   - Admin Interface: http://localhost:8000/admin

8. **To generate secret key**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

## 📝 API Endpoints

### Authentication (Implemented)
- `POST /api/v1/auth/register` - User registration

### Authentication (Implemented)
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/verification/verify` - Email verification
- `POST /api/v1/auth/verification` - Resend verification email
- `POST /api/v1/auth/token` - User login
- `POST /api/v1/auth/token/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current authenticated user profile
- `POST /api/v1/auth/logout` - User logout (single device)
- `POST /api/v1/auth/logout/all` - User logout (all devices)
- `POST /api/v1/auth/passwords/reset` - Password reset request
- `POST /api/v1/auth/passwords/reset/verify` - Verify OTP for password reset
- `POST /api/v1/auth/passwords/reset/complete` - Complete password reset
- `POST /api/v1/auth/passwords/change` - Change password (authenticated users)
- `GET /api/v1/auth/google` - Initiate Google OAuth login
- `GET /api/v1/auth/google/callback` - Handle Google OAuth callback

### Profiles (Planned)
- `GET /api/v1/profiles/` - List profiles
- `PATCH /api/v1/profiles/image/` - Update user image
- `DELETE /api/v1/profiles/image/` - Delete user image
- `GET /api/v1/profiles/{username}` - Get user profile
- `PATCH /api/v1/profiles/{username}` - Update user profile
- `POST /api/v1/profiles/{username}/skills` - Add skill
- `PATCH /api/v1/profiles/{username}/skills` - Update a specific skill e.g adding description
- `GET /api/v1/profiles/skills` - Retrieve a list of skills
- `DELETE /api/v1/profiles/{username}/skills/{skill_id}` - Remove skill

### Projects (Planned)
- `GET /api/v1/projects/` - List projects
- `POST /api/v1/projects/` - Create project
- `GET /api/v1/projects/{id}` - Get project
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project
- `POST /api/v1/projects/{id}/reviews` - Add review

### Messages (Planned)
- `GET /api/v1/messages/` - List messages
- `POST /api/v1/messages/` - Send message
- `GET /api/v1/messages/{id}` - Get message
- `PUT /api/v1/messages/{id}` - Mark as read


## Resources
- [How to send an email in fastapi](https://medium.com/nerd-for-tech/how-to-send-email-using-python-fastapi-947921059f0c)
- [Fastapi mail](https://sabuhish.github.io/fastapi-mail/example/#using-jinja2-html-templates)
- [Resolved issue with 403 for unauthenticated users](https://github.com/fastapi/fastapi/issues/2026)
- [Fastapi JWT Auth](https://indominusbyte.github.io/fastapi-jwt-auth/usage/revoking/)
- [Implementing Google OAuth2 in Fastapi](https://dev.to/ayoub3bidi/quick-tutorial-implementing-google-oauth2-in-fastapi-callback-method-ba4)

## 🤝 Contributing

This project is currently in active development. Contributions, issues, and feature requests are welcome!

## 📄 License

This project is licensed under the MIT License.