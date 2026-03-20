# Auxilia — Phase 1: The Idea Document

## 1. Requirement & Persona-Based Scenarios
**Problem:** Gig workers strictly depend on daily output to survive. Sudden disruptions—severe weather, curfews, or sudden localized strikes—strip their income unceremoniously, and traditional insurance models are too slow, manual, and broad to cover these micro-shocks.

**Persona Scenarios:**
- **Persona A (Q-Commerce/Food Delivery — e.g., Zepto/Swiggy Rider):** Highly sensitive to extreme rain and localized flooding. A 2-hour downpour in their specific zone means unsafe riding conditions and zero earnings for peak hours.
- **Persona B (Ride-Hailing — e.g., Uber/Ola Driver):** Sensitive to curfews, localized strikes, or road blockades. If their primary zone is locked down, they lose their entire daily target.

**Workflow:**
1. **Onboarding:** Rider signs up via voice/text, selects their primary zone and persona.
2. **Policy Creation:** An AI risk model generates a dynamic weekly premium. The rider pays, and the policy hash is logged on the blockchain.
3. **Monitoring:** Autonomous agents monitor free APIs (Weather, News) for their specific zone in real-time.
4. **Trigger & Consensus:** If a disruption occurs, multiple agents vote. If 2-of-3 agents agree (Consensus) and fraud checks pass, the claim is auto-approved.
5. **Instant Payout:** A payout is sent instantly via UPI (Razorpay) with zero human intervention.

## 2. Weekly Premium Model & Parametric Triggers
**Weekly Premium Model:**
Rather than a fixed monthly cost, we operate on a hyper-local, weekly rolling model. The base premium is extremely low (e.g., ₹99/week), adjusted dynamically by a `Zone Risk Multiplier` (0.8x to 1.3x) based on the zone's historical volatility and current seasonal forecasts (e.g., higher during monsoon).

**Parametric Triggers:**
These are immutable thresholds that automatically trigger a claim evaluation:
1. **Heavy Rain:** > 15mm/hr *[Source: OpenWeatherMap]*
2. **Extreme Heat:** > 42°C *[Source: OpenWeatherMap]*
3. **Severe Air Pollution:** AQI > 300 *[Source: OpenWeatherMap]*
4. **Curfews/Strikes:** Keyword matches for specific zones *[Source: NewsAPI]*
5. **Zone Activity Drop:** Active riders drop below 30% of the baseline *[Source: Internal App DB]*

**Platform Choice (Mobile/Web Responsive):**
We chose a **Responsive Web App (Next.js/PWA)** for the initial phase. Over 95% of gig workers use budget Android devices with limited storage. Asking them to download another native app creates friction. A progressive web app allows instant onboarding via browser (zero install) while opening the door to native Firebase Push Notifications or WhatsApp integration later.

## 3. AI/ML Integration
AI and Autonomous Agents are the core engine of Auxilia:
- **Premium Calculation (RiskAgent):** An XGBoost Machine Learning model trains on historical zone disruption data, weather seasonality, and persona type to predict the probability of a disruption in the upcoming week. This generates the dynamic risk multiplier.
- **Trigger Monitoring (TriggerAgent):** Asynchronous Python agents continuously poll data sources without human intervention.
- **Fraud Detection (FraudAgent):** Executes 3 parallel checks via `asyncio`: 
  1. Validates rider's GPS zone footprint.
  2. Prevents duplicate claims for the same event.
  3. Corroborates the disruption event against network swarm activity (verifying if other riders also went offline).
- **Agent Consensus:** Uses an LLM-inspired multi-agent architecture where agents must achieve a 2-of-3 consensus to trigger a payout, reducing false positives.

## 4. Tech Stack & Development Plan
**Tech Stack:**
- **Frontend Layer:** Next.js (React), ethers.js, Tailwind/Vanilla CSS
- **Backend & AI Layer:** FastAPI (Python), asyncio for identical parallel agent execution, XGBoost + scikit-learn for Risk Modeling.
- **Data & Storage Layer:** SQLite/PostgreSQL, OpenWeatherMap, NewsAPI
- **Blockchain Layer:** Local Hardhat Testnet (Solidity: ClaimLedger.sol) for tamper-proof audit trails.
- **Payments:** Razorpay Sandbox

**Development Plan:**
- **Phase 1 (Completed):** Ideation, Persona mapping, Architectural decisions, and UX Design.
- **Phase 2 (Completed):** Scaffold full-stack app, implemented Next.js frontend pages (Onboard, Dashboard, Claims, Heatmap).
- **Phase 3 (Completed):** Developed FastAPI multi-agent backend, trained XGBoost model, deployed Hardhat smart contract.
- **Phase 4 (Next):** Live test API endpoints, generate demonstration video, and host repository on GitHub.

---

## 5. Prototype Setup Instructions
*(For evaluators reviewing the prototype code)*

1. **Environment:** Copy `.env.example` to `.env`.
2. **ML Model:** Navigate to `/ml`, run `pip install -r ../backend/requirements.txt`, then `python train_model.py`.
3. **Blockchain:** Navigate to `/blockchain`, run `npm install`, then start the node `npx hardhat node` and deploy the contract `npx hardhat run scripts/deploy.js --network localhost`.
4. **Run Application:** At the root directory, run `docker-compose up --build`. Access the frontend at `http://localhost:3000`.

## 6. Demonstration Video
*(Please insert the 2-minute video link here before final submission)*
- **Link:** `[Insert Public Video Link Here]`
