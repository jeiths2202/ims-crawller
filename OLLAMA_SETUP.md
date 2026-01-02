# Ollama Setup Guide for LLM Fallback

This guide explains how to set up Ollama for LLM-powered natural language query parsing fallback.

## What is Ollama?

Ollama is a local LLM server that runs AI models on your machine. The IMS Crawler uses it as an optional fallback when rule-based parsing has low confidence (<0.7).

**Benefits:**
- ✅ **Handles complex queries** that rules can't parse
- ✅ **Runs locally** - no external API calls, no data sent to cloud
- ✅ **Optional** - works fine without LLM (rules-only mode)
- ✅ **Privacy** - all processing happens on your machine

## Installation

### Step 1: Install Ollama

**Linux/Mac:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
1. Download from https://ollama.com/download
2. Run the installer
3. Ollama will start automatically as a service

### Step 2: Pull the Model

Download the gemma:2b model (lightweight, fast, 1.4GB):

```bash
ollama pull gemma:2b
```

**Alternative models:**
- `gemma:7b` - Better accuracy, larger (4.8GB)
- `llama3:8b` - Meta's Llama 3, good performance (4.7GB)
- `phi3:mini` - Microsoft Phi-3, very fast (2.3GB)

### Step 3: Start Ollama Server

**Linux/Mac:**
```bash
ollama serve
```

**Windows:**
- Ollama runs automatically as a Windows service
- Check status: Open Task Manager → Services → "Ollama"

**Verify server is running:**
```bash
curl http://localhost:11434/api/tags
```

Should return JSON with available models.

### Step 4: Enable in IMS Crawler

Edit your `.env` file:

```env
# Enable LLM fallback
USE_LLM=true
LLM_MODEL=gemma:2b
LLM_BASE_URL=http://localhost:11434
LLM_TIMEOUT=10
```

## Usage

### When does LLM activate?

The LLM fallback activates **automatically** when:
1. Natural language query is detected (not IMS syntax)
2. Rule-based parsing confidence < 0.7
3. `USE_LLM=true` in `.env`
4. Ollama server is running

**Example queries that trigger LLM:**
```bash
# Complex nested query (rules struggle with this)
python main.py crawl -p "Tibero" -k "find all database connection timeout errors and authentication failures" -m 50

# Ambiguous phrasing
python main.py crawl -p "JEUS" -k "show me issues related to either memory problems or CPU spikes" -m 50

# Mixed language complex query
python main.py crawl -p "OpenFrame" -k "데이터베이스 connection issues 찾기" -m 50
```

**Queries that use rules only (no LLM):**
```bash
# Simple AND query (high confidence with rules)
python main.py crawl -p "Tibero" -k "find error and crash" -m 50

# Direct IMS syntax (always bypasses LLM)
python main.py crawl -p "JEUS" -k "+error +crash" -m 50
```

### Checking if LLM is active

When you run a query, the CLI will show:

```
⚙ Parsing natural language query...
LLM fallback enabled: gemma:2b
```

Or if server is not running:

```
⚙ Parsing natural language query...
⚠ LLM server not available, using rules only
```

## Troubleshooting

### "LLM server not available"

**Check 1: Is Ollama running?**
```bash
# Linux/Mac
ps aux | grep ollama

# Windows
tasklist | findstr ollama
```

**Check 2: Is the port accessible?**
```bash
curl http://localhost:11434/api/tags
```

**Check 3: Is the model downloaded?**
```bash
ollama list
```

Should show `gemma:2b` in the list.

**Fix:**
```bash
# Start server (Linux/Mac)
ollama serve

# Pull model if missing
ollama pull gemma:2b
```

### "Model not found"

If you changed `LLM_MODEL` in `.env`:

```bash
# Pull the model you specified
ollama pull <model-name>

# Example:
ollama pull llama3:8b
```

### LLM returns weird results

**Increase timeout** if model is slow:
```env
LLM_TIMEOUT=30  # Increase from 10 to 30 seconds
```

**Try different model:**
```env
LLM_MODEL=llama3:8b  # Better accuracy than gemma:2b
```

### Performance is slow

**Use smaller model:**
```bash
ollama pull gemma:2b  # Fastest (1.4GB)
```

**Or disable LLM:**
```env
USE_LLM=false  # Use rules only
```

## Advanced Configuration

### Custom Ollama Server

If running Ollama on a different machine:

```env
LLM_BASE_URL=http://192.168.1.100:11434
```

### Temperature Control

Lower temperature = more deterministic output:

```env
LLM_TEMPERATURE=0.1  # Default (deterministic)
LLM_TEMPERATURE=0.5  # More creative (less reliable)
```

### Token Limit

Control max response length:

```env
LLM_MAX_TOKENS=50   # Default (short responses)
LLM_MAX_TOKENS=100  # Longer responses (slower)
```

## Uninstalling

### Remove Ollama

**Linux:**
```bash
sudo systemctl stop ollama
sudo systemctl disable ollama
sudo rm /usr/local/bin/ollama
sudo rm -rf /usr/share/ollama
```

**Mac:**
```bash
rm -rf /Applications/Ollama.app
rm -rf ~/.ollama
```

**Windows:**
1. Settings → Apps → Ollama → Uninstall

### Remove Models

```bash
ollama rm gemma:2b
```

Models are stored in:
- Linux: `~/.ollama/models`
- Mac: `~/.ollama/models`
- Windows: `%USERPROFILE%\.ollama\models`

## FAQ

**Q: Do I need LLM?**
A: No, the crawler works fine without it. LLM is optional for complex queries.

**Q: Does it send data to the internet?**
A: No, Ollama runs 100% locally on your machine. No data leaves your computer.

**Q: How much RAM do I need?**
A: Minimum 4GB for gemma:2b, 8GB recommended for gemma:7b.

**Q: Can I use OpenAI/Claude instead?**
A: Currently only Ollama is supported. Cloud APIs may be added in Phase 4.

**Q: Will it slow down my searches?**
A: LLM only runs for complex queries with low confidence. Simple queries use fast rule-based parsing.

---

**For more information:** https://ollama.com
