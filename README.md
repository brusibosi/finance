# AleTrader - Algorithmic Trading System

**Version**: 2.0
**Last Updated**: 2025-10-22
**Purpose**: Multi-strategy algorithmic trading platform for systematic trading workflows

## 🎯 CRITICAL RULE: Enforce SOLID & DRY as the main rule

**All code must strictly adhere to SOLID principles (Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion) and DRY (Don't Repeat Yourself). This is the primary architectural mandate. Every design decision, refactoring, and code change must prioritize SOLID & DRY compliance above all else, except capital safety.**

## ⚠️ IMPORTANT: Import Contract Enforcement

**This repository enforces a mandatory import contract. All imports from AMS and ES MUST use the `aletrader.*` namespace.**

### Required Import Patterns

```python
# ✅ CORRECT - Execution Service (ES)
from aletrader.es.api import (
    process_backtest_step,
    submit_orders_batch,
    get_journal,
    reset_simulator,
)

# ✅ CORRECT - Account Management Service (AMS)
from aletrader.ams.api import (
    AccountManagementFacade,
    create_ams,
    create_account_management_facade,
    get_db_session_factory,
)

# ❌ FORBIDDEN - Old import patterns
from src.execution_service import process_backtest_step
from accountmanagementservice.src.orchestration.common.factories import create_ams
from executionservice.src.execution_service import process_backtest_step
```

**Failure to comply will result in PR rejection.** See `IMPORT_CONTRACT_ENFORCEMENT_STATUS.md` in the repository root for details.

---

## Table of Contents

1. [What is AleTrader?](#what-is-aletrader)
2. [System Architecture](#system-architecture)
3. [Quick Start](#quick-start)
4. [Three Main Workflows](#three-main-workflows)
5. [Key Concepts](#key-concepts)
6. [Configuration](#configuration)
7. [Detailed Documentation](#detailed-documentation)
8. [Development](#development)

---

## What is AleTrader?

AleTrader is a **Python-based algorithmic trading system** that automates the discovery, analysis, and selection of trading opportunities across global stock markets. It connects to Interactive Brokers (IBKR) to fetch market data, evaluate trading strategies, and generate actionable trading signals.

**Think of it as three connected modules:**

```
┌──────────────────────────────────────────────────────────────────────┐
│                        ALETRADER SYSTEM                              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────┐      ┌────────────────┐      ┌───────────────┐ │
│  │   SCREENER     │  →   │     TRADER     │  →   │   ADMIN UI    │ │
│  │                │      │                │      │               │ │
│  │ Find tradeable │      │ Analyze stocks │      │ Configure &   │ │
│  │ stocks and     │      │ with trading   │      │ Monitor the   │ │
│  │ fetch their    │      │ strategies     │      │ system        │ │
│  │ price history  │      │                │      │               │ │
│  └────────────────┘      └────────────────┘      └───────────────┘ │
│                                                                      │
│  Commands:                Commands:                Command:         │
│  - python                 - python                 - python         │
│    alescreener.py           aletrader.py             aleadmin.py    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**For non-technical users**: AleTrader helps you systematically find and evaluate trading opportunities. Instead of manually screening thousands of stocks, it automatically:
1. Discovers which stocks you can trade
2. Fetches their historical prices
3. Applies your trading rules to identify the best opportunities
4. Ranks them by quality so you can focus on the top picks

---

## System Architecture

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ALETRADER DATA FLOW                             │
└─────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────┐
                    │  IBKR Broker (TWS    │
                    │  or IB Gateway)      │
                    └──────────┬───────────┘
                               │
                               │ Live market connection
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 1: SCREENER - Discover Tradeable Universe                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Input:  Market codes (LSE, NASDAQ, XETRA, etc.)                    │
│           ↓                                                          │
│  1. Discover tickers from sources (Wikipedia, IBKR scanner)          │
│  2. Validate tickers exist on IBKR (qualifyContracts)               │
│  3. Fetch historical OHLCV data (up to 3 years)                     │
│  4. Save to database (ticker_universe + historical_data tables)      │
│           ↓                                                          │
│  Output: Database with tradeable stocks + price history              │
│                                                                       │
│  📁 Database: runtime/aletrader.db                                   │
│     - ticker_universe (960 tickers)                                  │
│     - historical_data (714,000+ price bars)                          │
│                                                                       │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             │ Ticker universe ready
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 2: TRADER - Analyze & Generate Signals                         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  PHASE 2A: Strategy Scanning (Scanner Orchestrator)           │  │
│  ├────────────────────────────────────────────────────────────────┤  │
│  │  For each active strategy:                                     │  │
│  │    1. Load tickers from ticker_universe                        │  │
│  │    2. Calculate indicators (RSI, MACD, EMA, ATR, ADX, etc.)    │  │
│  │    3. Apply strategy filters (price, volume, trend, momentum)  │  │
│  │    4. Score tickers (0-100 based on indicator strength)        │  │
│  │    5. Save results to scan_results table                       │  │
│  │                                                                 │  │
│  │  Example: 960 tickers → 127 passing filters → scores 0-89      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                             │                                          │
│                             ▼                                          │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  PHASE 2B: Strategy Aggregation                               │  │
│  ├────────────────────────────────────────────────────────────────┤  │
│  │  For each trading sub-account:                                 │  │
│  │    1. Load multiple strategy results                           │  │
│  │    2. Combine using policy (Union/Intersection/Weighted)       │  │
│  │    3. Generate ranked watchlist                                │  │
│  │    4. Save to watchlist_items table                            │  │
│  │                                                                 │  │
│  │  Example: 3 strategies → Union → 187 candidates → Top 20       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                             │                                          │
│                             ▼                                          │
│  Output: Ranked list of trading opportunities with BUY signals       │
│                                                                       │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             │ Trading signals ready
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 3: ADMIN UI - Configure, Monitor & Backtest                    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Web Interface (http://127.0.0.1:8000/admin)                        │
│    - Configure strategies, indicators, filters                       │
│    - View scan results and watchlists                                │
│    - Run backtests on historical data                                │
│    - Manage system settings                                          │
│    - Monitor system health                                           │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

```
┌────────────────────────────────────────────────────────────────────┐
│  TECHNOLOGY STACK                                                  │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Language:       Python 3.10.12                                    │
│  Database:       SQLite 3.x (runtime/aletrader.db)                │
│  ORM:            SQLModel 0.0.16                                   │
│  Web Framework:  FastAPI 0.104.0+ (Admin UI)                      │
│  Admin UI:       SQLAdmin 0.16.0+ (Database management)           │
│  Broker API:     ib_async 2.0.1 (Interactive Brokers)             │
│  Data Analysis:  pandas 2.1.4, numpy 1.26.4                       │
│  Indicators:     TA-Lib 0.4.28 (Technical indicators)             │
│  Market Data:    yfinance 0.2.40 (backup provider)                │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

1. **Python 3.10.12** or higher
2. **Interactive Brokers Gateway or TWS** (for live/paper trading)
3. **WSL or native Linux** (recommended) or Windows

### Installation

```bash
# Navigate to project directory
cd /path/to/teamB

# Install dependencies
pip install -r requirements.txt

# Verify IBKR connection
# - Start IB Gateway on port 4002 (paper) or 7497 (TWS paper)
# - Ensure API connections enabled in settings
```

### First Run - Complete Workflow

```bash
# Step 1: Discover tradeable stocks and fetch price history
python alescreener.py

# Output: Creates database with ~960 tickers and historical prices
# Runtime: ~2-5 minutes (incremental updates are faster)

# Step 2: Run trading strategies and generate signals
python aletrader.py run

# Output: Scans all strategies, combines results, generates watchlists
# Runtime: ~30-60 seconds for 960 tickers with multi-threading

# Step 3: Launch admin UI to view results
python aleadmin.py

# Output: Web interface at http://127.0.0.1:8000/admin
# View scan results, watchlists, configure strategies
```

---

## Three Main Workflows

### 1. Screener Workflow (Ticker Discovery)

**Purpose**: Build your tradeable universe by discovering stocks and fetching their price history.

**Command**: `python alescreener.py`

**What it does**:
1. Connects to Interactive Brokers
2. Discovers tickers from multiple sources (Wikipedia, IBKR scanner)
3. Validates each ticker exists on IBKR broker
4. Fetches up to 3 years of historical OHLCV data
5. Saves to database for analysis

**Key Features**:
- **Incremental Updates**: Only fetches missing data on subsequent runs (90% faster)
- **Multi-Market Support**: LSE, NASDAQ, XETRA, Euronext, and more
- **Smart Caching**: Skips recently-fetched tickers (15-minute cache)
- **Exchange Hours Awareness**: Doesn't re-fetch during closed market hours
- **Automatic Fallback**: Tries multiple date ranges to maximize data capture

**Output**:
```
Database: C:\Users\alebo\trading-data\aletrader.db
  ✓ ticker_universe: 960 tradeable stocks
  ✓ historical_data: 714,000+ price bars
```

**See detailed documentation**: [readme_screener.md](readme_screener.md)

---

### 2. Trader Workflow (Strategy Execution)

**Purpose**: Analyze your stock universe with trading strategies and generate ranked buy signals.

**Command**: `python aletrader.py run`

**What it does**:
1. Loads active trading strategies from database
2. Scans all tickers with each strategy (parallel processing)
3. Calculates technical indicators (RSI, MACD, EMA, etc.)
4. Applies filters (price range, volume, trend alignment)
5. Scores each stock (0-100) based on indicator strength
6. Combines multi-strategy results per trading account
7. Generates ranked watchlists with top opportunities

**Available Commands**:
```bash
python aletrader.py run          # Full automatic workflow
python aletrader.py agg-scan     # Run strategy scans only
python aletrader.py agg-combine  # Combine scan results only
python aletrader.py trader       # Execute trading logic only
```

**Key Features**:
- **Multi-Strategy Support**: Run multiple strategies simultaneously
- **Multi-Threading**: Process 960 tickers in ~30 seconds (12 threads)
- **Strategy Aggregation**: Combine results with Union/Intersection/Weighted policies
- **Multi-Account**: Separate watchlists for different trading accounts
- **Database-Driven**: All configuration stored in database (no code changes needed)

**Output**:
```
Scan Results:
  ✓ scan_runs: Metadata for each strategy execution
  ✓ scan_results: Per-ticker scores and indicator values
  ✓ combiner_results: Aggregated multi-strategy rankings
  ✓ watchlist_items: Final BUY signals ready for execution
```

**See detailed documentation**: [readme_trader.md](readme_trader.md)

---

### 3. Admin UI Workflow (Configuration & Monitoring)

**Purpose**: Configure strategies, view results, run backtests, and monitor system health.

**Command**: `python aleadmin.py`

**What it does**:
1. Launches FastAPI web server with SQLAdmin interface
2. Provides database management for all AleTrader tables
3. Enables strategy configuration (indicators, filters, weights)
4. Displays scan results and watchlists
5. Runs historical backtests
6. Manages system settings and configuration

**Access**: `http://127.0.0.1:8000/admin`

**Key Features**:
- **Strategy Builder**: Configure strategies without coding
- **Scan Explorer**: View detailed scan results with drill-down
- **Watchlist Viewer**: See ranked trading opportunities
- **Backtest Runner**: Validate strategies on historical data
- **System Settings**: Centralized configuration management
- **Dark Theme**: Professional WCAG 2.1 AA compliant UI

**Available Views**:
```
http://127.0.0.1:8000/admin/strategy/list         # Manage strategies
http://127.0.0.1:8000/admin/scan-run/list         # View scan executions
http://127.0.0.1:8000/admin/scan-result/list      # Analyze scan results
http://127.0.0.1:8000/admin/watchlist-item/list   # See buy signals
http://127.0.0.1:8000/admin/backtest-run/list     # Review backtests
http://127.0.0.1:8000/admin/system-setting/list   # Configure system
```

**See detailed documentation**: [readme_admin.md](readme_admin.md)

---

## Key Concepts

### For Non-Technical Users

**Q: What is a "ticker"?**
A: A ticker is a stock symbol (e.g., AAPL for Apple, VOD.L for Vodafone on London Stock Exchange).

**Q: What is "historical data"?**
A: Price history showing how a stock traded in the past (Open, High, Low, Close prices + Volume).

**Q: What is a "strategy"?**
A: A set of rules to identify good trading opportunities (e.g., "buy stocks trending up with strong momentum").

**Q: What is a "scan"?**
A: The process of checking all stocks against your strategy rules to find matches.

**Q: What is a "watchlist"?**
A: Your shortlist of stocks that passed all strategy filters and are ranked by quality.

**Q: What is a "backtest"?**
A: Testing your strategy on historical data to see how it would have performed in the past.

### Technical Concepts

**Screener vs Scanner**:
- **Screener** (alescreener.py): Data acquisition layer - discovers tickers and fetches historical prices
- **Scanner** (inside aletrader.py): Analysis layer - evaluates tickers with trading strategies

**Strategy Scoring**:
- Each strategy calculates a score (0-100) for every ticker
- Score reflects indicator strength (higher = better setup)
- Scores can be combined across multiple strategies

**Strategy Aggregation Policies**:
- **Union**: Include if ANY strategy selects (more opportunities, less strict)
- **Intersection**: Include if ALL strategies select (fewer opportunities, more conservative)
- **Weighted**: Combine scores with custom weights per strategy (balanced approach)

**Database Schema**:
```
Key Tables:
  ticker_universe     → All tradeable stocks discovered by screener
  historical_data     → OHLCV price bars for each ticker
  strategies          → Strategy definitions (indicators + filters + scoring)
  scan_runs           → Metadata for each strategy execution
  scan_results        → Per-ticker results for each scan
  combiner_results    → Aggregated multi-strategy rankings
  watchlist_items     → Final BUY/WAIT/SKIP signals
  backtest_runs       → Historical validation runs
  backtest_trades     → Simulated trades from backtests
  system_settings     → Application configuration (centralized)
```

---

## Configuration

### Database-Only Configuration (Feature 031)

**All configuration is stored in the database** in the `system_settings` table.

**Key Settings**:
```
Database: runtime/aletrader.db
Table: system_settings

Key configuration areas:
  - Screener settings (markets, data fetch parameters)
  - Scanner runtime (thread count, batch sizes)
  - Strategy parameters (indicator periods, filter thresholds)
  - Broker connections (hosts, ports, credentials)
  - Logging (paths, levels, formats)
```

**Manage via Admin UI**:
```bash
python aleadmin.py
# Navigate to: http://127.0.0.1:8000/admin/system-setting/list
# Edit settings directly in the web interface
# Changes take effect immediately (hot reload)
```

**Legacy JSON Files** (Archived):
- Old JSON configuration files moved to `configs/_legacy/`
- Rollback instructions available in `configs/_legacy/README.md`
- No longer used by the application

---

## Detailed Documentation

**Main Components**:
- **[Screener Documentation](readme_screener.md)** - Ticker discovery, validation, data fetching
- **[Trader Documentation](readme_trader.md)** - Strategy scanning, aggregation, signal generation
- **[Admin UI Documentation](readme_admin.md)** - Web interface, configuration, backtesting

**Additional Resources** (in MD/ folder):
- `MD/CLAUDE.md` - Development guidelines and architecture principles
- `MD/CHANGELOG.md` - Version history and feature releases
- `MD/QUICKSTART.md` - Simplified getting started guide
- `MD/WORKFLOW_GUIDE.md` - Step-by-step workflow instructions
- `MD/CLI_ARCHITECTURE.md` - Command-line interface details

---

## Development

### Project Structure

```
teamB/
├── aletrader.py           # Main trader CLI entry point
├── alescreener.py         # Screener CLI entry point
├── aleadmin.py            # Admin UI launcher
├── src/
│   ├── core/              # Core infrastructure (DB, config, logging)
│   ├── screener/          # Ticker discovery and validation
│   ├── aggregator/        # Strategy scanning orchestration
│   ├── trader/            # Trade execution and watchlist generation
│   ├── trader_manager/    # Multi-account trading orchestration
│   ├── strategy/          # Strategy framework and models
│   ├── indicators/        # Technical indicator implementations
│   ├── filters/           # Strategy filter implementations
│   ├── providers/         # Market data providers (IBKR, Yahoo Finance)
│   ├── brokers/           # Broker adapters (IBKR, Paper trading)
│   ├── webconsole_v2/     # FastAPI Admin UI
│   ├── common/            # Shared models and utilities
│   └── utils/             # Helper functions and utilities
├── runtime/
│   └── aletrader.db       # Main SQLite database
├── configs/
│   └── _legacy/           # Archived JSON configuration files
├── tests/                 # Test suite
├── MD/                    # Documentation archive
└── README.md              # This file
```

### Development Guidelines

**Code Style**:
- Python 3.10.12+ with type hints
- Black formatter (auto-formatting)
- Ruff linter (code quality)
- Follow PEP 8 conventions

**Database Access Pattern** (WSL Native):
```python
from src.core.session import DatabaseManager

# ALWAYS use DatabaseManager - NEVER use sqlite3.connect() directly!
db_manager = DatabaseManager("runtime/aletrader.db")
with db_manager.get_session() as session:
    # Your queries here
    # Connection auto-closes when exiting 'with' block
```

**Running Tests**:
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/screener/test_screener.py

# Run with coverage
pytest --cov=src --cov-report=html
```

**Code Quality**:
```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy src/
```

### Contributing

1. Create a feature branch from `main`
2. Make changes following code style guidelines
3. Add tests for new functionality
4. Update documentation
5. Submit pull request

---

## Support

**Issues**: [GitHub Issues](https://github.com/anthropics/aletrader/issues)
**Documentation**: See `readme_*.md` files for detailed component documentation
**Configuration**: Use Admin UI at `http://127.0.0.1:8000/admin`

---

**Version History**:
- **v2.0 (2025-10-22)**: Config source unification, database-only configuration
- **v1.7 (2025-10-21)**: Multi-strategy aggregation, backtest simulator
- **v1.6 (2025-10-20)**: Admin dark theme, component library
- **v1.5 (2025-10-19)**: Strategy aggregation MVP
- **v1.4 (2025-10-18)**: Multi-account trading support

See [MD/CHANGELOG.md](MD/CHANGELOG.md) for complete version history.
