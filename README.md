# AgentBounty

**Pay-per-use AI Agent Marketplace with Crypto Payments**

AgentBounty is a decentralized marketplace for AI agents where users pay per task using USDC on Base Sepolia. The platform implements the X402 Payment Protocol with EIP-712 signatures for gasless user transactions and CIBA (Client Initiated Backchannel Authentication) for payment approvals.

---

## 🎭 Try Demo Mode (No Setup Required!)

**Want to explore AgentBounty instantly without any setup?**

```bash
# Start server
uvicorn app.main:app --reload

# Open browser
http://localhost:8000/?demo=true
```

**Demo mode includes:**
- ✅ Auto-login with demo user
- ✅ Pre-configured wallet with 50 USDC
- ✅ 3 sample AI agent tasks with real results
- ✅ Simulated payment flow
- ✅ Full UI exploration

👉 **[Demo Mode Documentation](DEMO_MODE.md)** | **[Quick Start Guide](DEMO_QUICK_START.md)**

---

## 🚀 Quick Start (Production Mode)

### Prerequisites

- Python 3.9+
- Auth0 account (for authentication)
- Web3 wallet (MetaMask)
- Base Sepolia testnet access
- USDC on Base Sepolia (for testing)

### Installation

```bash
# Clone repository
git clone https://github.com/premananda108/AgentBounty.git
cd AgentBounty

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your credentials
```

### Running the Application

```bash
# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Open browser
# Navigate to http://localhost:8000
```

---

## 📋 Features

### ✅ Authentication & Authorization

- **Auth0 OAuth Integration**
  - Email/password login
  - GitHub OAuth
  - Google OAuth (future)
  - Session-based authentication
  - User profile management

- **Wallet Connection**
  - MetaMask integration
  - Wallet signature verification
  - Wallet-to-Auth0 linking
  - Balance checking

### ✅ AI Agents

**1. FactCheck Agent** 🔍
- Multi-stage fact verification
- URL and text input modes
- Web scraping with Bright Data
- Google Search integration
- Gemini AI analysis
- Source citation

**2. Travel Planner Agent** ✈️
- Flight search
- Hotel recommendations
- Real-time pricing
- Itinerary generation

### ✅ Payment System

**X402 Protocol Implementation:**
- HTTP 402 Payment Required
- EIP-712 typed signatures
- ERC-3009 transferWithAuthorization
- USDC payments on Base Sepolia
- Gasless transactions for users

**CIBA Payment Approval:**
- Threshold-based approval ($0.002+)
- Simulated approval for testing
- Real Auth0 CIBA ready (requires Guardian)
- Email verification alternative (planned)

### ✅ Task Management

- Create and execute AI agent tasks
- Real-time progress updates
- Background execution
- Result caching
- Payment status tracking
- Error handling

### ✅ Web Interface

- Modern Tailwind CSS design
- Responsive layout
- Real-time task updates (3s polling)
- Modal-based task creation
- Payment confirmation dialogs
- Markdown result rendering

---

## 🏗️ Architecture

```
AgentBounty/
├── app/
│   ├── agents/              # AI Agents
│   │   ├── base.py         # BaseAgent interface
│   │   ├── factcheck.py    # FactCheck agent
│   │   ├── ai_travel_planner.py
│   │   ├── registry.py     # Agent registration
│   │   └── scraper.py      # Web scraping utilities
│   │
│   ├── routers/            # API Routes
│   │   ├── auth.py         # Auth0 OAuth flow
│   │   ├── wallet.py       # Wallet connection
│   │   ├── tasks.py        # Task management + X402
│   │   └── payments.py     # Payment processing + CIBA
│   │
│   ├── services/           # Business Logic
│   │   ├── auth0_service.py    # Auth0 Management API (with caching)
│   │   ├── task_service.py     # Task execution
│   │   ├── payment_service.py  # X402 + EIP-712
│   │   └── ciba_service.py     # CIBA approval flow
│   │
│   ├── utils/              # Utilities
│   │   └── db.py           # SQLite schema & migrations
│   │
│   ├── static/             # Frontend
│   │   ├── index.html
│   │   ├── css/style.css
│   │   └── js/
│   │       ├── app.js      # Main logic
│   │       ├── ui.js       # UI components
│   │       ├── api.js      # API calls
│   │       └── auth.js     # Auth0 client
│   │
│   ├── config.py           # Configuration
│   └── main.py             # FastAPI app
│
├── .env                    # Environment variables
├── requirements.txt        # Python dependencies
└── agentbounty.db         # SQLite database
```

---

## 🔧 Configuration

### Environment Variables

Create `.env` file with:

```bash
# Auth0 - Web Application
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your_client_id
AUTH0_CLIENT_SECRET=your_client_secret
AUTH0_CALLBACK_URL=http://localhost:8000/auth/callback
AUTH0_AUDIENCE=https://your-tenant.auth0.com/api/v2/

# Auth0 - M2M Application (Management API)
AUTH0_M2M_CLIENT_ID=your_m2m_client_id
AUTH0_M2M_CLIENT_SECRET=your_m2m_client_secret

# Session
SECRET_KEY=your-secret-key-here

# AI APIs
GEMINI_API_KEY=your_gemini_api_key
BRIGHT_DATA_API_KEY=your_bright_data_key  # Optional

# Blockchain (Base Sepolia)
BASE_RPC_URL=https://sepolia.base.org
USDC_CONTRACT_ADDRESS=0x036CbD53842c5426634e7929541eC2318f3dCF7e
SERVER_WALLET_ADDRESS=your_server_wallet_address
SERVER_PRIVATE_KEY=your_server_private_key

# Database
DATABASE_PATH=/tmp/agentbounty.db

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=False

# Payment & CIBA
CIBA_THRESHOLD_USD=0.002
ENABLE_REAL_CIBA=false  # Set to true for production with Guardian
```

---

## 💳 CIBA Payment Approval

### How It Works

For payments **>= $0.002**, users must approve the transaction:

**Testing Mode (ENABLE_REAL_CIBA=false):**
1. User completes task
2. Clicks "View Result"
3. Sees CIBA approval screen
4. Clicks **"Simulate Approval"** button
5. Payment modal appears
6. Signs EIP-712 transaction
7. Receives result

**Production Mode (ENABLE_REAL_CIBA=true):**
- Requires Auth0 Guardian app
- User receives push notification
- Approves on phone
- Payment proceeds automatically

**Future: Email Mode:**
- Email with approval link (planned)
- No app installation required
- Best for general users

### Configuration

```bash
# Threshold for requiring CIBA approval
CIBA_THRESHOLD_USD=0.002

# Enable/disable real CIBA (vs simulation)
ENABLE_REAL_CIBA=false
```

---

## 🔐 Security Features

### Authentication
- ✅ Auth0 OAuth with session cookies
- ✅ CSRF protection via SessionMiddleware
- ✅ Secure cookie settings
- ✅ Token caching (reduces API calls)

### Payment Security
- ✅ EIP-712 signature verification
- ✅ Nonce validation
- ✅ Timestamp validation (1 hour window)
- ✅ CIBA approval for large payments
- ✅ User-specific wallet linking

### API Security
- ✅ Rate limiting via Auth0 caching
- ✅ User profile caching (5 min)
- ✅ Management token caching (23 hours)
- ✅ Dependency injection for services

---

## 📊 Database Schema

### Tables

**tasks**
- id, user_id, agent_type, status
- input_data, output_data
- estimated_cost, actual_cost
- payment_status, payment_tx_hash
- ciba_request_id, progress_message
- created_at, started_at, completed_at

**task_results**
- id, task_id, result_type, content
- storage_path, created_at

**ciba_requests**
- id, task_id, user_id, auth_req_id
- status, amount
- created_at, expires_at, approved_at

---

## 🧪 Testing

### Test Agents

```bash
# Test FactCheck Agent
curl -X POST http://localhost:8000/api/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "factcheck",
    "input_data": {
      "mode": "text",
      "text": "The sky is blue"
    }
  }'
```

### Test Payment Flow

1. Create task (< $0.002) → No CIBA
2. Create task (>= $0.002) → CIBA required
3. Simulate approval
4. Sign EIP-712 transaction
5. Verify result access

---

## 📚 API Documentation

### Authentication

```
GET  /auth/login          # Initiate Auth0 login
GET  /auth/callback       # Auth0 callback
GET  /auth/logout         # Logout
GET  /auth/user           # Get current user
```

### Wallet

```
POST /api/wallet/connect      # Connect wallet
GET  /api/wallet/info         # Get wallet info
POST /api/wallet/disconnect   # Disconnect wallet
```

### Tasks

```
GET  /api/tasks/              # List user tasks
POST /api/tasks/              # Create task
POST /api/tasks/{id}/start    # Start task
GET  /api/tasks/{id}/result   # Get result (X402)
```

### Payments

```
POST /api/payments/authorize              # Process payment
GET  /api/payments/ciba/status/{id}       # Check CIBA status
POST /api/payments/ciba/simulate/{id}     # Simulate approval (testing)
```

---

## 🚀 Deployment

### Production Checklist

- [ ] Set `DEBUG=false`
- [ ] Use production database path
- [ ] Configure real SMTP for emails
- [ ] Set up Auth0 Guardian (if using CIBA)
- [ ] Deploy to secure HTTPS endpoint
- [ ] Configure CORS for production domain
- [ ] Set strong `SECRET_KEY`
- [ ] Use production USDC contract
- [ ] Enable monitoring/logging

---

## 📝 Changelog

### v0.5.0 (Current)
- ✅ CIBA payment approval flow
- ✅ Threshold-based approval ($0.002+)
- ✅ Simulated CIBA for testing
- ✅ Auth0 API caching (fixes 429 errors)
- ✅ User profile caching (5 min)
- ✅ Management token caching (23 hours)
- ✅ Improved error handling
- ✅ Progress messages for tasks
- ✅ Database migrations

### v0.4.0
- ✅ FactCheck Agent with multi-stage verification
- ✅ Travel Planner Agent
- ✅ Wallet-to-Auth0 linking
- ✅ X402 Payment Protocol
- ✅ EIP-712 signatures

### v0.3.0
- ✅ Auth0 OAuth integration
- ✅ Session management
- ✅ User authentication

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- Auth0 for authentication
- Google Gemini for AI capabilities
- Base for blockchain infrastructure
- Bright Data for web scraping
- Tailwind CSS for UI components

---

## 📞 Support

For issues or questions:
- GitHub Issues: [Create Issue]
- Documentation: See `/docs` folder
- Email: support@agentbounty.example

---

**Built with ❤️ using FastAPI, Auth0, and Base Sepolia**
