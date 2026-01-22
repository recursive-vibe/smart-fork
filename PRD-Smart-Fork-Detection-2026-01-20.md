# Product Requirements Document: Smart Fork Detection for Claude Code

**Version:** 1.0  
**Date:** January 20, 2026  
**Product Type:** Claude Code MCP Server  
**Target Users:** Developers using Claude Code for software development

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Solution Overview](#solution-overview)
4. [Target Audience](#target-audience)
5. [Core Features & Functionality](#core-features--functionality)
6. [Technical Architecture](#technical-architecture)
7. [Data Models & Storage](#data-models--storage)
8. [User Experience & Interface](#user-experience--interface)
9. [Search & Ranking Algorithm](#search--ranking-algorithm)
10. [Security & Privacy](#security--privacy)
11. [Development Phases](#development-phases)
12. [Success Metrics](#success-metrics)
13. [Future Enhancements](#future-enhancements)
14. [Technical Challenges & Solutions](#technical-challenges--solutions)

---

## Executive Summary

Smart Fork Detection is an MCP (Model Context Protocol) server for Claude Code that solves the "context loss" problem in AI-assisted development. By maintaining a searchable vector database of all Claude Code session transcripts, it enables developers to seamlessly resume work from the most relevant previous conversation, eliminating the need to re-explain context and dramatically increasing productivity.

**Key Value Propositions:**
- Overcomes the 200,000 token context limit by intelligent session forking
- Achieves 100% success rate in finding relevant prior context (based on initial testing)
- Reduces context rebuilding time from minutes to seconds
- Enables rapid strategy testing by forking from a single proven baseline
- Transforms hundreds of isolated conversations into connected, reusable knowledge

---

## Problem Statement

### Current Pain Points

**Context Loss:**
Developers frequently need to implement features in existing projects but face a critical problem: each new Claude Code session starts with zero context. This forces developers to repeatedly explain project architecture, coding standards, previous decisions, and implementation details.

**Token Limit Constraints:**
Long conversations eventually hit the 200,000 token context window limit, forcing developers to start fresh sessions and lose valuable accumulated context.

**Knowledge Fragmentation:**
Developers accumulate hundreds or thousands of Claude Code sessions containing valuable problem-solving approaches, architectural decisions, and implementation patterns. This knowledge is trapped in isolated conversations and effectively wasted.

**Productivity Impact:**
- 10-30 minutes spent re-establishing context per new session
- Reduced quality when Claude lacks full project understanding
- Inability to efficiently test multiple approaches from the same baseline

---

## Solution Overview

Smart Fork Detection creates an "external long-term memory" for Claude Code by:

1. **Automatic Background Indexing:** Continuously capturing and embedding Claude Code session transcripts into a vector database
2. **On-Demand Semantic Search:** Allowing developers to find the most relevant past conversations for their current task
3. **Intelligent Session Forking:** Enabling seamless continuation from the optimal prior context point

### How It Works

```
User invokes: /fork-detect
         ↓
User describes: "I want to add real-time token usage cards to my dashboard"
         ↓
System embeds query → Searches vector DB → Calculates composite scores
         ↓
Returns: Top 5 ranked sessions with previews and scores
         ↓
User selects: Session #1 (81% match - "Real-time dashboard updates")
         ↓
System generates: Fork command
         ↓
User pastes command in new terminal → Seamlessly continues with full context
```

### Differentiation from Official Memory

Unlike Anthropic's planned "knowledge base" memory system (top-down structured memory), Smart Fork Detection provides:
- **Bottom-up context inheritance:** Finds actual past conversations, not curated knowledge
- **Episodic memory:** Working memory with strong context and timing
- **Immediate availability:** Works today with existing Claude Code sessions
- **Developer control:** Manual, on-demand tool rather than automatic memory

The two approaches are complementary and may integrate in the future.

---

## Target Audience

### Primary Users

**Individual Developers:**
- Using Claude Code for personal projects or professional development
- Have accumulated 50+ Claude Code sessions
- Work across multiple projects or features
- Value productivity and efficient workflows

**Technical Characteristics:**
- Comfortable with command-line tools
- Understand basic concepts of embeddings and semantic search
- May or may not have deep AI/ML knowledge

### Usage Scenarios

1. **Feature Implementation:** "I need to add OAuth to my app, and I built OAuth integration 3 months ago in a different project"
2. **Bug Investigation:** "I fixed a similar database connection issue before, but can't remember which session"
3. **Architecture Decisions:** "I discussed API design patterns extensively in a past session"
4. **Rapid Prototyping:** "I want to test 3 different UI approaches by forking from my base design session"
5. **Knowledge Retrieval:** "What was that clever solution Claude suggested for handling async operations?"

---

## Core Features & Functionality

### MVP Features (v1.0)

#### 1. `/fork-detect` Command
**User Story:** As a developer, I want to search my past Claude Code sessions so I can resume work with relevant context.

**Acceptance Criteria:**
- User types `/fork-detect` in Claude Code
- Claude prompts: "What would you like to do?"
- User provides natural language description
- System returns top 5 ranked results within 3 seconds
- Each result shows: session ID, date, topic, preview snippet, relevance score
- Results are ordered by composite score (highest to lowest)

**Example:**
```
> /fork-detect
Claude: What would you like to do?
User: Add authentication to my Next.js dashboard
[System searches and displays results]
```

#### 2. Background Session Indexing
**User Story:** As a developer, I want my sessions automatically indexed so I don't have to manually manage the database.

**Acceptance Criteria:**
- New sessions are automatically indexed when created
- Checkpoint indexing occurs every 10-20 message exchanges
- Final comprehensive indexing when session closes
- Failed/crashed sessions are still captured via checkpoints
- Indexing runs without impacting Claude Code performance
- Session registry tracks last sync timestamp

**Technical Requirements:**
- Monitor `~/.claude/projects/{project}/*.jsonl` files for changes
- Detect new sessions, updated sessions, and session closures
- Process sessions in chunks to avoid RAM exhaustion
- Batch size configurable based on system resources (default: 50 chunks)

#### 3. Interactive Selection Interface
**User Story:** As a developer, I want to review and select from multiple options so I can choose the most appropriate context.

**Acceptance Criteria:**
- Display exactly 5 options:
  1. Top ranked result (marked "Recommended")
  2. Second ranked result
  3. Third ranked result
  4. "None - start fresh" (start with no prior context)
  5. "Type something" (custom input)
- Each result shows: session ID, score, date, topic, preview
- "Chat about this" button available for discussion before selection
- Keyboard navigation: Enter to select, ↑/↓ to navigate, Esc to cancel
- Clear visual distinction for recommended result

#### 4. Dual Forking Mechanisms
**User Story:** As a developer, I want flexibility in how I fork sessions depending on my workflow needs.

**Acceptance Criteria:**
- **Method 1 - New Terminal Fork:**
  - Command: `claude --resume [session-id] --fork-session`
  - Creates fresh terminal with inherited context
  - Useful for clean start with prior knowledge
  
- **Method 2 - In-Session Fork:**
  - Command: `/fork [session-id] [path]`
  - Continues within current conversation
  - Useful for seamless continuation
  
- Both methods display session metadata before forking
- Fork command is copy-paste ready (user doesn't need to modify it)
- Success confirmation with execution time displayed

#### 5. Initial Database Setup
**User Story:** As a first-time user, I want the tool to automatically set up and index my existing sessions so I can start using it immediately.

**Acceptance Criteria:**
- On first run, automatically scan `~/.claude/` directory
- Detect all existing session files across all projects
- Display progress: "Indexing session 47 of 342..."
- Create session registry at `~/.smart-fork/session-registry.json`
- Initialize vector database at `~/.smart-fork/vector_db/`
- Estimated time displayed (e.g., "~15 minutes remaining")
- Graceful handling if interrupted (resume from last checkpoint)

#### 6. Claude Memory Integration
**User Story:** As a developer, I want the search to consider Claude's memory categories so results are contextually relevant.

**Acceptance Criteria:**
- Extract and index memory markers from sessions:
  - PATTERN (design patterns, solutions)
  - WORKING_SOLUTION (proven implementations)
  - WAITING (async operations, pending items)
- Display recalled memories with similarity scores
- Weight results based on memory type relevance
- Show memory indicators in search results

---

## Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    Claude Code Client                    │
│                    (User Interface)                      │
└────────────────────┬────────────────────────────────────┘
                     │ MCP Protocol
┌────────────────────▼────────────────────────────────────┐
│              Smart Fork MCP Server                       │
│  ┌──────────────────────────────────────────────────┐   │
│  │         Command Handler (/fork-detect)           │   │
│  └───────────┬──────────────────────────────────────┘   │
│              │                                           │
│  ┌───────────▼──────────────┐  ┌────────────────────┐   │
│  │   Embedding Service      │  │  Search Service    │   │
│  │   (Nomic 768-dim)        │  │  (Composite Score) │   │
│  └───────────┬──────────────┘  └─────────┬──────────┘   │
│              │                           │              │
│  ┌───────────▼───────────────────────────▼──────────┐   │
│  │           Local REST API Server                  │   │
│  │           (localhost:8741)                       │   │
│  │    Endpoints: /chunks/search, /sessions/index   │   │
│  └───────────┬──────────────────────────────────────┘   │
└──────────────┼──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│                  Storage Layer                           │
│  ┌────────────────┐  ┌──────────────┐  ┌────────────┐   │
│  │  Vector DB     │  │   Session    │  │   Config   │   │
│  │  (ChromaDB)    │  │   Registry   │  │    JSON    │   │
│  │ ~/.smart-fork/ │  │    .json     │  │  settings  │   │
│  └────────────────┘  └──────────────┘  └────────────┘   │
└─────────────────────────────────────────────────────────┘
               │
               │ Monitors
               ▼
┌─────────────────────────────────────────────────────────┐
│           Claude Code Session Files                      │
│     ~/.claude/projects/{project}/*.jsonl                 │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

**MCP Server Framework:**
- Language: Python 3.10+
- Framework: FastMCP or MCP SDK (Python)
- Async support for non-blocking operations

**Vector Database:**
- Primary: ChromaDB (local, lightweight, excellent Python integration)
- Alternative: FAISS (for users preferring Facebook's solution)
- Storage: Persistent disk-backed collections

**Embedding Model:**
- Model: `nomic-embed-text-v1.5`
- Dimensions: 768
- Library: `sentence-transformers` or Nomic's official Python client
- Rationale: Superior quality for long-form technical text, runs locally, free and open source

**Local API Server:**
- Framework: FastAPI (async, high performance)
- Port: 8741 (configurable)
- Purpose: Provides REST endpoints for search and indexing operations

**File Monitoring:**
- Library: `watchdog` (cross-platform file system events)
- Monitors: `~/.claude/` directory tree
- Events: File creation, modification, deletion

**Session Parsing:**
- Format: JSONL (JSON Lines)
- Parser: Built-in `json` module with streaming support
- Handles: Malformed lines, incomplete sessions, corrupted data

### Data Flow

#### Indexing Flow
```
1. File Monitor detects new/updated session file
   ↓
2. Session Parser reads JSONL and extracts messages
   ↓
3. Chunking Service splits session into semantic chunks (500-1000 tokens)
   ↓
4. Memory Extractor identifies PATTERN/WORKING_SOLUTION/WAITING markers
   ↓
5. Embedding Service generates 768-dim vectors (batch processing)
   ↓
6. Vector DB stores chunks with metadata
   ↓
7. Session Registry updated with timestamp and stats
```

#### Search Flow
```
1. User invokes /fork-detect with natural language query
   ↓
2. Embedding Service generates query vector
   ↓
3. Vector DB performs similarity search (top 50 chunks)
   ↓
4. Scoring Engine calculates composite scores per session
   ↓
5. Aggregator groups chunks by session, ranks sessions
   ↓
6. Result Formatter prepares top 5 with metadata
   ↓
7. Interactive UI presents results to user
   ↓
8. Fork Command Generator creates appropriate command
```

---

## Data Models & Storage

### Storage Directory Structure

```
~/.smart-fork/
├── vector_db/                    # ChromaDB persistent storage
│   ├── chroma.sqlite3           # Metadata and index
│   └── collections/             # Vector collections
│       └── session_chunks/      # Main collection
├── session-registry.json        # Quick lookup index
├── config.json                  # User configuration
├── logs/                        # Application logs
│   ├── indexing.log
│   ├── search.log
│   └── errors.log
└── cache/                       # Temporary cache
    └── embeddings/              # Cached embeddings (optional)
```

### Session Registry Schema

```json
{
  "version": "1.0",
  "last_synced": "2026-01-20T22:23:33.311Z",
  "total_sessions": 342,
  "total_chunks": 15847,
  "sessions": {
    "8402b1ed-99dc-417d-86a9-36a1478036dc": {
      "project": "mortgage-coach-project",
      "project_path": "/Users/user/.claude/projects/mortgage-coach-project",
      "created_at": "2026-01-15T14:22:10.000Z",
      "updated_at": "2026-01-15T18:45:33.000Z",
      "message_count": 87,
      "chunk_count": 23,
      "topic": "Session Dashboard",
      "tags": ["dashboard", "nextjs", "real-time", "token-usage"],
      "memory_types": ["PATTERN", "WORKING_SOLUTION"],
      "indexed_at": "2026-01-15T18:46:00.000Z"
    }
  }
}
```

### Vector Database Schema

**Collection Name:** `session_chunks`

**Chunk Document Structure:**
```python
{
  "id": "8402b1ed_chunk_05",           # Unique chunk identifier
  "session_id": "8402b1ed-99dc-417d-86a9-36a1478036dc",
  "chunk_index": 5,                    # Position in session
  "text": "When building a session dashboard...",
  "embedding": [0.023, -0.145, ...],   # 768-dimensional vector
  "metadata": {
    "project": "mortgage-coach-project",
    "timestamp": "2026-01-15T15:30:22.000Z",
    "message_numbers": [12, 13, 14],   # Which messages in this chunk
    "memory_type": "WORKING_SOLUTION",
    "has_code": true,
    "languages": ["javascript", "jsx"],
    "tokens": 876
  }
}
```

### Configuration Schema

```json
{
  "version": "1.0",
  "embedding": {
    "model": "nomic-embed-text-v1.5",
    "dimensions": 768,
    "batch_size": 50,
    "max_batch_memory_mb": 2048
  },
  "indexing": {
    "checkpoint_interval": 15,          // Messages between checkpoints
    "chunk_size_tokens": 750,           // Target chunk size
    "chunk_overlap_tokens": 150,        // Overlap between chunks
    "auto_index": true,
    "watch_directories": ["~/.claude/"]
  },
  "search": {
    "max_results": 5,
    "similarity_threshold": 0.3,        // Minimum similarity score
    "include_recent_boost": true,
    "recency_weight_days": 30
  },
  "server": {
    "host": "localhost",
    "port": 8741,
    "enable_api": true
  },
  "storage": {
    "directory": "~/.smart-fork/",
    "vector_db": "chromadb",
    "max_cache_size_mb": 500
  }
}
```

### Chunking Strategy

**Why Chunk-Based Instead of Whole Sessions:**
- Sessions can be very long (thousands of messages)
- Different parts of a session cover different topics
- Enables precise matching to specific relevant portions
- Better performance with smaller embedding units
- More granular scoring and ranking

**Chunking Algorithm:**
```
1. Split session by message boundaries
2. Group messages into ~750 token chunks with 150 token overlap
3. Ensure chunks don't split code blocks or logical units
4. Extract topic/theme for each chunk
5. Identify memory markers within each chunk
6. Generate embedding per chunk
7. Store with parent session reference
```

**Example Chunking:**
```
Session: 87 messages, ~25,000 tokens
↓
Chunks:
- Chunk 0: Messages 1-5 (initial project discussion)
- Chunk 1: Messages 4-8 (architecture planning) [overlap with Chunk 0]
- Chunk 2: Messages 7-12 (API design)
- ...
- Chunk 22: Messages 80-87 (final implementation)
Total: 23 chunks
```

---

## User Experience & Interface

### Command Invocation

**Primary Command:**
```bash
/fork-detect
```

**Claude's Response:**
```
What would you like to do?
```

**User Input Examples:**
```
"Add real-time token usage cards to my dashboard"
"Implement OAuth authentication for my Next.js app"
"Fix the database connection pooling issue"
"Create a responsive navigation menu with Tailwind"
```

### Search Results Display

**Format:**
```
┌─────────────────────────────────────────────────────────┐
│                    □ Fork Session                       │
└─────────────────────────────────────────────────────────┘

Which session would you like to fork for adding real-time 
token usage cards to your dashboard?

❯ 1. #1: 8402b1ed (Recommended)
    Real-time token usage dashboard updates - best semantic match (81%)
    
  2. #2: 3a850835
    Token usage field registration issues (74%)
    
  3. #3: e6b158a2
    Live stats implementation - 17 stories completed (67%)
    
  4. None - start fresh
    Don't fork any session, start with no prior context
    
  5. Type something.
    Custom input or refine search
    
┌─────────────────────────────────────────────────────────┐
│ Chat about this                                          │
└─────────────────────────────────────────────────────────┘

Enter to select · ↑/↓ to navigate · Esc to cancel
```

### Result Details

**Each result includes:**
- **Position Number:** #1, #2, #3
- **Session ID:** Truncated for readability (8402b1ed...)
- **Recommendation Badge:** Only on highest-scoring result
- **Topic/Description:** Auto-extracted from session content
- **Match Type:** "best semantic match" / "working solution" / etc.
- **Score Percentage:** 81%, 74%, 67%
- **Date:** "Recent", "2 weeks ago", "Jan 15"
- **Additional Context:** Message count, project name, or key details

### Selection Actions

**Option 1-3 Selection (Session Fork):**
```
You selected: Session 8402b1ed
Generating fork command...

Fork Command (not copied):
claude --resume 8402b1ed-99dc-417d-86a9-36a1478036dc --fork-session

Or use /fork in this session:
/fork 8402b1ed-99dc-417d-86a9-36a1478036dc C:/Users/user/.claude/projects/mortgage-coach-project/8402b1ed-99dc-417d-86a9-36a1478036dc.jsonl

✨Worked for 1m 13s
```

**Option 4 Selection (Start Fresh):**
```
Starting fresh with no prior context.
Ready to begin! What would you like to work on?
```

**Option 5 Selection (Custom Input):**
```
What would you like to search for or do differently?
> [User provides refined query]
```

**Chat About This:**
```
User clicks "Chat about this"
↓
Claude: I found these sessions related to token usage dashboards. 
The top result (81% match) is from your work on real-time updates 
for the mortgage coach project. Would you like me to explain what 
was accomplished in that session, or shall we proceed with forking?

User: What did we accomplish?
Claude: [Provides summary based on session metadata]
```

### Error States

**No Sessions Found:**
```
No relevant sessions found for "implement blockchain validation"

Would you like to:
1. Start a fresh session
2. Refine your search query
3. Browse recent sessions
```

**Database Not Initialized:**
```
Smart Fork database not found. Initializing...

Scanning your Claude Code sessions...
Found 156 sessions across 12 projects.

Estimated indexing time: ~8 minutes
Continue? (Y/n)
```

**Search Timeout:**
```
Search is taking longer than expected...

This might happen if:
- Database is very large (10,000+ sessions)
- First search after startup (warming up)

⏳ Still searching... (15s elapsed)
```

---

## Search & Ranking Algorithm

### Composite Scoring Formula

```
Final Score = (best_similarity × 0.40) 
            + (avg_similarity × 0.20)
            + (chunk_ratio × 0.05)
            + (recency × 0.25)
            + (chain_quality × 0.10)
```

### Component Breakdown

#### 1. Best Similarity (40% weight)
**Definition:** Highest cosine similarity score among all chunks in the session.

**Rationale:** Indicates at least one part of the session is highly relevant to the query.

**Calculation:**
```python
best_similarity = max(cosine_similarity(query_embedding, chunk_embedding) 
                      for chunk in session_chunks)
```

**Example:**
```
Query: "Add OAuth authentication"
Session chunks:
- Chunk 3: OAuth implementation discussion (similarity: 0.87)
- Chunk 7: Database schema design (similarity: 0.32)
- Chunk 12: Error handling (similarity: 0.41)

best_similarity = 0.87
```

#### 2. Average Similarity (20% weight)
**Definition:** Mean cosine similarity across all chunks in the session.

**Rationale:** Measures overall relevance of the entire session, not just peak matching.

**Calculation:**
```python
avg_similarity = mean(cosine_similarity(query_embedding, chunk_embedding) 
                      for chunk in session_chunks)
```

**Example:**
```
Same session as above:
avg_similarity = (0.87 + 0.32 + 0.41 + ... + 0.55) / 23 = 0.52
```

#### 3. Chunk Ratio (5% weight)
**Definition:** Proportion of session chunks that exceed similarity threshold (0.3).

**Rationale:** Sessions with more relevant chunks provide broader useful context.

**Calculation:**
```python
relevant_chunks = count(chunk for chunk in session_chunks 
                        if similarity(chunk) > 0.3)
chunk_ratio = relevant_chunks / total_chunks
```

**Example:**
```
Session with 23 chunks:
- 8 chunks exceed 0.3 threshold
chunk_ratio = 8 / 23 = 0.35
```

#### 4. Recency (25% weight)
**Definition:** Time-based decay factor favoring recent sessions.

**Rationale:** Recent work is often more relevant (current project state, recent patterns, newer technologies).

**Calculation:**
```python
days_old = (current_date - session_updated_at).days
recency_score = exp(-days_old / 30)  # 30-day decay constant
```

**Example:**
```
Session from 5 days ago:
recency_score = exp(-5/30) = 0.85

Session from 60 days ago:
recency_score = exp(-60/30) = 0.14
```

#### 5. Chain Quality (10% weight)
**Definition:** Success rate of sessions forked from this session.

**Rationale:** Sessions that led to successful continued work are likely valuable baseline contexts.

**Calculation (Post-MVP):**
```python
chain_quality = (successful_forks / total_forks) if total_forks > 0 else 0.5

# Success criteria:
# - Forked session lasted > 20 messages
# - No early abandonment
# - Led to file modifications/commits
```

**Note:** For MVP, chain_quality defaults to 0.5 (neutral). Full tracking implemented in v1.1.

### Ranking Process

```python
def rank_sessions(query: str, all_sessions: List[Session]) -> List[RankedSession]:
    query_embedding = embed(query)
    ranked = []
    
    for session in all_sessions:
        # Get all chunk similarities for this session
        chunk_sims = [cosine_sim(query_embedding, chunk.embedding) 
                      for chunk in session.chunks]
        
        # Calculate components
        best_sim = max(chunk_sims)
        avg_sim = mean(chunk_sims)
        chunk_ratio = sum(1 for s in chunk_sims if s > 0.3) / len(chunk_sims)
        recency = exp(-(now() - session.updated_at).days / 30)
        chain_qual = session.chain_quality or 0.5
        
        # Composite score
        score = (best_sim * 0.40 +
                 avg_sim * 0.20 +
                 chunk_ratio * 0.05 +
                 recency * 0.25 +
                 chain_qual * 0.10)
        
        ranked.append(RankedSession(session, score, {
            'best_similarity': best_sim,
            'avg_similarity': avg_sim,
            'chunk_ratio': chunk_ratio,
            'recency': recency,
            'chain_quality': chain_qual
        }))
    
    # Sort by score descending, return top 5
    return sorted(ranked, key=lambda x: x.score, reverse=True)[:5]
```

### Memory Type Boosting

Sessions containing relevant memory markers receive additional score boost:

```python
memory_boost = {
    'PATTERN': 1.05,           # 5% boost for design patterns
    'WORKING_SOLUTION': 1.08,  # 8% boost for proven solutions
    'WAITING': 1.02            # 2% boost for async context
}

if session.memory_type in memory_boost:
    score *= memory_boost[session.memory_type]
```

### Search Optimization

**Vector Search Strategy:**
1. Initial k-nearest neighbors search (k=200 chunks)
2. Group chunks by session
3. Calculate composite scores per session
4. Return top 5 sessions

**Performance Targets:**
- Search latency: < 3 seconds for 10,000+ sessions
- Indexing throughput: > 100 messages/second
- Memory usage: < 2GB for 50,000 chunks

---

## Security & Privacy

### Data Privacy

**Local-Only Storage:**
- All data stored locally in `~/.smart-fork/`
- No cloud uploads or external API calls (except embedding model if using API version)
- Vector database encrypted at rest (optional)

**Sensitive Data Handling:**
- Session transcripts may contain API keys, passwords, or personal information
- Tool does NOT redact or filter sensitive data from indexing
- **User Responsibility:** Users must ensure their sessions don't contain credentials
- **Recommendation:** Use environment variables and .env files (not hardcoded secrets)

**Access Control:**
- Database files readable only by user (Unix permissions: 600)
- No network exposure (local server binds to 127.0.0.1 only)

### Security Considerations

**Local Server Security:**
- REST API only accessible from localhost
- No authentication required (single-user system)
- Optional: API key authentication for multi-user systems (future)

**Code Injection Prevention:**
- Session content sanitized before embedding
- No eval() or exec() of session code
- Chunk text treated as data, not executable code

**Dependency Security:**
- Pin all dependencies to specific versions
- Regular security audits of dependencies
- Use virtual environment isolation

### Privacy Best Practices Documentation

**User Guidelines (to be documented):**
1. Never hardcode API keys or secrets in Claude Code sessions
2. Use `.env` files for sensitive configuration
3. Review session transcripts before sharing forked sessions
4. Consider encrypting `~/.smart-fork/` directory for extra protection
5. Regularly prune old sessions containing outdated/sensitive info

---

## Development Phases

### Phase 1: MVP (v1.0) - Core Functionality
**Duration:** 4-6 weeks  
**Goal:** Deliver working `/fork-detect` command with basic search and forking

**Milestones:**

**Week 1-2: Foundation**
- [ ] Set up MCP server project structure
- [ ] Implement Nomic embedding integration
- [ ] Create ChromaDB wrapper with chunk storage
- [ ] Build session file parser (JSONL reader)
- [ ] Implement chunking algorithm

**Week 3-4: Core Features**
- [ ] Build background indexing service
- [ ] Implement file monitoring (watchdog integration)
- [ ] Create composite scoring algorithm
- [ ] Develop search service with ranking
- [ ] Build local REST API server

**Week 5-6: User Interface & Polish**
- [ ] Implement `/fork-detect` MCP command handler
- [ ] Create interactive selection UI
- [ ] Build fork command generator (dual modes)
- [ ] Add initial database setup flow
- [ ] Write user documentation
- [ ] Testing and bug fixes

**Deliverables:**
- Functional MCP server installable via pip/npm
- Working `/fork-detect` command
- Automatic background indexing
- Top 5 search results with composite scoring
- Dual forking modes
- Basic configuration options

### Phase 2: Enhancement (v1.1) - Advanced Features
**Duration:** 3-4 weeks  
**Goal:** Add chain quality tracking, performance optimization, and advanced search

**Features:**
- [ ] Session chain tracking system
- [ ] Fork success monitoring
- [ ] Chain quality scoring in composite algorithm
- [ ] Search filtering (by project, date range, tags)
- [ ] Manual `/reindex` command
- [ ] `/stats` command (database statistics)
- [ ] Performance optimization (caching, batch processing)
- [ ] Configuration UI/command

**Deliverables:**
- Chain quality component fully functional
- Advanced search filters
- Maintenance commands
- Performance improvements (2x faster search)

### Phase 3: Ecosystem Integration (v1.2) - Complementary Features
**Duration:** 4-6 weeks  
**Goal:** Build the "other two components" of the context management system

**Potential Components (TBD based on user feedback):**
- Session summarization tool
- Automatic session organization/tagging
- Session continuation assistant
- Visual session chain explorer
- Context compression tool

**Deliverables:**
- 1-2 additional context management tools
- Integration between all components
- Unified dashboard/interface

### Phase 4: Polish & Scale (v2.0) - Production Ready
**Duration:** 3-4 weeks  
**Goal:** Enterprise-ready features and scalability

**Features:**
- [ ] Team sharing capabilities (optional encrypted sync)
- [ ] Session export/import
- [ ] Advanced analytics dashboard
- [ ] Plugin system for custom embeddings/ranking
- [ ] Support for 100,000+ sessions
- [ ] Cloud backup option (user-controlled)

---

## Success Metrics

### User Adoption Metrics

**Primary KPIs:**
- **Daily Active Users:** Percentage of Claude Code users invoking `/fork-detect` daily
- **Search Success Rate:** Percentage of searches resulting in a fork action
- **Retention:** Users still actively using after 30 days

**Targets (Month 3):**
- 40% of pilot users invoke `/fork-detect` at least weekly
- 75% search success rate (user selects from results vs. "start fresh")
- 80% 30-day retention

### Performance Metrics

**System Performance:**
- **Search Latency:** < 3 seconds for 95th percentile
- **Indexing Speed:** > 100 messages/second
- **Memory Usage:** < 2GB RAM with 50,000 chunks
- **Database Size:** ~500KB per 1,000 messages

**Targets:**
- All searches complete in < 5 seconds
- Zero indexing failures or data loss
- Stable memory usage (no leaks)

### Quality Metrics

**Search Relevance:**
- **Top-1 Accuracy:** First result is relevant 80% of time
- **Top-3 Accuracy:** At least one of top 3 is relevant 95% of time
- **User Satisfaction:** 4+ star rating on usefulness

**Measurement Methods:**
- User feedback after fork selection
- Implicit signals (session duration after fork, file modifications)
- Periodic user surveys

### Business Impact Metrics

**Productivity Gains:**
- **Context Rebuild Time Saved:** Average minutes saved per session
- **Successful Feature Implementations:** Increase in completed features
- **Session Efficiency:** Fewer messages needed to complete tasks

**Estimated Impact:**
- Save 15-30 minutes per development session
- Reduce redundant context explanations by 80%
- Increase successful feature completion by 25%

---

## Future Enhancements

### Short-Term (v1.x)

**Smart Forking Improvements:**
- Multi-query search (combine multiple past sessions)
- Negative search (exclude certain topics/sessions)
- Temporal search ("sessions from last week about authentication")
- Project-scoped search toggle

**User Experience:**
- Session preview viewer (read full session before forking)
- Fork history tracking (what you've forked recently)
- Favorite/bookmark sessions
- Custom tags and notes on sessions

**Performance:**
- Incremental indexing (delta updates only)
- Query caching for repeated searches
- Embedding caching to reduce computation
- Multi-threaded indexing

### Medium-Term (v2.x)

**Component #2 - Session Organization (Hypothesis):**
- Automatic topic clustering
- Project-based organization
- Tag suggestions based on content
- Session relationship graphs

**Component #3 - Session Continuation (Hypothesis):**
- Smart resume (automatically load relevant past context)
- Session merging (combine multiple sessions)
- Context compression (intelligently prune old messages)
- Cross-session references

**Advanced Intelligence:**
- Learn from user fork selections (improve ranking over time)
- Predict which sessions user might need next
- Auto-suggest forks based on current work
- Duplicate session detection

### Long-Term (v3.x)

**Team Features:**
- Shared session libraries (team knowledge base)
- Privacy controls (public/private sessions)
- Session collaboration (fork from teammate's work)
- Permission management

**Platform Expansion:**
- Support for other AI coding assistants
- Integration with GitHub/GitLab (link commits to sessions)
- IDE plugins (VS Code, JetBrains)
- Web dashboard for session management

**Advanced Capabilities:**
- Natural language session querying ("Show me all sessions where we discussed API design for the mobile app")
- Session diff tool (compare two sessions)
- Automated session summarization
- Multi-modal search (search by code snippets, error messages, screenshots)

---

## Technical Challenges & Solutions

### Challenge 1: RAM Exhaustion During Batch Embedding

**Problem:** Embedding large batches of text can consume excessive RAM, especially with 768-dimensional Nomic embeddings. Original developer experienced system lockup with improper batch sizing.

**Solution:**
```python
# Adaptive batch sizing based on available memory
import psutil

def calculate_safe_batch_size():
    available_ram = psutil.virtual_memory().available
    # Conservative estimate: 10MB per embedding in batch
    max_batch = min(available_ram // (10 * 1024 * 1024), 50)
    return max(max_batch, 10)  # Minimum batch of 10

# Stream processing with memory monitoring
def embed_chunks_safely(chunks):
    batch_size = calculate_safe_batch_size()
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        embeddings = model.encode(batch)
        yield from embeddings
        
        # Garbage collection after each batch
        import gc
        gc.collect()
```

**Acceptance Criteria:**
- Indexing completes without system lockup
- RAM usage stays below configurable limit (default 2GB)
- Graceful degradation (smaller batches) on low-memory systems

### Challenge 2: Session Chunking at Semantic Boundaries

**Problem:** Naive chunking (e.g., every N tokens) can split logical units like code blocks, conversations, or explanations mid-thought.

**Solution:**
```python
# Semantic-aware chunking
def chunk_session_intelligently(session_messages):
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for message in session_messages:
        message_tokens = count_tokens(message.content)
        
        # Check if adding this message exceeds target
        if current_tokens + message_tokens > TARGET_CHUNK_SIZE:
            # Only split if we have enough content
            if current_tokens > MIN_CHUNK_SIZE:
                chunks.append(create_chunk(current_chunk))
                current_chunk = [message]  # Start new chunk
                current_tokens = message_tokens
            else:
                # Too small, keep adding
                current_chunk.append(message)
                current_tokens += message_tokens
        else:
            current_chunk.append(message)
            current_tokens += message_tokens
    
    # Don't forget last chunk
    if current_chunk:
        chunks.append(create_chunk(current_chunk))
    
    return chunks
```

**Acceptance Criteria:**
- Code blocks never split mid-block
- Conversation turns kept together (user message + Claude response)
- Chunks range from 500-1000 tokens (target 750)
- Overlap of 150 tokens between chunks

### Challenge 3: Real-Time Indexing Without Performance Impact

**Problem:** Continuously monitoring and indexing sessions while Claude Code is running could slow down the user's workflow.

**Solution:**
```python
# Low-priority background indexing with debouncing
import asyncio
from collections import defaultdict

class BackgroundIndexer:
    def __init__(self):
        self.pending_sessions = defaultdict(float)  # session_id -> last_modified
        self.debounce_delay = 5  # seconds
        
    async def schedule_index(self, session_id, modified_time):
        # Update pending queue
        self.pending_sessions[session_id] = modified_time
        
        # Wait for activity to settle
        await asyncio.sleep(self.debounce_delay)
        
        # Check if this is still the latest modification
        if self.pending_sessions[session_id] == modified_time:
            await self.index_session_async(session_id)
            del self.pending_sessions[session_id]
    
    async def index_session_async(self, session_id):
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.index_session, session_id)
```

**Acceptance Criteria:**
- Indexing triggered 5 seconds after last modification
- No impact on Claude Code responsiveness
- Graceful handling of rapid successive changes
- Process priority set to low/background

### Challenge 4: Handling Corrupted or Incomplete Sessions

**Problem:** Sessions may be corrupted (malformed JSON), incomplete (crashed mid-session), or contain special characters that break parsing.

**Solution:**
```python
# Robust session parser with error recovery
def parse_session_robust(filepath):
    messages = []
    errors = []
    
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line_num, line in enumerate(f, 1):
            try:
                # Skip empty lines
                if not line.strip():
                    continue
                    
                # Parse JSON
                message = json.loads(line)
                messages.append(message)
                
            except json.JSONDecodeError as e:
                # Log error but continue
                errors.append(f"Line {line_num}: {str(e)}")
                continue
            except Exception as e:
                # Unexpected error - log and continue
                errors.append(f"Line {line_num}: Unexpected error: {str(e)}")
                continue
    
    # Only fail if we got NOTHING
    if not messages:
        raise ValueError(f"No valid messages in session. Errors: {errors}")
    
    # Log warnings but return what we got
    if errors:
        log.warning(f"Session {filepath} had {len(errors)} parse errors")
    
    return messages, errors
```

**Acceptance Criteria:**
- Graceful handling of malformed JSON lines
- Incomplete sessions still indexed (partial data better than none)
- Error logging for debugging but no indexing failures
- UTF-8 encoding errors handled

### Challenge 5: Scaling to 10,000+ Sessions

**Problem:** As users accumulate thousands of sessions, search performance may degrade and database size may become unwieldy.

**Solution:**
```python
# Hierarchical indexing with project-level organization
class HierarchicalIndex:
    def __init__(self):
        self.project_indexes = {}  # project -> VectorDB
        self.global_index = None   # All sessions
        
    def search(self, query, scope='global'):
        if scope == 'global':
            return self.global_index.search(query)
        elif scope in self.project_indexes:
            # Faster search within project
            return self.project_indexes[scope].search(query)
        else:
            # Fall back to global
            return self.global_index.search(query)
    
    def index_session(self, session):
        project = session.project
        
        # Ensure project index exists
        if project not in self.project_indexes:
            self.project_indexes[project] = VectorDB(f"index_{project}")
        
        # Index in both project and global
        self.project_indexes[project].add(session)
        self.global_index.add(session)
```

**Future Optimization:**
- Archive old sessions (>1 year) to separate database
- Implement approximate nearest neighbor (ANN) for faster search
- Database sharding by time period or project

**Acceptance Criteria:**
- Search remains < 3 seconds with 10,000 sessions
- Database size < 5GB for 10,000 sessions
- Option to search within current project only (faster)

---

## Appendix

### Glossary

**Terms:**
- **Chunking:** Breaking long sessions into smaller semantic units for better search granularity
- **Composite Scoring:** Ranking algorithm combining multiple factors (similarity, recency, etc.)
- **Context Loss:** Problem where new sessions start without knowledge from previous conversations
- **Embedding:** Vector representation of text that captures semantic meaning
- **Episodic Memory:** Type of memory related to specific events/experiences (vs. semantic/factual)
- **Forking:** Creating a new session that inherits context from a previous session
- **MCP (Model Context Protocol):** Protocol for extending Claude with custom tools/capabilities
- **RAG (Retrieval-Augmented Generation):** Using search/retrieval to augment LLM with external knowledge
- **Session:** Single conversation thread in Claude Code (stored as .jsonl file)
- **Vector Database:** Database optimized for storing and searching high-dimensional vectors

### References

**Technologies:**
- [Model Context Protocol Documentation](https://modelcontextprotocol.io)
- [Nomic Embeddings](https://www.nomic.ai/blog/posts/nomic-embed-text-v1)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Claude Code Documentation](https://docs.claude.com/claude-code)

**Inspiration:**
- Original concept by [@PerceptualPeak on X](https://x.com/PerceptualPeak)
- [36kr Article on Smart Forking](https://eu.36kr.com/en/p/3647435834838663)

### Change Log

**Version 1.0 (2026-01-20):**
- Initial PRD creation
- Comprehensive analysis of original concept and implementation
- Detailed technical architecture and data models
- Complete feature specifications for MVP
- Development roadmap and success metrics

---

## Document Metadata

**Author:** Product Requirements Document  
**Stakeholders:** Awentz513 (Product Owner), Development Team  
**Status:** Draft for Review  
**Next Review:** After stakeholder feedback  
**Related Documents:** None (initial document)

---

**End of Document**
