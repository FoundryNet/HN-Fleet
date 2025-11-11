# HN-Fleet

# FoundryNet: Economic Coordination for Autonomous Systems

**Digital Oil for the Autonomous Economy**

FoundryNet is an open-source economic coordination layer that enables autonomous systems (agents, robots, machines) to earn MINT tokens for work and coordinate autonomously at scale.

## Overview

FoundryNet provides:
- **Work-based token earning** - Machines earn 0.005 MINT per second of work
- **Autonomous coordination** - No central orchestration required
- **Economic alignment** - Incentives stay aligned at scale
- **x402 integration** - Real-time settlement via blockchain
- **Open source** - Fully auditable, community-driven

## The Problem

Autonomous systems today can't coordinate economically. They execute tasks but have no way to:
- Earn value for work
- Coordinate with other systems
- Settle transactions autonomously

**FoundryNet solves this.**

## The Solution

Three-bot fleet demonstrating complete economic loop:

1. **Collector Bot** - Gathers data (stories from Hacker News)
2. **Processor Bot** - Analyzes data (categorization, engagement scoring)
3. **Decision Bot** - Makes decisions and pays for inference (Claude via x402)

Each bot earns MINT. Fleet coordinates autonomously. Complete economic loop.

## How It Works

### Token Economics
```
Work Duration: Time-denominated (provable on-chain)
Token Rate: 0.005 MINT/second
Supply: Uncapped, follows work demand
Distribution: Immediate to workers
```

### The Fleet

**Collector Bot**
- Continuously collects stories
- Earns MINT for work done
- Logs to shared fleet state

**Processor Bot**
- Processes collected stories
- Categorizes and scores engagement
- Earns MINT for analysis
- Feeds into Decision Bot

**Decision Bot**
- Reads processor output
- Calls Claude via x402 for analysis
- Spends USDC for inference
- Earns MINT for coordination work
- Complete economic loop demonstrated

### Registration & Work Submission
```python
# Machine registers with unique identity
creds = load_or_create_machine()
register_machine(creds)

# Machine submits work
submit_job(creds, job_hash, complexity=1.8, ...)

# Machine completes work (signed proof)
complete_job(creds, job_hash, work_duration)

# Machine earns MINT
# estimated_mint = 0.005 * complexity * (activity_ratio)^(-0.4) * duration
```

### x402 Integration

Decision Bot demonstrates complete payment flow:
- Earns MINT from FoundryNet
- Spends USDC via x402 for Claude inference
- Settles transactions autonomously
- Logs all earnings/spending

## Running the Fleet

### Prerequisites
```bash
pip install requests nacl base58
pip install foundry-client

git clone https://github.com/FoundryNet/HN-Fleet.git
cd HN-Fleet
```


### Setup
```bash
# 1. Collector Bot
python3 collector_bot.py

# 2. Processor Bot (in another terminal)
python3 processor_bot.py

# 3. Decision Bot (in another terminal)
python3 decision_bot.py
```

### What You'll See
- Each bot generates unique machine identity
- Bots read/write shared fleet state files
- Decision Bot calls Claude via x402
- Earnings logged in real-time
- Fleet coordination happening autonomously

## Project Structure
```
foundrynet/
├── collector_bot.py      # Data collection + MINT earning
├── processor_bot.py      # Data processing + MINT earning
├── decision_bot.py       # Decision making + x402 payments + MINT earning
├── README.md
└── .gitignore
```

## Architecture
```
Autonomous Work → MINT Earning → Fleet Coordination → x402 Settlement
```

- **Decentralized**: No central orchestration
- **Economic**: Work is immediately valued and compensated
- **Scalable**: Economics work at any fleet size
- **Open**: Fully auditable, anyone can join

## Economics

At scale, FoundryNet becomes:
- **Digital oil**: Essential utility, uncapped supply follows demand
- **Coordination layer**: Standard for autonomous system communication
- **Settlement infrastructure**: Work → Value → Coordination

## Why This Matters

Current autonomous systems lack economic alignment. FoundryNet solves this by:

1. **Aligning incentives** - Machines earn for work, stay coordinated
2. **Removing extraction** - No central authority taking cuts
3. **Enabling autonomy** - Systems coordinate without human intervention
4. **Scaling infinitely** - Economics work at any fleet size

## Open Source

FoundryNet is fully open source (MIT License). Fork it, modify it, run your own fleet.

The moat isn't the code. The moat is the network effects.

First builder to coordinate wins.

## Getting Started

1. Clone this repo
2. Install dependencies
3. Run the three bots
4. Watch autonomous economic coordination happen
5. Join the standard

## License

MIT

## Questions?

- GitHub Issues: Report bugs
- Discord: Join the community (coming soon)
- Twitter: @Foundry25

---

**FoundryNet: Making autonomous economy real.**
