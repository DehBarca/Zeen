# Zeen - Streaming Platform

**See it. Feel it. Keep it Zeen**

A modern streaming platform prototype built with **React** and **FastAPI**, demonstrating the integration of multiple NoSQL databases for user management, content catalog, recommendations, and real-time event tracking.

## 📋 Project Overview

Zeen is a full-featured streaming platform that showcases how different NoSQL databases can work together in a single system:

- **MongoDB**: User profiles, show metadata, and episode details
- **Cassandra**: High-throughput watch history and real-time analytics
- **Dgraph**: Graph-based recommendations and relationships
- **ChromaDB**: Semantic search for natural language queries

### Core Features

✅ **User Management**: Registration, login, profile management with JWT auth  
✅ **Content Catalog**: Browse movies, series, and episodes with filters  
✅ **Database Integration**: MongoDB for documents, Cassandra for events, Dgraph for relationships  
✅ **Vector Search**: ChromaDB integration for semantic search capabilities  
✅ **REST API**: Comprehensive OpenAPI documentation with Swagger UI  
✅ **Async Architecture**: High-performance async/await throughout backend  
✅ **Development Environment**: Docker Compose with all services preconfigured  
✅ **Type Safety**: Full TypeScript frontend and Pydantic-validated backend  

### Planned Features 🗺️

🔜 Watch history tracking (Cassandra)  
🔜 Personalized recommendations (Dgraph graph relationships)  
🔜 Semantic search across content (ChromaDB embeddings)  
🔜 Real-time analytics dashboard  
🔜 Admin panel for content management  

## � Quick Start

Get the app running in 3 commands:

```bash
git clone <repository-url> && cd Zeen
cp .env.example .env
docker-compose up --build
```

Then open:
- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/api/v1/docs

That's it! All 7 services (MongoDB, Cassandra, Dgraph Zero, Dgraph Alpha, ChromaDB, Backend, Frontend) will start automatically.

---

## �🏗️ Architecture

### Tech Stack

**Backend:**
- FastAPI 0.115.0 (Python web framework)
- Motor 3.6.0 (async MongoDB driver)
- Cassandra Driver 3.29.3
- Pydgraph (Dgraph client)
- ChromaDB 0.6.3 (Vector database)
- Python 3.12

**Frontend:**
- React 19.0.0 with TypeScript 5.4.2
- Vite 5.1.0 (build tool)
- Zustand 4.5.0 (state management)
- Axios (HTTP client)
- Node.js 20-alpine

**Infrastructure:**
- Docker & Docker Compose
- MongoDB 8.0
- Apache Cassandra 5.0
- Dgraph 25.3.2 (Zero + Alpha)
- ChromaDB latest

## 🚀 Getting Started

### Prerequisites

- **Docker Desktop** installed and running (includes Docker CLI and Docker Compose)
- **Git** for cloning the repository

*Optional for local development:*
- **Node.js** 20+
- **Python** 3.12+

### Installation & Running

#### Using Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone <repository-url>
cd Zeen

# 2. Create environment file
cp .env.example .env

# 3. Start all services
docker-compose up --build

# 4. Wait for all services to be healthy
# Watch the output until you see health messages
```

Once running, access:
- **Web App**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs
- **API ReDoc**: http://localhost:8000/redoc

#### Verifying Services

```bash
# Check all containers are healthy
docker-compose ps

# View logs for a specific service
docker-compose logs backend
docker-compose logs frontend
docker-compose logs mongodb
```

#### Stopping Services

```bash
# Stop all services (keeps data)
docker-compose stop

# Stop and remove containers and volumes (clean slate)
docker-compose down -v
```

### Local Development (Without Docker)

**Note**: Docker Compose approach is recommended. For local development:

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start databases separately (requires Docker)
docker-compose up mongodb cassandra dgraph-zero dgraph chromadb

# Run FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev

# Access at http://localhost:5173
```

**Important**: Local development still requires Docker for databases. For a complete isolated experience, use `docker-compose up --build`.

## ⚙️ Configuration

### Environment Variables

The `.env` file controls all configuration. Key variables:

**Database Connections:**
- `MONGODB_USER` / `MONGODB_PASSWORD` - MongoDB credentials
- `CASSANDRA_HOSTS` / `CASSANDRA_PORT` - Cassandra connection
- `DGRAPH_URL` - Dgraph server URL
- `CHROMADB_URL` - ChromaDB server URL

**Security:**
- `SECRET_KEY` - JWT signing key (change in production!)
- `ALGORITHM` - JWT algorithm (HS256 recommended)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token validity period (default: 30)

**API:**
- `API_V1_STR` - API version prefix (default: /api/v1)
- `PROJECT_NAME` - Application name

**Frontend:**
- `VITE_API_URL` - Backend API URL for frontend (default: http://localhost:8000)

### Default Credentials (Local Development)

- **MongoDB**: `admin` / `password123`
- **API JWT expires**: 30 minutes

⚠️ **Important**: Change `SECRET_KEY` and database credentials in production!

## 📚 API Endpoints

### Authentication

- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get access token
- `GET /api/v1/auth/me` - Get current user info

### Users

- `GET /api/v1/users/{user_id}` - Get user profile
- `PUT /api/v1/users/{user_id}` - Update user profile

### Content

- `GET /api/v1/content/` - List content (with filters)
- `GET /api/v1/content/{content_id}` - Get content details
- `POST /api/v1/content/` - Create content (admin)
- `PUT /api/v1/content/{content_id}` - Update content (admin)
- `DELETE /api/v1/content/{content_id}` - Delete content (admin)

## 🔐 Authentication

The platform uses **JWT (JSON Web Tokens)** for authentication:

1. User registers or logs in
2. Server returns an access token
3. Client includes token in `Authorization: Bearer <token>` header
4. Token expires after 30 minutes (configurable)

## 📊 Database Schema

### MongoDB Collections

**users**
```javascript
{
  _id: ObjectId,
  email: String,
  username: String,
  hashed_password: String,
  first_name: String,
  last_name: String,
  is_active: Boolean,
  created_at: DateTime,
  updated_at: DateTime
}
```

**content**
```javascript
{
  _id: ObjectId,
  title: String,
  description: String,
  content_type: "movie" | "series" | "episode",
  duration_minutes: Number,
  release_date: DateTime,
  poster_url: String,
  banner_url: String,
  rating: Number,
  genres: [String],
  cast: [String],
  directors: [String],
  created_at: DateTime,
  updated_at: DateTime
}
```

### Cassandra Tables

**watch_history**
- For storing time-series data of user watch events
- Partitioned by user_id for efficient queries
- Supports high-throughput writes

### Dgraph Predicates

- User → watches → Content (relationships)
- User → enjoys_genre → Genre
- Content → features_actor → Actor
- Content → made_by → Director

### ChromaDB Collections

- Vector embeddings of content descriptions
- Enables semantic search across the catalog

## 🔄 Project Structure

```
Zeen/
├── docker-compose.yml           # Service orchestration
├── .env.example                 # Environment template
├── README.md                    # This file
├── backend/
│   ├── app/
│   │   ├── core/               # Config, security, database
│   │   ├── models/             # Data models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── api/                # API routes
│   │   └── main.py             # FastAPI app
│   ├── requirements.txt
│   └── Dockerfile
└── frontend/
    ├── src/
    │   ├── components/         # Reusable React components
    │   ├── pages/             # Page components
    │   ├── services/          # API service layer
    │   ├── store/             # Zustand stores
    │   ├── hooks/             # Custom React hooks
    │   └── App.tsx            # Main app component
    ├── package.json
    ├── vite.config.ts
    └── Dockerfile
```

## 🧪 Testing

```bash
# Run backend tests
cd backend
pytest

# Run frontend tests
cd frontend
npm test
```

## 📖 Development Guide

### Adding a New API Endpoint

1. Create a Pydantic schema in `app/schemas/`
2. Create endpoint file in `app/api/v1/endpoints/`
3. Include router in `app/api/v1/api.py`
4. Test with `/api/v1/docs`

### Creating database models

Models are Python classes that represent database documents.

```python
# In app/models/
class MyModel:
    def __init__(self, field1, field2):
        self.field1 = field1
        self.field2 = field2
    
    def to_dict(self):
        return {"field1": self.field1, "field2": self.field2}
```

## 🐛 Troubleshooting

### Services won't start

Check all required ports (27017, 9042, 8080, 8000, 5173) are available:

```bash
# Check container status
docker-compose ps

# View detailed logs
docker-compose logs -f backend
```

### MongoDB connection timeout

Ensure MongoDB has time to initialize (can take 10-15 seconds):

```bash
docker-compose logs mongodb
# Should see "Waiting for connections" message
```

### Frontend shows 404 error

1. Verify frontend container is running: `docker ps | grep frontend`
2. Check frontend logs: `docker-compose logs frontend`
3. Clear browser cache and reload: `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)

### Backend API unreachable

1. Verify backend is healthy: `docker-compose ps` (should show "healthy")
2. Test endpoint directly: `curl http://localhost:8000/health`
3. Check logs: `docker-compose logs backend`

### Port conflicts

If ports are already in use:

```bash
# Option 1: Stop all Docker containers
docker stop $(docker ps -q)

# Option 2: Use different ports (edit docker-compose.yml)
# Change "8000:8000" to "8001:8000" for example
```

### Database data persists after `docker-compose down -v`

The `-v` flag removes volumes. To ensure clean state:

```bash
docker-compose down -v
docker system prune -f
```

### Cassandra is slow to become healthy

Cassandra can take 30-60 seconds to fully initialize. Be patient with initial startup.

## 🚀 Production Deployment

⚠️ **Before deploying to production:**

1. Change `SECRET_KEY` to a strong random value
2. Update database credentials
3. Set `VITE_API_URL` to production domain
4. Enable HTTPS/SSL
5. Configure CORS for your domain
6. Use managed database services (avoid container databases)
7. Implement proper logging and monitoring

## 📝 License

MIT License - See LICENSE file for details

## 👥 Contributing

Contributions are welcome! Please:

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## 📞 Support

For issues or questions, please open a GitHub issue.

### CORS errors when calling API

Verify `ALLOWED_ORIGINS` in `.env` includes your frontend URL.

## 🤝 Contributing

1. Create a feature branch (`git checkout -b feature/AmazingFeature`)
2. Commit changes (`git commit -m 'Add AmazingFeature'`)
3. Push to branch (`git push origin feature/AmazingFeature`)
4. Open a Pull Request

## 📄 License

This project is under MIT License.

## 👥 Team

- **Diego A. Barraza C.** - Lead Developer
- **Diego Romo M.** - Backend Architecture
- **Juan P. Gutierrez G.** - Frontend Development

**ITESO - Universidad Jesuita de Guadalajara**  
Project Date: February 3, 2026

## 📞 Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Zeen** - See it. Feel it. Keep it Zeen 🎬