# Enhanced Schema v2.0 Redis Subscription Guide

## 📋 Overview

Enhanced Schema v2.0 provides rich match data with complete contact information, team logo integration, and intelligent sync priority for the calendar service. This guide explains how to use and configure Enhanced Schema v2.0 features.

## 🎯 Key Features

### ✅ Multi-Version Channel Support
- Subscribes to `fogis:matches:updates:v2` for Enhanced Schema v2.0
- Maintains fallback subscriptions to `fogis:matches:updates:v1` and `fogis:matches:updates`
- Automatic schema version detection and routing

### ✅ Complete Contact Information
- Full referee contact data (mobile, email, address)
- Complete team contact information
- Structured address data for calendar entries

### ✅ Team Logo Integration
- Integrates with team-logo-combiner service
- Uses Organization IDs for logo generation
- Automatic logo caching for performance
- Graceful degradation when logo service unavailable

### ✅ Intelligent Sync Priority
- High-priority changes (time, date, venue, referee) trigger immediate sync
- Medium-priority changes use standard sync
- Detailed change information for better calendar updates

### ✅ Backward Compatibility
- Continues processing v1.0 and v1.5 schema messages
- Graceful degradation when Enhanced Schema v2.0 features unavailable
- No breaking changes to existing functionality

## 🔧 Configuration

### Environment Variables

```bash
# Enhanced Schema v2.0 Configuration
REDIS_SCHEMA_VERSION=2.0                              # Preferred schema version
LOGO_COMBINER_URL=http://team-logo-combiner:5002     # Logo service URL
REDIS_ENABLED=true                                    # Enable Redis integration

# Backward Compatibility
REDIS_FALLBACK_SCHEMAS=1.5,1.0                       # Fallback schema versions
REDIS_SUBSCRIPTION_TIMEOUT=30                         # Subscription timeout

# Standard Redis Configuration
REDIS_URL=redis://fogis-redis:6379                   # Redis server URL
REDIS_TIMEOUT=5                                       # Connection timeout
```

### Docker Compose Configuration

```yaml
services:
  fogis-calendar-sync:
    environment:
      - REDIS_SCHEMA_VERSION=2.0
      - LOGO_COMBINER_URL=http://team-logo-combiner:5002
      - REDIS_ENABLED=true
      - REDIS_FALLBACK_SCHEMAS=1.5,1.0
    depends_on:
      - fogis-redis
      - team-logo-combiner
```

## 📨 Enhanced Schema v2.0 Message Format

### Complete Message Structure

```json
{
  "schema_version": "2.0",
  "message_id": "uuid",
  "timestamp": "2025-09-26T10:30:00Z",
  "source": "match-list-processor",
  "type": "match_updates",
  "payload": {
    "matches": [
      {
        "match_id": 6170049,
        "teams": {
          "home": {
            "name": "Lindome GIF",
            "id": 26405,
            "logo_id": 10741,
            "organization_id": 10741
          },
          "away": {
            "name": "Jonsereds IF",
            "id": 25562,
            "logo_id": 9595,
            "organization_id": 9595
          }
        },
        "venue": {
          "name": "Lindevi IP 1 Konstgräs",
          "coordinates": {
            "latitude": 57.584681,
            "longitude": 12.108868
          }
        },
        "referees": [
          {
            "name": "Bartek Svaberg",
            "role": "Huvuddomare",
            "role_short": "Dom",
            "contact": {
              "mobile": "0709423055",
              "email": "bartek.svaberg@gmail.com",
              "address": {
                "street": "Lilla Tulteredsvägen 50",
                "postal_code": "43331",
                "city": "Partille"
              }
            }
          }
        ],
        "team_contacts": [
          {
            "name": "Morgan Johansson",
            "team_name": "Landvetter IS Senior",
            "is_reserve": false,
            "contact": {
              "mobile": "0733472740",
              "phone": "031918723",
              "email": "morgan@kalltorpsbygg.se"
            }
          }
        ]
      }
    ],
    "detailed_changes": [
      {
        "field": "avsparkstid",
        "from": "19:00",
        "to": "19:15",
        "category": "time_change",
        "priority": "high",
        "description": "Match time changed from 19:00 to 19:15"
      }
    ],
    "metadata": {
      "has_changes": true,
      "total_matches": 1,
      "change_summary": "Time and venue changes detected"
    }
  }
}
```

## 🔄 Message Processing Flow

### 1. Schema Version Detection

```python
# Automatic detection based on schema_version field
if schema_version == "2.0":
    # Enhanced Schema v2.0 processing
    _handle_enhanced_schema_v2(data)
elif schema_version in ["1.5", "1.0"]:
    # Legacy schema processing
    _handle_legacy_schema(data, schema_version)
```

### 2. Logo Enrichment (v2.0 only)

```python
# Extract Organization IDs
home_org_id = match["teams"]["home"]["organization_id"]
away_org_id = match["teams"]["away"]["organization_id"]

# Generate combined logo
logo_path = logo_service.generate_combined_logo(home_org_id, away_org_id)

# Add to match data
match["logo_path"] = logo_path
```

### 3. Priority Detection

```python
# Check for high-priority changes
high_priority = any(
    change["priority"] == "high" or
    change["category"] in ["time_change", "date_change", "venue_change"]
    for change in detailed_changes
)

# Trigger appropriate sync
if high_priority:
    immediate_calendar_sync(matches)
else:
    standard_calendar_sync(matches)
```

## 📊 Statistics and Monitoring

### Redis Status Endpoint

```bash
GET /redis-status
```

**Response:**
```json
{
  "success": true,
  "timestamp": "2025-09-26T10:30:00Z",
  "status": {
    "enabled": true,
    "connected": true,
    "subscribed": true,
    "schema_version_stats": {
      "v2_messages": 150,
      "v1_messages": 25,
      "unknown_messages": 0,
      "preferred_schema": "2.0"
    },
    "logo_service": {
      "enabled": true,
      "cache_size": 45
    }
  }
}
```

### Redis Statistics Endpoint

```bash
GET /redis-stats
```

**Response:**
```json
{
  "success": true,
  "timestamp": "2025-09-26T10:30:00Z",
  "statistics": {
    "messages_processed": 175,
    "messages_received": 180,
    "errors": 5,
    "uptime": 86400,
    "schema_version_stats": {
      "v2_messages": 150,
      "v1_messages": 25,
      "unknown_messages": 0
    },
    "logo_service": {
      "enabled": true,
      "cache_size": 45
    }
  }
}
```

## 🧪 Testing

### Unit Tests

```bash
# Run Enhanced Schema v2.0 tests
python -m pytest tests/redis_integration/test_enhanced_schema_v2.py -v

# Run all Redis integration tests
python -m pytest tests/redis_integration/ -v
```

### Integration Testing

```bash
# Test with v2.0 message
curl -X POST http://localhost:5003/redis-test \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": "2.0",
    "type": "match_updates",
    "payload": {
      "matches": [...],
      "detailed_changes": [...],
      "metadata": {"has_changes": true}
    }
  }'
```

## 🔍 Troubleshooting

### Logo Service Not Available

**Symptom:** Logos not appearing in calendar entries

**Solution:**
1. Check `LOGO_COMBINER_URL` environment variable
2. Verify team-logo-combiner service is running
3. Check logs for logo service connection errors
4. Service will gracefully degrade to text-only entries

### Schema Version Mismatch

**Symptom:** Messages processed as wrong version

**Solution:**
1. Verify `schema_version` field in messages
2. Check `REDIS_SCHEMA_VERSION` configuration
3. Review schema version statistics in `/redis-stats`

### High Memory Usage

**Symptom:** Increasing memory consumption

**Solution:**
1. Check logo cache size in statistics
2. Clear logo cache if needed (restart service)
3. Consider implementing cache size limits

## 📚 Additional Resources

- [Redis Subscription Integration Guide](redis_subscription_integration_guide.md)
- [Issue #115 - Enhanced Schema v2.0 Implementation](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/issues/115)
- [match-list-processor Issue #69 - Enhanced Schema v2.0](https://github.com/PitchConnect/match-list-processor/issues/69)

## 🎯 Migration from v1.0 to v2.0

### Step 1: Update Configuration

```bash
# Add to .env or docker-compose.yml
REDIS_SCHEMA_VERSION=2.0
LOGO_COMBINER_URL=http://team-logo-combiner:5002
```

### Step 2: Deploy Updated Service

```bash
# Rebuild and restart service
docker-compose build fogis-calendar-sync
docker-compose up -d fogis-calendar-sync
```

### Step 3: Verify Operation

```bash
# Check Redis status
curl http://localhost:5003/redis-status

# Monitor statistics
curl http://localhost:5003/redis-stats
```

### Step 4: Monitor Transition

- Watch schema version statistics
- Verify both v1.0 and v2.0 messages processed
- Check logo generation success rate
- Monitor calendar sync performance

---

**Enhanced Schema v2.0 provides a significant upgrade to match data processing while maintaining full backward compatibility with existing systems.**
