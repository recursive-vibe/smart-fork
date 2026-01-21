# Phase 3 Features - Testing Guide

## Prerequisites

Before testing, install dependencies:
```bash
pip3 install -e .
# or if that fails due to proxy:
pip3 install numpy scikit-learn sentence-transformers chromadb watchdog psutil
```

---

## New MCP Tools Added in Phase 3

### P3 Tools (5 new features, 9 new tools total)

#### 1. Session Summarization
**Tool:** `get-session-summary`
- Get a quick TF-IDF based summary of any session
- Shows top topics and key sentences

**Test:**
```bash
# Via MCP client or Claude.ai
get-session-summary session_id="test-session-001"
```

**Expected:** Summary with 3 key sentences and top 5 topics

---

#### 2. Automatic Topic Clustering
**Tools:**
- `cluster-sessions` - Run k-means clustering on all sessions
- `get-session-clusters` - List all clusters with metadata
- `get-cluster-sessions` - View sessions in a specific cluster

**Test:**
```bash
# Cluster all sessions
cluster-sessions num_clusters=5

# View clusters
get-session-clusters

# View sessions in cluster 0
get-cluster-sessions cluster_id=0
```

**Expected:**
- Sessions grouped by topic (Python, JavaScript, Database, etc.)
- Cluster labels auto-generated from tags/projects
- Silhouette score quality metric

---

#### 3. Session Diff Tool
**Tool:** `compare-sessions`
- Compare two sessions semantically
- Find common vs unique content
- Extract topic differences

**Test:**
```bash
# Compare two sessions
compare-sessions session_id_1="session-abc" session_id_2="session-xyz" include_content=true
```

**Expected:**
- Overall similarity score (0-100%)
- List of matching messages with scores
- Unique topics in each session
- Technology differences

---

#### 4. Session Archiving
**Enhancement:** `fork-detect` now accepts `--include-archive` parameter
- Archive old sessions (default: >365 days)
- Search archived sessions when needed
- Restore sessions from archive

**Test:**
```bash
# Normal search (active sessions only)
fork-detect query="python database" limit=5

# Search including archived sessions
fork-detect query="python database" limit=5 include_archive=true
```

**Direct service usage (Python):**
```python
from smart_fork.session_archive_service import SessionArchiveService
archive = SessionArchiveService(storage_dir="~/.smart-fork")

# Archive sessions older than 1 year
results = archive.archive_old_sessions(dry_run=True)
print(f"Would archive {results['sessions_moved']} sessions")

# Actually archive
results = archive.archive_old_sessions(dry_run=False)

# Restore a session
archive.restore_session("old-session-id")
```

---

#### 5. VS Code Extension
**Location:** `vscode-extension/`
**Commands:**
- `Smart Fork: Search Sessions` - Search from command palette
- `Smart Fork: Fork Session` - Fork from a specific session ID
- `Smart Fork: View Fork History` - See recent forks

**Test:**
```bash
cd vscode-extension
npm install
npm run compile

# Then in VS Code:
# 1. Open vscode-extension folder
# 2. Press F5 to launch Extension Development Host
# 3. Cmd+Shift+P > "Smart Fork: Search Sessions"
```

---

## Running Automated Tests

### Unit Tests (Fast, no network required)
```bash
# Session summarization
python3 -m pytest tests/test_session_summary_service.py -v

# Topic clustering
python3 -m pytest tests/test_session_clustering_service.py -v

# Session diff
python3 -m pytest tests/test_session_diff_service.py -v

# Session archiving
python3 -m pytest tests/test_session_archive_service.py -v
```

### Integration Tests (Slower, requires network for embedding model)
```bash
# Note: May fail in proxy environments
python3 -m pytest tests/test_session_summary_integration.py -v
python3 -m pytest tests/test_session_clustering_integration.py -v
python3 -m pytest tests/test_session_diff_integration.py -v
python3 -m pytest tests/test_session_archive_integration.py -v
```

### Run All Tests
```bash
python3 -m pytest tests/ -v
```

---

## Manual Testing with Real Data

### 1. Test Summarization on Real Sessions
```python
from smart_fork.session_summary_service import SessionSummaryService
from smart_fork.session_registry import SessionRegistry

registry = SessionRegistry(storage_dir="~/.smart-fork")
summary_service = SessionSummaryService()

# Get a real session
sessions = registry.list_sessions()
if sessions:
    session = sessions[0]
    summary = summary_service.generate_summary(session.messages)
    print(f"Summary: {summary}")
```

### 2. Test Clustering on Your Sessions
```bash
# Start the MCP server
python3 -m smart_fork.server

# Then from Claude.ai or MCP client:
# 1. cluster-sessions num_clusters=8
# 2. get-session-clusters
# 3. Browse clusters to see if grouping makes sense
```

### 3. Test Session Diff
```bash
# Compare two similar sessions about the same topic
compare-sessions session_id_1="<id1>" session_id_2="<id2>" include_content=true

# Look for:
# - High similarity (>80%) for truly similar sessions
# - Common topics identified correctly
# - Unique content highlighted properly
```

### 4. Test Archiving Workflow
```python
from smart_fork.session_archive_service import SessionArchiveService
from smart_fork.config_manager import ConfigManager

config = ConfigManager()
archive = SessionArchiveService(
    storage_dir=config.get_storage_dir(),
    threshold_days=30  # Archive sessions older than 30 days for testing
)

# Dry run
results = archive.archive_old_sessions(dry_run=True)
print(f"Would archive: {results}")

# Actually archive
if results['sessions_moved'] > 0:
    archive.archive_old_sessions(dry_run=False)

# Verify
stats = archive.get_archive_stats()
print(f"Archive stats: {stats}")

# Search archive
archived = archive.search_archive(query="python")
print(f"Found {len(archived)} archived sessions matching 'python'")
```

---

## Verification Files

Detailed verification documentation for each feature:
- `verification/phase3-session-summarization.txt`
- `verification/phase3-automatic-topic-clustering.txt`
- `verification/phase3-session-diff-tool.txt`
- `verification/phase3-vscode-extension.txt`

(Note: Session archiving verification is in the test files)

---

## Known Issues

1. **Network/Proxy Issues:** Integration tests may fail when downloading the embedding model from Hugging Face due to proxy settings. Unit tests should work fine.

2. **Missing Dependencies:** If you see `ModuleNotFoundError: No module named 'numpy'` or similar, run:
   ```bash
   pip3 install -e .
   ```

3. **VS Code Extension:** Requires TypeScript compilation before use. See `vscode-extension/README.md` for setup.

---

## Success Criteria

### Session Summarization
- ✅ Summaries are 2-3 sentences
- ✅ Top 5 topics are relevant
- ✅ No code snippets in summaries
- ✅ Generation takes <50ms per session

### Topic Clustering
- ✅ Sessions group by similar topics
- ✅ Labels make sense (from tags/projects)
- ✅ Silhouette score >0.25 (good quality)
- ✅ Can browse sessions by cluster

### Session Diff
- ✅ Similar sessions score >75%
- ✅ Different sessions score <25%
- ✅ Common topics identified correctly
- ✅ Unique content highlighted

### Session Archiving
- ✅ Old sessions moved to archive
- ✅ Archive searchable with flag
- ✅ Restore works correctly
- ✅ Statistics accurate

### VS Code Extension
- ✅ Extension activates on command
- ✅ Search results display in panel
- ✅ Can fork from extension
- ✅ Fork history viewable

---

## Next Steps After Testing

1. Review test results
2. Fix any issues found
3. Push commits to remote
4. Update documentation
5. Consider publishing VS Code extension to marketplace
