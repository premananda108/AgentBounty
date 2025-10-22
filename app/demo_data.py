"""
Demo Mode Mock Data - Realistic sample data for demo users
"""
from datetime import datetime, timedelta
import json

# Demo User
DEMO_USER = {
    "sub": "demo|user_12345",
    "email": "demo@agentbounty.com",
    "name": "Demo User",
    "nickname": "demo",
    "picture": "https://i.pravatar.cc/150?img=68",
    "email_verified": True
}

# Demo Wallet
DEMO_WALLET = {
    "wallet_address": "0xdE3089c44de71234567890123456789012345678",
    "usdc_balance": 50.25,
    "connected": True
}

# Demo Tasks - 2 задачи с разными статусами для демонстрации функционала
DEMO_TASKS = [
    {
        "id": "demo_task_001",
        "user_id": DEMO_USER["sub"],
        "agent_type": "factcheck",
        "status": "completed",
        "input_data": {
            "mode": "text",
            "text": "Artificial Intelligence will automate 50% of jobs by 2030"
        },
        "output_data": None,
        "estimated_cost": 0.0025,
        "actual_cost": 0.0023,
        "payment_status": "unpaid",
        "payment_tx_hash": None,
        "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        "started_at": (datetime.utcnow() - timedelta(hours=2, minutes=-1)).isoformat(),
        "completed_at": (datetime.utcnow() - timedelta(hours=1, minutes=58)).isoformat(),
        "metadata": {"duration_seconds": 3.2},
        "progress_message": None
    },
    {
        "id": "demo_task_002",
        "user_id": DEMO_USER["sub"],
        "agent_type": "ai_travel_planner",
        "status": "completed",
        "input_data": {
            "origin": "San Francisco",
            "destination": "Tokyo",
            "dates": "2025-12-01 to 2025-12-10",
            "budget": "moderate"
        },
        "output_data": None,
        "estimated_cost": 0.0018,
        "actual_cost": 0.0016,
        "payment_status": "unpaid",
        "payment_tx_hash": None,
        "created_at": (datetime.utcnow() - timedelta(minutes=45)).isoformat(),
        "started_at": (datetime.utcnow() - timedelta(minutes=44)).isoformat(),
        "completed_at": (datetime.utcnow() - timedelta(minutes=42)).isoformat(),
        "metadata": {"duration_seconds": 2.8},
        "progress_message": None
    },
]

# Demo Results - богатый контент для каждой задачи
DEMO_RESULTS = {
    "demo_task_001": {
        "task_id": "demo_task_001",
        "status": "completed",
        "result_type": "markdown",
        "actual_cost": 0.0023,
        "content": """## FactCheck Analysis: AI Job Automation

### Claim Verification
**Statement**: "Artificial Intelligence will automate 50% of jobs by 2030"

**Verdict**: ⚠️ **PARTIALLY TRUE** - Requires context

### Evidence Analysis

#### Supporting Evidence:
1. **McKinsey Global Institute (2023)**
   - Predicts 30% of work activities could be automated by 2030
   - Up to 375M workers globally may need to switch occupations
   - Source: [McKinsey Report](https://example.com/mckinsey)

2. **World Economic Forum (2023)**
   - Estimates 85M jobs displaced by 2025
   - BUT also predicts 97M new jobs created
   - Net positive of 12M jobs
   - Source: [WEF Future of Jobs](https://example.com/wef)

3. **Oxford University Study (2013)**
   - Originally claimed 47% of US jobs at risk
   - Later studies revised this to 14% high-risk
   - Source: [Frey & Osborne](https://example.com/oxford)

#### Contradicting Evidence:
1. **OECD Analysis (2023)**
   - Only 14% of jobs face high automation risk
   - 32% likely to see significant changes, not elimination
   - Source: [OECD](https://example.com/oecd)

2. **MIT Technology Review (2024)**
   - AI augments rather than replaces workers
   - Focus shifting to human-AI collaboration
   - Source: [MIT Review](https://example.com/mit)

### Conclusion
The claim oversimplifies a complex situation. While AI will significantly impact the job market by 2030:
- **Automation** will affect 30-40% of work activities (not entire jobs)
- **Job displacement** likely in 10-15% of roles
- **Job transformation** more common than elimination
- **New jobs** will emerge, potentially offsetting losses

**Recommendation**: The 50% figure lacks nuance. More accurate: "AI will significantly transform 40-50% of jobs by 2030, with 10-15% facing high automation risk."

---
*Analysis completed in 3.2 seconds*
*Sources verified: 5/5*
""",
        "metadata": {
            "sources_checked": 5,
            "confidence_score": 0.78,
            "verification_time": 3.2
        }
    },
    "demo_task_002": {
        "task_id": "demo_task_002",
        "status": "completed",
        "result_type": "markdown",
        "actual_cost": 0.0016,
        "content": """## ✈️ Travel Plan: San Francisco → Tokyo

### Flight Options

#### Recommended: United Airlines
- **Departure**: SFO → NRT (Narita)
- **Date**: Dec 1, 2025 - 11:30 AM
- **Duration**: 11h 15m (non-stop)
- **Price**: ~$850 (Economy), ~$2,400 (Business)
- **Arrival**: Dec 2, 2025 - 3:45 PM JST

#### Alternative: ANA
- **Departure**: SFO → HND (Haneda)
- **Date**: Dec 1, 2025 - 1:00 PM
- **Duration**: 11h 30m (non-stop)
- **Price**: ~$920 (Economy), ~$2,800 (Business)
- **Arrival**: Dec 2, 2025 - 5:30 PM JST

### Hotel Recommendations

#### 🏨 Moderate Budget Hotels

**1. Hotel Gracery Shinjuku** ⭐⭐⭐⭐
- Location: Shinjuku (Godzilla head!)
- Price: ~$120/night
- Rating: 4.3/5 (2,340 reviews)
- Near: JR Shinjuku Station (5 min walk)

**2. Shibuya Tokyu REI Hotel** ⭐⭐⭐
- Location: Shibuya crossing
- Price: ~$95/night
- Rating: 4.1/5 (1,820 reviews)
- Near: Shibuya Station (3 min walk)

**3. Richmond Hotel Premier Asakusa** ⭐⭐⭐⭐
- Location: Asakusa (traditional area)
- Price: ~$110/night
- Rating: 4.5/5 (2,890 reviews)
- Near: Sensoji Temple (8 min walk)

### 9-Day Itinerary

**Day 1-2 (Dec 2-3)**: Arrival & Shinjuku
- Check-in at hotel
- Explore Shinjuku Gyoen Garden
- Visit Tokyo Metropolitan Building (free observation deck)
- Evening: Kabukicho & Golden Gai

**Day 3-4 (Dec 4-5)**: Traditional Tokyo
- Asakusa: Sensoji Temple
- Ueno Park & Museums
- Akihabara (electronics & anime)

**Day 5-6 (Dec 6-7)**: Modern Tokyo
- Shibuya Crossing & Shopping
- Harajuku (Takeshita Street)
- Meiji Shrine
- teamLab Borderless Museum

**Day 7 (Dec 8)**: Day Trip
- Option A: Mt. Fuji & Hakone
- Option B: Nikko (UNESCO site)

**Day 8-9 (Dec 9-10)**: Last Days
- Tsukiji Outer Market
- Tokyo Skytree
- Shopping: Ginza
- Departure prep

### Budget Estimate (Moderate)

- **Flights**: $850 (round trip)
- **Hotels**: $110/night × 9 = $990
- **Food**: $50/day × 9 = $450
- **Transport**: JR Pass (7-day) = $280
- **Activities**: $300
- **Shopping/Misc**: $400

**Total**: ~$3,270 per person

### Travel Tips
- 🎫 Get JR Pass before arrival (must buy outside Japan)
- 📱 Rent pocket WiFi at airport
- 💴 ATMs at 7-Eleven accept foreign cards
- 🍜 Try: Ramen, Sushi, Tempura, Okonomiyaki
- 🚇 Download: Google Maps, Hyperdia (train times)

---
*Plan generated in 2.8 seconds*
*Prices are estimates, check current rates*
""",
        "metadata": {
            "flights_found": 8,
            "hotels_found": 12,
            "total_budget_estimate": 3270
        }
    }
}

# Preview для задач (первые 200 символов)
DEMO_PREVIEWS = {
    "demo_task_001": "## FactCheck Analysis: AI Job Automation\n\n### Claim Verification\n**Statement**: \"Artificial Intelligence will automate 50% of jobs by 2030\"\n\n**Verdict**: ⚠️ **PARTIALLY TRUE** - Requires context...",
    "demo_task_002": "## ✈️ Travel Plan: San Francisco → Tokyo\n\n### Flight Options\n\n#### Recommended: United Airlines\n- **Departure**: SFO → NRT (Narita)\n- **Date**: Dec 1, 2025 - 11:30 AM\n- **Duration**: 11h..."
}
