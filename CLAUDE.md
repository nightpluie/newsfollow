# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**newsfollow** is a news monitoring system that:
1. Crawls multiple Taiwan news websites (UDN, TVBS, 中時, 三立)
2. Detects potential major events through clustering and scoring
3. Generates draft articles using LLM
4. Integrates with ETtoday publishing workflow

**Two-tier architecture:**
- **CLI tool** (`main.py`) - Core crawler and event detection engine
- **Web dashboard** (`news_dashboard.py`) - Flask UI for news analysis and AI rewriting

## Common Commands

### Development Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp config.example.yaml config.yaml
```

### CLI Tool (main.py)

```bash
# Run one monitoring cycle (crawl + detect events)
python3 main.py run-once

# Run one cycle and publish drafts
python3 main.py run-once --publish

# Run continuous monitoring loop
python3 main.py loop

# List recent detected events
python3 main.py list-events --limit 30

# Custom config file
python3 main.py --config custom.yaml run-once

# Debug logging
python3 main.py --log-level DEBUG run-once
```

### Web Dashboard

```bash
# Start Flask server
python news_dashboard.py
# Access at http://localhost:8080

# Stop server
pkill -f "news_dashboard.py"
```

### Testing

```bash
# Crawler health check
python3 tests/test_crawler_health.py

# LLM integration test (requires OPENAI_API_KEY)
python3 tests/test_llm_integration.py

# Hybrid similarity test
python3 tests/test_hybrid.py

# Run all tests
python3 -m pytest tests/
```

### Environment Variables

```bash
# Required for LLM features
export OPENAI_API_KEY='your_key'
export OPENAI_MODEL='gpt-4o-mini'
export OPENAI_BASE_URL='https://api.openai.com/v1/chat/completions'
```

## High-Level Architecture

### Core Data Flow

```
[Web Crawling] → [Signal Extraction] → [Deduplication] → [Event Clustering]
    → [Scoring & Filtering] → [Draft Generation] → [Publishing]
```

### Key Concepts

**Signal**: A single news item extracted from a webpage
- Contains: title, url, source, section, weight, timestamp
- Represents raw data before processing

**Event**: A cluster of similar signals from multiple sources
- Formed when signals have similarity ≥ threshold (default 0.74)
- Scored based on: source count, weight, section type, keywords
- Only events with score ≥ threshold (default 11) are kept

**Draft**: LLM-generated article for a high-scoring event
- Created by `DraftGenerator` using OpenAI-compatible API
- Falls back to template if LLM unavailable

### Critical Classes

**MonitorApp** (`main.py`)
- Main orchestrator class
- Coordinates: crawler → detector → generator → publisher
- Manages one monitoring cycle or continuous loop

**Repository** (`main.py`)
- SQLite database abstraction
- Tables: `signals`, `events`, `drafts`, `publish_logs`
- Handles persistence and querying

**RequestsCrawler** (`main.py`)
- Implements web crawling using requests + BeautifulSoup
- Config-driven: reads `config.yaml` for sources, selectors, weights
- Returns list of Signal objects

**DraftGenerator** (`main.py`)
- LLM integration for generating article drafts
- Configurable via `config.yaml` (model, temperature, max_tokens)
- Has fallback mode when LLM disabled

**PublisherStub / PublisherCommandAdapter** (`main.py`)
- Publish adapter pattern for ETtoday integration
- `stub`: logs only (for testing)
- `command`: executes shell command with JSON stdin/stdout

## Title Similarity Algorithm

Located in `main.py`, this is central to event detection.

### Multi-metric Approach

The `title_similarity()` function combines 4 algorithms:

1. **Jaccard Similarity** (35% weight)
   - Measures word overlap between titles
   - Uses Jieba Chinese word segmentation

2. **Cosine Similarity** (30% weight)
   - Vector space similarity using TF-IDF-like weighting
   - Handles word frequency differences

3. **Longest Common Substring (LCS)** (25% weight)
   - Finds longest matching character sequence
   - Good for detecting similar phrasing

4. **Number Matching** (10% weight)
   - Extracts numbers from titles and checks overlap
   - Ensures numeric facts match (dates, amounts, etc.)

### Entity Enhancement

The algorithm includes intelligent entity recognition:
- Maps "台積電" ↔ "TSMC"
- Maps "鴻海" ↔ "Foxconn"
- Adds both forms to token list for better matching

### Thresholds

- **Similarity threshold**: 0.5 (titles with score ≥ 0.5 are considered same news)
- **Cluster similarity**: 0.74 in `config.yaml` (for event formation)
- See `docs/SIMILARITY_ANALYSIS.md` for detailed analysis

## Configuration (config.yaml)

### Key Parameters

```yaml
interval_seconds: 180          # Loop mode interval
event_threshold: 11            # Minimum score to create event
cluster_similarity: 0.74       # Title similarity for clustering
crawler_backend: requests      # requests | openclaw (openclaw is stub)

llm:
  enabled: true
  provider: openai
  model: gpt-4o-mini
  temperature: 0.4
  max_tokens: 1200
```

### Adding New News Sources

Edit `config.yaml` and add to `sources` array:

```yaml
sources:
  - source_id: example_media
    source_name: Example Media
    domain_contains: example.com
    sections:
      - section_id: homepage
        url: https://example.com/news
        weight: 5                    # Higher weight = more important
        max_items: 25                # Max signals to extract
        selectors:                   # CSS selectors (tries in order)
          - "a.article-title"
          - "h2 a"
          - "main a[href*='/news/']"
```

**Weight guidance:**
- `6`: Breaking news, marquee sections
- `5`: Homepage, main sections
- `4`: Hot/popular sections

## Database Schema

SQLite database at `./newsfollow.db` (configurable):

**signals**: Raw crawled items
- `id`, `url`, `title`, `normalized_title`, `source`, `section`, `weight`, `crawled_at`

**events**: Clustered high-impact news
- `event_key` (hash), `canonical_title`, `score`, `source_count`, `signal_count`, `first_seen`, `last_seen`

**drafts**: LLM-generated articles
- `event_key`, `title`, `body`, `image_prompt`, `generated_at`, `generator_info`

**publish_logs**: Publishing history
- `event_key`, `draft_id`, `status`, `external_id`, `message`, `published_at`

## Testing Strategy

### Current Test Files

- `test_crawler_health.py` - Validates crawler can fetch from all sources
- `test_llm_integration.py` - Tests LLM draft generation
- `test_hybrid.py` - Tests hybrid similarity checker (algorithm + LLM)
- `test_similarity_case.py` - Test specific similarity scenarios
- `test_ettoday_crawl.py` - Validates ETtoday crawling

### Running Specific Tests

```bash
# Test single source crawling
python3 tests/test_crawler_health.py

# Check event detection
python3 main.py run-once
sqlite3 newsfollow.db "SELECT COUNT(*) FROM signals;"  # Should be > 50
sqlite3 newsfollow.db "SELECT COUNT(*) FROM events;"   # Depends on news

# Validate similarity scoring
python3 tests/test_similarity_case.py
```

## Known Limitations

### Intentional Stubs

These features are reserved for future implementation:

1. **OpenClaw crawler backend** (`crawler_backend: openclaw`)
   - Currently warns and falls back to `requests`
   - Class `OpenClawCrawlerStub` is placeholder

2. **Mobile push monitoring** (`mobile_push.enabled`)
   - Class `MobilePushMonitorStub` is placeholder
   - For future Android notification monitoring

3. **Direct ETtoday integration**
   - Use `publisher.mode: command` to bridge with external script
   - See `scripts/publisher_command_example.py`

### CSS Selector Fragility

Web crawlers depend on CSS selectors in `config.yaml`. When source websites update:
- Selectors may stop working
- Multiple fallback selectors help (tries each in order)
- Monitor crawler success rate in logs

**Recovery approach:**
- Inspect HTML: `curl URL | grep -A 5 "news title"`
- Test new selectors in browser DevTools
- Update `config.yaml` with new selectors
- Run `python3 tests/test_crawler_health.py` to verify

## Important Files

**Core application:**
- `main.py` (1319 lines) - CLI tool, crawler, event detection
- `news_dashboard.py` (691 lines) - Flask web application
- `config.yaml` - Configuration for sources, LLM, publisher

**Algorithms:**
- `improved_similarity.py` - Enhanced similarity algorithm
- `hybrid_similarity.py` - Hybrid checker (algorithm + LLM)
- `news_importance.py` - News importance scoring

**Utilities:**
- `cache_manager.py` - File-based cache (5min TTL)

**Documentation:**
- `docs/CLAUDE.md` - Detailed documentation of web dashboard features
- `docs/DESIGN_REVIEW.md` - Architecture critique and improvement suggestions
- `docs/VALIDATION_CHECKLIST.md` - Testing and validation guide

## Web Dashboard Features

See `docs/CLAUDE.md` for comprehensive documentation of:
- News analysis workflow
- AI rewriting with Claude Skills
- Similarity checking and filtering
- Cache system and performance optimizations

The web dashboard (`news_dashboard.py`) provides:
- Visual interface for news monitoring
- AI-powered article rewriting (uses Claude Haiku 4.5 with custom skill)
- ETtoday comparison (finds missing news)
- Multi-source analysis and importance scoring

## Development Notes

### Code Organization

**main.py is intentionally large (1319 lines)**
- Contains complete monitoring pipeline in one file
- Classes are tightly coupled (Signal → Event → Draft flow)
- Splitting would require significant refactoring
- See `docs/DESIGN_REVIEW.md` for recommended module structure

### Virtual Environments

This project has multiple venv directories:
- `.venv/` - Primary virtual environment
- `venv/` - Backup (should use .venv)

Use `.venv` for consistency:
```bash
source .venv/bin/activate
```

### Performance Considerations

- First crawl: 12-15 seconds (parallel fetching of 5 sources)
- Cached crawl: 2-3 seconds (uses 5min cache)
- Similarity comparison: O(n²) complexity
- With 25 items/source × 5 sources = ~125 signals → ~8000 comparisons

## Deployment Notes

### Production Readiness

**✅ Suitable for:**
- Prototype/experimental deployment
- Small-scale monitoring (2-5 sources)
- Local development and testing

**⚠️ Needs improvement for production:**
- Add monitoring and alerting
- Implement selector health checks
- Add rate limiting for crawlers
- Consider async crawler for >10 sources
- Migrate to PostgreSQL for high-frequency monitoring

See `docs/DESIGN_REVIEW.md` for detailed production checklist.

### Environment Setup

**Required:**
- Python 3.8+
- SQLite (included with Python)

**Optional:**
- OpenAI API key (for LLM features)
- External publisher script (for ETtoday integration)

## Architecture Decisions

### Why Jieba for Chinese Segmentation?

Chinese text requires word segmentation (no spaces between words). Jieba is:
- Well-established library for Chinese NLP
- Good balance of accuracy and speed
- Large built-in dictionary
- Falls back to character-based if Jieba unavailable

### Why Multiple Similarity Metrics?

Single metric approaches have weaknesses:
- Jaccard alone: poor with word order
- Cosine alone: sensitive to title length
- LCS alone: misses semantic similarity

Combining 4 metrics with tuned weights achieves 87.5% accuracy.

### Why SQLite vs PostgreSQL?

**Current choice: SQLite**
- Simple deployment (single file)
- No separate database server
- Sufficient for prototype scale
- Easy backup and migration

**When to switch to PostgreSQL:**
- Monitoring frequency < 60 seconds
- More than 20 news sources
- Need for horizontal scaling
- Advanced time-series analysis

### Why Config-Driven Architecture?

All news sources defined in `config.yaml` (not code) because:
- Non-technical users can add sources
- No code changes needed for new media
- Easy A/B testing of selector strategies
- Source changes don't require deployment

## Related Resources

- **Quick start:** See `README.md`
- **Design review:** See `docs/DESIGN_REVIEW.md`
- **Validation guide:** See `docs/VALIDATION_CHECKLIST.md`
- **Dashboard docs:** See `docs/CLAUDE.md`
- **Similarity analysis:** See `docs/SIMILARITY_ANALYSIS.md`
