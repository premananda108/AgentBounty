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
# Данные взяты из реальной базы данных
DEMO_TASKS = [
    {
        "id": "demo_task_001",
        "user_id": DEMO_USER["sub"],
        "agent_type": "factcheck",
        "status": "completed",
        "input_data": {
            "mode": "url",
            "url": "https://www.linkedin.com/posts/anthropicresearch_our-ceo-dario-amodei-met-with-indias-prime-activity-7382777706049945600-FXb0/?utm_source=share"
        },
        "output_data": None,
        "estimated_cost": 0.001,
        "actual_cost": 0.001,
        "payment_status": "paid",
        "payment_tx_hash": "0x336ac893ef4710c3756e5972f09d1e894689506bc85ca0a4cce18e347a887756",
        "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        "started_at": (datetime.utcnow() - timedelta(hours=2, minutes=-1)).isoformat(),
        "completed_at": (datetime.utcnow() - timedelta(hours=1, minutes=58)).isoformat(),
        "metadata": {"verdict": "TRUE", "confidence": 95, "claims": []},
        "progress_message": None
    },
    {
        "id": "demo_task_002",
        "user_id": DEMO_USER["sub"],
        "agent_type": "ai-travel-planner",
        "status": "completed",
        "input_data": {
            "text": "I need to travel from New York to Miami on October 29, 2025."
        },
        "output_data": None,
        "estimated_cost": 0.002,
        "actual_cost": 0.002,
        "payment_status": "unpaid",
        "payment_tx_hash": None,
        "created_at": (datetime.utcnow() - timedelta(minutes=45)).isoformat(),
        "started_at": (datetime.utcnow() - timedelta(minutes=44)).isoformat(),
        "completed_at": (datetime.utcnow() - timedelta(minutes=42)).isoformat(),
        "metadata": {"message": "I need to travel from New York to Miami on October 29, 2025.", "mcp_enabled": True},
        "progress_message": None
    },
]

# Demo Results - богатый контент для каждой задачи
DEMO_RESULTS = {
    "demo_task_001": {
        "task_id": "demo_task_001",
        "status": "completed",
        "result_type": "text",
        "actual_cost": 0.001,
        "content": """## Post Summary

The LinkedIn post, published by the official Anthropic company page, announces that its CEO, Dario Amodei, met with India's Prime Minister Narendra Modi in New Delhi. The post details the discussion points, focusing on Anthropic's commitment to advancing safe and beneficial AI in India, cultivating India's AI innovation ecosystem, and aligning AI development with democratic values, serving diverse sectors like healthcare, education, and agriculture.

## Claims Identified

1. The LinkedIn post was made by a user named "Anthropic."
2. Anthropic's LinkedIn profile URL is `https://www.linkedin.com/company/anthropicresearch`.
3. Anthropic has 1,571,092 followers on LinkedIn.
4. The LinkedIn post was timestamped "1 week ago" and was marked as "Edited."
5. Anthropic's CEO is Dario Amodei.
6. Dario Amodei met with India's Prime Minister Narendra Modi.
7. The meeting took place in New Delhi.
8. Anthropic announced plans to open its India office in early 2026.
9. Anthropic plans to hire local teams in India.
10. Anthropic plans to support India's entrepreneurial ecosystem.

## Verification Results

### Claim 5: Anthropic's CEO is Dario Amodei
**Findings**: Verified. An update on Anthropic's official LinkedIn page mentions "Our CEO, Dario Amodei." This is a widely known and consistently reported fact about the company.
**Credibility Level**: High (Official company LinkedIn page).

### Claim 6: Dario Amodei met with India's Prime Minister Narendra Modi
**Findings**: Verified. Multiple authoritative news sources and government announcements confirm this meeting.
- The Hindu (Oct 13, 2025): "Prime Minister Narendra Modi on Saturday met Dario Amodei, the CEO of Anthropic..."
- PM India (Oct 11, 2025) official press release: "Mr. Dario Amodei, CEO of Anthropic, today met Prime Minister, Shri Narendra Modi..."
**Credibility Level**: High (Government source and reputable news organizations).

### Claim 7: The meeting took place in New Delhi
**Findings**: Verified. Multiple authoritative news sources specify New Delhi as the meeting location.
**Credibility Level**: High (Government source and reputable news organizations).

### Claim 8: Anthropic announced plans to open its India office in early 2026
**Findings**: Verified. Anthropic's official website and multiple news sources confirm the announcement.
- Anthropic's official news release (Oct 7, 2025): "Today we're announcing that we're expanding our global operations to India, with plans to open an office in Bengaluru in early 2026."
**Credibility Level**: High (Official company announcement and reputable news organizations).

## Final Verdict

**VERDICT: TRUE**
**Confidence Score: 95%**

The substantive claims made in Anthropic's LinkedIn post regarding its CEO Dario Amodei's meeting with Indian Prime Minister Narendra Modi in New Delhi, and the company's plans to establish an office in India, hire local talent, and support the entrepreneurial ecosystem, are **TRUE**. These claims are extensively corroborated by official government sources, Anthropic's own announcements, and numerous reputable news organizations.

---
*Analysis completed with high confidence*
*Multiple authoritative sources verified*
""",
        "metadata": {
            "verdict": "TRUE",
            "confidence": 95,
            "claims": []
        }
    },
    "demo_task_002": {
        "task_id": "demo_task_002",
        "status": "completed",
        "result_type": "text",
        "actual_cost": 0.002,
        "content": """## Flights from New York to Miami on October 29, 2025

**American Airlines**
- **Price:** Starting from $126.96
- **Departure/Arrival:** Daily service from JFK/LGA to MIA
- **Duration:** Approximately 3 hours
- **Booking URL:** https://www.aa.com/en-us/flights-from-new-york-to-miami

**Spirit Airlines**
- **Price:** From $63 (Roundtrip, Nov 12-15, 2025)
- **Departure/Arrival:** From New York (LGA) to Miami (MIA)
- **Booking URL:** https://www.spirit.com/en/flights-from-new-york-to-miami

**Frontier Airlines**
- **Price:** From $54 (Roundtrip)
- **Departure/Arrival:** From NYC (JFK/LGA) to Miami (MIA)
- **Booking URL:** https://flights.flyfrontier.com/en/flights-from-new-york-to-miami

---

## Hotels in Miami

**Novotel Miami Brickell** ⭐⭐⭐⭐
- **Rating:** 4.3 (3K reviews)
- **Price:** $165 per night
- **Amenities:** Pool, Eco-certified
- **Booking URL:** https://www.expedia.com/Miami-Hotels.d178286.Travel-Guide-Hotels

**The Goodtime Hotel, Miami Beach** ⭐⭐⭐⭐
- **Rating:** 4.3 (1.9K reviews)
- **Price:** $195 per night (26% less than usual)
- **Amenities:** Dining, pools
- **Booking URL:** https://www.expedia.com/Miami-Hotels.d178286.Travel-Guide-Hotels

**DoubleTree by Hilton Miami Airport** ⭐⭐⭐
- **Rating:** 3.6 (4.2K reviews)
- **Price:** $111 per night (21% less than usual)
- **Amenities:** Pool, dining
- **Booking URL:** https://www.expedia.com/Miami-Hotels.d178286.Travel-Guide-Hotels

**JW Marriott Marquis Miami** ⭐⭐⭐⭐⭐
- **Rating:** 4.4 (2.6K reviews)
- **Price:** $276 per night (31% less than usual)
- **Amenities:** Acclaimed restaurant
- **Booking URL:** https://www.expedia.com/Miami-Hotels.d178286.Travel-Guide-Hotels

**Best Western Plus Miami Intl Airport** ⭐⭐⭐⭐
- **Rating:** 4.0 (2.8K reviews)
- **Price:** $124 per night
- **Amenities:** Dining, bar
- **Booking URL:** https://www.expedia.com/Miami-Hotels.d178286.Travel-Guide-Hotels

**The Biltmore Hotel - Coral Gables**
- **Location:** Coral Gables, near Miami Beach and downtown Miami
- **Amenities:** Fontana Restaurant, Sunday Brunch, Championship Golf Course
- **Booking URL:** https://biltmorehotel.com/

---
*Prices and availability are subject to change. Please check the websites for current information for your specific dates.*
""",
        "metadata": {
            "message": "I need to travel from New York to Miami on October 29, 2025.",
            "mcp_enabled": True
        }
    }
}

# Preview для задач (первые 200 символов)
DEMO_PREVIEWS = {
    "demo_task_001": "## Post Summary\n\nThe LinkedIn post, published by the official Anthropic company page, announces that its CEO, Dario Amodei, met with India's Prime Minister Narendra Modi in New Delhi. The post details the discussion points...",
    "demo_task_002": "## Flights from New York to Miami on October 29, 2025\n\n**American Airlines**\n- **Price:** Starting from $126.96\n- **Departure/Arrival:** Daily service from JFK/LGA to MIA\n- **Duration:** Approximately 3 hours..."
}
