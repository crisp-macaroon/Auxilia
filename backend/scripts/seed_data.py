"""
Seed Script for Auxilia Backend
Populates the database with realistic dummy data for demonstration
"""
import asyncio
import random
import uuid
import json
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
import sys
sys.path.insert(0, '/home/statixlo/Develp/hackathon/devtrails/Auxilia/backend')

from app.models.database import Base, Rider, Zone, Policy, Claim, TriggerEvent, Transaction
from app.models.database import PersonaType, PolicyStatus, ClaimStatus, TriggerType, RiderStatus
from app.core.config import settings

# Mumbai zones with realistic coordinates
MUMBAI_ZONES = [
    {"id": "andheri-east", "name": "Andheri East", "lat": 19.1136, "lon": 72.8697, "risk": "medium", "city": "Mumbai", "state": "Maharashtra"},
    {"id": "andheri-west", "name": "Andheri West", "lat": 19.1364, "lon": 72.8296, "risk": "medium", "city": "Mumbai", "state": "Maharashtra"},
    {"id": "bandra-west", "name": "Bandra West", "lat": 19.0596, "lon": 72.8295, "risk": "low", "city": "Mumbai", "state": "Maharashtra"},
    {"id": "bandra-east", "name": "Bandra East", "lat": 19.0587, "lon": 72.8482, "risk": "medium", "city": "Mumbai", "state": "Maharashtra"},
    {"id": "powai", "name": "Powai", "lat": 19.1176, "lon": 72.9060, "risk": "low", "city": "Mumbai", "state": "Maharashtra"},
    {"id": "kurla", "name": "Kurla", "lat": 19.0726, "lon": 72.8845, "risk": "high", "city": "Mumbai", "state": "Maharashtra"},
    {"id": "dadar", "name": "Dadar", "lat": 19.0178, "lon": 72.8478, "risk": "high", "city": "Mumbai", "state": "Maharashtra"},
    {"id": "lower-parel", "name": "Lower Parel", "lat": 19.0047, "lon": 72.8305, "risk": "medium", "city": "Mumbai", "state": "Maharashtra"},
    {"id": "malad-west", "name": "Malad West", "lat": 19.1872, "lon": 72.8484, "risk": "medium", "city": "Mumbai", "state": "Maharashtra"},
    {"id": "goregaon-east", "name": "Goregaon East", "lat": 19.1663, "lon": 72.8526, "risk": "medium", "city": "Mumbai", "state": "Maharashtra"},
    {"id": "borivali-west", "name": "Borivali West", "lat": 19.2307, "lon": 72.8567, "risk": "low", "city": "Mumbai", "state": "Maharashtra"},
    {"id": "thane-west", "name": "Thane West", "lat": 19.2183, "lon": 72.9781, "risk": "medium", "city": "Mumbai", "state": "Maharashtra"},
    {"id": "vashi", "name": "Vashi", "lat": 19.0771, "lon": 72.9986, "risk": "low", "city": "Mumbai", "state": "Maharashtra"},
    {"id": "churchgate", "name": "Churchgate", "lat": 18.9322, "lon": 72.8264, "risk": "high", "city": "Mumbai", "state": "Maharashtra"},
    {"id": "colaba", "name": "Colaba", "lat": 18.9067, "lon": 72.8147, "risk": "medium", "city": "Mumbai", "state": "Maharashtra"},
]

# Bangalore zones
BANGALORE_ZONES = [
    {"id": "koramangala", "name": "Koramangala", "lat": 12.9352, "lon": 77.6245, "risk": "medium", "city": "Bangalore", "state": "Karnataka"},
    {"id": "indiranagar", "name": "Indiranagar", "lat": 12.9784, "lon": 77.6408, "risk": "low", "city": "Bangalore", "state": "Karnataka"},
    {"id": "whitefield", "name": "Whitefield", "lat": 12.9698, "lon": 77.7500, "risk": "medium", "city": "Bangalore", "state": "Karnataka"},
    {"id": "hsr-layout", "name": "HSR Layout", "lat": 12.9116, "lon": 77.6389, "risk": "low", "city": "Bangalore", "state": "Karnataka"},
    {"id": "electronic-city", "name": "Electronic City", "lat": 12.8399, "lon": 77.6770, "risk": "medium", "city": "Bangalore", "state": "Karnataka"},
    {"id": "marathahalli", "name": "Marathahalli", "lat": 12.9591, "lon": 77.6974, "risk": "high", "city": "Bangalore", "state": "Karnataka"},
    {"id": "jayanagar", "name": "Jayanagar", "lat": 12.9308, "lon": 77.5838, "risk": "low", "city": "Bangalore", "state": "Karnataka"},
    {"id": "btm-layout", "name": "BTM Layout", "lat": 12.9166, "lon": 77.6101, "risk": "medium", "city": "Bangalore", "state": "Karnataka"},
    {"id": "mg-road", "name": "MG Road", "lat": 12.9756, "lon": 77.6062, "risk": "high", "city": "Bangalore", "state": "Karnataka"},
    {"id": "hebbal", "name": "Hebbal", "lat": 13.0358, "lon": 77.5970, "risk": "medium", "city": "Bangalore", "state": "Karnataka"},
]

# Delhi NCR zones
DELHI_ZONES = [
    {"id": "connaught-place", "name": "Connaught Place", "lat": 28.6315, "lon": 77.2167, "risk": "high", "city": "Delhi", "state": "Delhi"},
    {"id": "saket", "name": "Saket", "lat": 28.5245, "lon": 77.2066, "risk": "medium", "city": "Delhi", "state": "Delhi"},
    {"id": "dwarka", "name": "Dwarka", "lat": 28.5921, "lon": 77.0460, "risk": "low", "city": "Delhi", "state": "Delhi"},
    {"id": "rohini", "name": "Rohini", "lat": 28.7495, "lon": 77.0565, "risk": "medium", "city": "Delhi", "state": "Delhi"},
    {"id": "lajpat-nagar", "name": "Lajpat Nagar", "lat": 28.5700, "lon": 77.2373, "risk": "high", "city": "Delhi", "state": "Delhi"},
    {"id": "karol-bagh", "name": "Karol Bagh", "lat": 28.6514, "lon": 77.1907, "risk": "high", "city": "Delhi", "state": "Delhi"},
    {"id": "janakpuri", "name": "Janakpuri", "lat": 28.6219, "lon": 77.0878, "risk": "medium", "city": "Delhi", "state": "Delhi"},
    {"id": "vasant-kunj", "name": "Vasant Kunj", "lat": 28.5205, "lon": 77.1567, "risk": "low", "city": "Delhi", "state": "Delhi"},
    {"id": "noida-sec-18", "name": "Noida Sector 18", "lat": 28.5706, "lon": 77.3260, "risk": "medium", "city": "Noida", "state": "Uttar Pradesh"},
    {"id": "gurgaon-cyber-city", "name": "Gurgaon Cyber City", "lat": 28.4940, "lon": 77.0886, "risk": "medium", "city": "Gurgaon", "state": "Haryana"},
]

# Hyderabad zones
HYDERABAD_ZONES = [
    {"id": "hitech-city", "name": "HITEC City", "lat": 17.4435, "lon": 78.3772, "risk": "medium", "city": "Hyderabad", "state": "Telangana"},
    {"id": "gachibowli", "name": "Gachibowli", "lat": 17.4401, "lon": 78.3489, "risk": "low", "city": "Hyderabad", "state": "Telangana"},
    {"id": "madhapur", "name": "Madhapur", "lat": 17.4483, "lon": 78.3915, "risk": "medium", "city": "Hyderabad", "state": "Telangana"},
    {"id": "banjara-hills", "name": "Banjara Hills", "lat": 17.4156, "lon": 78.4347, "risk": "low", "city": "Hyderabad", "state": "Telangana"},
    {"id": "jubilee-hills", "name": "Jubilee Hills", "lat": 17.4326, "lon": 78.4071, "risk": "low", "city": "Hyderabad", "state": "Telangana"},
    {"id": "secunderabad", "name": "Secunderabad", "lat": 17.4399, "lon": 78.4983, "risk": "high", "city": "Hyderabad", "state": "Telangana"},
    {"id": "kukatpally", "name": "Kukatpally", "lat": 17.4849, "lon": 78.4138, "risk": "medium", "city": "Hyderabad", "state": "Telangana"},
    {"id": "ameerpet", "name": "Ameerpet", "lat": 17.4375, "lon": 78.4482, "risk": "high", "city": "Hyderabad", "state": "Telangana"},
    {"id": "lb-nagar", "name": "LB Nagar", "lat": 17.3457, "lon": 78.5522, "risk": "medium", "city": "Hyderabad", "state": "Telangana"},
    {"id": "dilsukhnagar", "name": "Dilsukhnagar", "lat": 17.3688, "lon": 78.5247, "risk": "high", "city": "Hyderabad", "state": "Telangana"},
]

# Kerala zones (Kochi, Trivandrum, Calicut)
KERALA_ZONES = [
    {"id": "ernakulam", "name": "Ernakulam", "lat": 9.9816, "lon": 76.2999, "risk": "medium", "city": "Kochi", "state": "Kerala"},
    {"id": "fort-kochi", "name": "Fort Kochi", "lat": 9.9639, "lon": 76.2432, "risk": "low", "city": "Kochi", "state": "Kerala"},
    {"id": "marine-drive-kochi", "name": "Marine Drive", "lat": 9.9784, "lon": 76.2825, "risk": "medium", "city": "Kochi", "state": "Kerala"},
    {"id": "kakkanad", "name": "Kakkanad", "lat": 10.0159, "lon": 76.3419, "risk": "low", "city": "Kochi", "state": "Kerala"},
    {"id": "edappally", "name": "Edappally", "lat": 10.0261, "lon": 76.3125, "risk": "medium", "city": "Kochi", "state": "Kerala"},
    {"id": "technopark-tvm", "name": "Technopark", "lat": 8.5568, "lon": 76.8810, "risk": "low", "city": "Trivandrum", "state": "Kerala"},
    {"id": "kowdiar", "name": "Kowdiar", "lat": 8.5074, "lon": 76.9561, "risk": "low", "city": "Trivandrum", "state": "Kerala"},
    {"id": "kazhakootam", "name": "Kazhakootam", "lat": 8.5720, "lon": 76.8735, "risk": "medium", "city": "Trivandrum", "state": "Kerala"},
    {"id": "kozhikode-beach", "name": "Kozhikode Beach", "lat": 11.2588, "lon": 75.7804, "risk": "high", "city": "Calicut", "state": "Kerala"},
    {"id": "mavoor-road", "name": "Mavoor Road", "lat": 11.2560, "lon": 75.7873, "risk": "medium", "city": "Calicut", "state": "Kerala"},
]

# Combined zones list
ALL_ZONES = MUMBAI_ZONES + BANGALORE_ZONES + DELHI_ZONES + HYDERABAD_ZONES + KERALA_ZONES

# Realistic Indian names
FIRST_NAMES = [
    "Rahul", "Amit", "Suresh", "Vikram", "Rajesh", "Sanjay", "Anil", "Deepak",
    "Pradeep", "Mahesh", "Ramesh", "Sunil", "Vijay", "Ajay", "Prakash", "Mohan",
    "Ravi", "Ashok", "Manoj", "Kishore", "Dinesh", "Ganesh", "Mukesh", "Naresh",
    "Santosh", "Yogesh", "Nilesh", "Jitendra", "Harish", "Rakesh"
]

LAST_NAMES = [
    "Sharma", "Patel", "Verma", "Gupta", "Singh", "Kumar", "Yadav", "Chauhan",
    "Joshi", "Mishra", "Pandey", "Tiwari", "Dubey", "Shukla", "Saxena", "Agarwal",
    "Malhotra", "Kapoor", "Khanna", "Bhatia", "Reddy", "Nair", "Menon", "Pillai",
    "Desai", "Shah", "Mehta", "Jain", "Choudhary", "Thakur"
]


def generate_phone():
    return f"+91{random.randint(7000000000, 9999999999)}"


def random_date(start_days_ago: int, end_days_ago: int = 0):
    start = datetime.utcnow() - timedelta(days=start_days_ago)
    end = datetime.utcnow() - timedelta(days=end_days_ago)
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


async def seed_database():
    """Main seeding function"""
    print("Connecting to database...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        print("Dropping existing tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("\n1. Seeding zones...")
        zones = await seed_zones(session)
        await session.commit()
        
        print("2. Seeding riders...")
        riders = await seed_riders(session, zones)
        await session.commit()
        
        print("3. Seeding policies...")
        policies = await seed_policies(session, riders, zones)
        await session.commit()
        
        print("4. Seeding trigger events...")
        trigger_events = await seed_trigger_events(session, zones)
        await session.commit()
        
        print("5. Seeding claims...")
        claims = await seed_claims(session, policies, riders, trigger_events)
        await session.commit()
        
        print("6. Seeding transactions...")
        await seed_transactions(session, claims)
        await session.commit()
        
        print("\n" + "=" * 50)
        print("Database seeded successfully!")
        print("=" * 50)
        print(f"  Zones:          {len(zones)}")
        print(f"  Riders:         {len(riders)}")
        print(f"  Policies:       {len(policies)}")
        print(f"  Trigger Events: {len(trigger_events)}")
        print(f"  Claims:         {len(claims)}")
        print("=" * 50)


async def seed_zones(session: AsyncSession) -> list:
    """Seed zones across all cities"""
    zones = []
    risk_factors = {"low": 0.8, "medium": 1.0, "high": 1.3}
    
    for zone_data in ALL_ZONES:
        zone = Zone(
            id=zone_data["id"],
            name=zone_data["name"],
            city=zone_data["city"],
            state=zone_data["state"],
            country="IN",
            latitude=zone_data["lat"],
            longitude=zone_data["lon"],
            radius_km=2.5,
            risk_level=zone_data["risk"],
            base_premium_factor=risk_factors[zone_data["risk"]],
            is_active=True,
            created_at=random_date(90, 60)
        )
        session.add(zone)
        zones.append(zone)
    
    await session.flush()
    print(f"   Created {len(zones)} zones across {len(set(z['city'] for z in ALL_ZONES))} cities")
    return zones


async def seed_riders(session: AsyncSession, zones: list) -> list:
    """Seed delivery riders across all cities"""
    riders = []
    
    for i in range(150):  # Increased from 50 to 150 for more cities
        zone = random.choice(zones)
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        
        # Slight variation in coordinates within zone
        lat_offset = random.uniform(-0.01, 0.01)
        lon_offset = random.uniform(-0.01, 0.01)
        
        persona = random.choice([PersonaType.QCOMMERCE, PersonaType.FOOD_DELIVERY])
        
        rider = Rider(
            id=str(uuid.uuid4()),
            phone=generate_phone(),
            name=f"{first_name} {last_name}",
            email=f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 99)}@gmail.com",
            persona=persona,
            zone_id=zone.id,
            latitude=zone.latitude + lat_offset,
            longitude=zone.longitude + lon_offset,
            risk_score=round(random.uniform(0.1, 0.9), 2),
            status=random.choice([RiderStatus.ACTIVE, RiderStatus.ACTIVE, RiderStatus.ACTIVE, RiderStatus.INACTIVE]),
            created_at=random_date(180, 30)
        )
        session.add(rider)
        riders.append(rider)
    
    await session.flush()
    print(f"   Created {len(riders)} riders")
    return riders


async def seed_policies(session: AsyncSession, riders: list, zones: list) -> list:
    """Seed insurance policies"""
    policies = []
    
    # Premium and coverage by persona (weekly pricing)
    policy_config = {
        PersonaType.QCOMMERCE: {"premium": 99, "coverage": 5000},     # Rs 99/week
        PersonaType.FOOD_DELIVERY: {"premium": 79, "coverage": 4000}, # Rs 79/week
    }
    
    # 70% of riders have policies
    for rider in random.sample(riders, int(len(riders) * 0.7)):
        config = policy_config[rider.persona]
        zone = next((z for z in zones if z.id == rider.zone_id), random.choice(zones))
        
        # Apply zone risk factor to premium
        premium = config["premium"] * zone.base_premium_factor
        
        start_date = random_date(60, 5)
        
        policy = Policy(
            id=str(uuid.uuid4()),
            rider_id=rider.id,
            zone_id=zone.id,
            persona=rider.persona,
            premium=round(premium, 2),
            coverage=config["coverage"],
            start_date=start_date,
            end_date=start_date + timedelta(days=7),  # Weekly policy
            status=PolicyStatus.ACTIVE,
            tx_hash=f"0x{uuid.uuid4().hex}" if random.random() > 0.3 else None,
            created_at=start_date
        )
        session.add(policy)
        policies.append(policy)
    
    await session.flush()
    print(f"   Created {len(policies)} policies")
    return policies


async def seed_trigger_events(session: AsyncSession, zones: list) -> list:
    """Seed trigger events (weather, traffic, etc.)"""
    trigger_events = []
    
    thresholds = {
        TriggerType.RAIN: 50.0,
        TriggerType.TRAFFIC: 60.0,
        TriggerType.SURGE: 2.5,
        TriggerType.ROAD_DISRUPTION: 3.0
    }
    
    sources = {
        TriggerType.RAIN: "OpenWeatherMap",
        TriggerType.TRAFFIC: "TomTom",
        TriggerType.SURGE: "Internal",
        TriggerType.ROAD_DISRUPTION: "NewsAPI+Gemini"
    }
    
    # Create 300 trigger events over the last 7 days (increased for more zones)
    # Weighted distribution for realistic analytics
    trigger_weights = {
        TriggerType.RAIN: 35,           # 35% - most common
        TriggerType.TRAFFIC: 30,        # 30% - second most common
        TriggerType.SURGE: 20,          # 20% - moderate
        TriggerType.ROAD_DISRUPTION: 15 # 15% - least common but high impact
    }
    trigger_types_weighted = []
    for t, weight in trigger_weights.items():
        trigger_types_weighted.extend([t] * weight)
    
    for _ in range(300):
        zone = random.choice(zones)
        trigger_type = random.choice(trigger_types_weighted)
        threshold = thresholds[trigger_type]
        
        # 40% of triggers exceed threshold
        if random.random() > 0.6:
            value = threshold * random.uniform(1.0, 2.0)  # Above threshold
            is_active = True
        else:
            value = threshold * random.uniform(0.3, 0.9)  # Below threshold
            is_active = False
        
        event_time = random_date(7, 0)
        
        event = TriggerEvent(
            id=str(uuid.uuid4()),
            zone_id=zone.id,
            trigger_type=trigger_type,
            value=round(value, 2),
            threshold=threshold,
            is_active=is_active,
            source=sources[trigger_type],
            raw_data=json.dumps({
                "api_response": "sample_data",
                "confidence": round(random.uniform(0.8, 1.0), 2),
                "timestamp": event_time.isoformat()
            }),
            created_at=event_time,
            expires_at=event_time + timedelta(hours=random.randint(1, 6))
        )
        session.add(event)
        trigger_events.append(event)
    
    await session.flush()
    print(f"   Created {len(trigger_events)} trigger events")
    return trigger_events


async def seed_claims(session: AsyncSession, policies: list, riders: list, trigger_events: list) -> list:
    """Seed insurance claims"""
    claims = []
    
    payout_amounts = {
        TriggerType.RAIN: 150,
        TriggerType.TRAFFIC: 100,
        TriggerType.SURGE: 200,
        TriggerType.ROAD_DISRUPTION: 500
    }
    
    # Filter active trigger events
    active_triggers = [t for t in trigger_events if t.is_active]
    
    # Create 120-150 claims (increased for more riders)
    num_claims = random.randint(120, 150)
    
    for _ in range(num_claims):
        policy = random.choice(policies)
        rider = next((r for r in riders if r.id == policy.rider_id), None)
        if not rider:
            continue
        
        # Pick a trigger event that matches the zone or a random one
        zone_triggers = [t for t in active_triggers if t.zone_id == policy.zone_id]
        if zone_triggers:
            trigger_event = random.choice(zone_triggers)
        else:
            trigger_event = random.choice(active_triggers) if active_triggers else random.choice(trigger_events)
        
        trigger_type = trigger_event.trigger_type
        amount = payout_amounts[trigger_type]
        
        # Weighted status distribution
        statuses = [ClaimStatus.PENDING, ClaimStatus.PROCESSING, ClaimStatus.APPROVED, ClaimStatus.PAID, ClaimStatus.REJECTED]
        weights = [0.08, 0.07, 0.10, 0.65, 0.10]
        status = random.choices(statuses, weights=weights)[0]
        
        claim_time = random_date(14, 0)
        
        # Fraud score - lower for approved/paid, higher for rejected
        if status == ClaimStatus.REJECTED:
            fraud_score = round(random.uniform(0.6, 0.95), 2)
        else:
            fraud_score = round(random.uniform(0.0, 0.3), 2)
        
        ai_decisions = {
            TriggerType.RAIN: [
                "Claim verified. Weather data confirms heavy rainfall in zone.",
                "Heavy rain alert validated via OpenWeatherMap. Payout approved.",
                "Rainfall exceeded 15mm/hr threshold. Auto-approved.",
            ],
            TriggerType.TRAFFIC: [
                "Parametric trigger validated. Traffic congestion exceeded threshold.",
                "Traffic index above 60% confirmed via TomTom API.",
                "Severe traffic jam detected. Income loss verified.",
            ],
            TriggerType.SURGE: [
                "Automatic approval. All conditions met for surge payout.",
                "Platform surge detected. Delivery demand spike confirmed.",
                "Surge multiplier validated. Compensation approved.",
            ],
            TriggerType.ROAD_DISRUPTION: [
                "Claim approved after AI verification of incident reports.",
                "Road disruption confirmed via NewsAPI + Gemini analysis.",
                "Local incident verified. Zone activity dropped significantly.",
            ],
        }
        
        ai_decision = random.choice(ai_decisions.get(trigger_type, ["Claim verified via AI agent consensus."]))
        
        claim = Claim(
            id=str(uuid.uuid4()),
            policy_id=policy.id,
            rider_id=rider.id,
            trigger_type=trigger_type,
            trigger_value=trigger_event.value,
            threshold=trigger_event.threshold,
            amount=amount,
            status=status,
            fraud_score=fraud_score,
            ai_decision=ai_decision if status in [ClaimStatus.APPROVED, ClaimStatus.PAID] else None,
            tx_hash=f"0x{uuid.uuid4().hex}" if status == ClaimStatus.PAID else None,
            trigger_event_id=trigger_event.id,
            created_at=claim_time,
            processed_at=claim_time + timedelta(minutes=random.randint(1, 30)) if status not in [ClaimStatus.PENDING] else None
        )
        session.add(claim)
        claims.append(claim)
    
    await session.flush()
    print(f"   Created {len(claims)} claims")
    return claims


async def seed_transactions(session: AsyncSession, claims: list):
    """Seed blockchain transactions"""
    transactions = []
    
    # Transactions for paid claims
    paid_claims = [c for c in claims if c.status == ClaimStatus.PAID]
    
    for claim in paid_claims:
        tx = Transaction(
            id=str(uuid.uuid4()),
            claim_id=claim.id,
            tx_type="claim_paid",
            tx_hash=claim.tx_hash or f"0x{uuid.uuid4().hex}",
            from_address="0x742d35Cc6634C0532925a3b844Bc9e7595f2bD78",  # Platform wallet
            to_address=f"0x{uuid.uuid4().hex[:40]}",  # Rider wallet (simulated)
            amount=claim.amount,
            gas_used=round(random.uniform(21000, 50000), 0),
            status="confirmed",
            created_at=claim.processed_at or claim.created_at,
            confirmed_at=claim.processed_at + timedelta(seconds=random.randint(10, 60)) if claim.processed_at else None
        )
        session.add(tx)
        transactions.append(tx)
    
    # Some policy creation transactions
    for _ in range(20):
        tx = Transaction(
            id=str(uuid.uuid4()),
            claim_id=None,
            tx_type="policy_created",
            tx_hash=f"0x{uuid.uuid4().hex}",
            from_address=f"0x{uuid.uuid4().hex[:40]}",
            to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f2bD78",
            amount=random.choice([99, 199]),
            gas_used=round(random.uniform(21000, 35000), 0),
            status="confirmed",
            created_at=random_date(30, 0),
            confirmed_at=random_date(30, 0)
        )
        session.add(tx)
        transactions.append(tx)
    
    await session.flush()
    print(f"   Created {len(transactions)} transactions")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("    Auxilia Database Seeder")
    print("=" * 50 + "\n")
    asyncio.run(seed_database())
