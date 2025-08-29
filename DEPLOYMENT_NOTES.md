# Deployment Notes - Phase 1: Fresh Sync Implementation

## Overview

This document provides deployment guidance for the Phase 1 implementation of the `--fresh-sync` flag, which resolves critical contact processing failures in the FOGIS Calendar & Contacts Sync service.

## What's New

### New Command-Line Flag: `--fresh-sync`

The `--fresh-sync` flag forces complete reprocessing of both calendar events and referee contacts, bypassing all change detection mechanisms.

**Key Benefits:**
- Resolves contact processing failures where referees weren't being added to Google Contacts
- Provides clear semantics for different sync scenarios
- Maintains backward compatibility with existing workflows

## Deployment Scenarios

### Scenario 1: Standard Deployment (No Changes Required)

If your current deployment works correctly and referee contacts are being processed:

```bash
# No changes needed - existing behavior preserved
python fogis_calendar_sync.py
```

### Scenario 2: Missing Referee Contacts (Use Fresh Sync)

If referee contacts are missing from Google Contacts:

```bash
# Force complete reprocessing
python fogis_calendar_sync.py --fresh-sync
```

### Scenario 3: Complete Refresh (Calendar + Contacts)

For a complete refresh of both calendar events and contacts:

```bash
# Delete calendar events AND force contact processing
python fogis_calendar_sync.py --fresh-sync --delete
```

## Docker Deployment Updates

### Environment Variables

No new environment variables are required. The `--fresh-sync` flag is passed as a command-line argument.

### Docker Compose Example

```yaml
version: '3.8'
services:
  fogis-sync:
    image: ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:latest
    environment:
      - FOGIS_USERNAME=${FOGIS_USERNAME}
      - FOGIS_PASSWORD=${FOGIS_PASSWORD}
    volumes:
      - ./config.json:/app/config.json
      - ./credentials:/app/credentials
    command: ["python", "fogis_calendar_sync.py", "--fresh-sync"]  # Add flag as needed
```

### Cron Job Updates

If using cron for scheduled syncs, you may want to use `--fresh-sync` periodically:

```bash
# Daily normal sync
0 6 * * * docker exec fogis-sync python fogis_calendar_sync.py

# Weekly fresh sync (Sundays at 3 AM)
0 3 * * 0 docker exec fogis-sync python fogis_calendar_sync.py --fresh-sync
```

## Monitoring and Validation

### Success Indicators

Look for these log messages to confirm successful contact processing:

```
🏃‍♂️ Starting referee contact processing...
📋 Found X referees to process
🔐 Google People API authentication in progress...
✅ Successfully loaded Google People credentials
🔧 Google People API service built successfully
👤 Processing referee: [Name] (#[ID])
✅ Updated/Created contact for referee: [Name]
📊 Contact processing summary:
   Total referees: X
   Processed: X
   Skipped: 0
   Errors: 0
✅ Contact processing completed successfully
```

### Troubleshooting

If contacts are still not being processed after using `--fresh-sync`:

1. **Check Google People API Setup:**
   - Verify Google People API is enabled in Google Cloud Console
   - Confirm OAuth scopes include contacts permissions

2. **Verify Authentication:**
   - Check that token file exists and is valid
   - Look for authentication success messages in logs

3. **Review Match Data:**
   - Confirm FOGIS matches contain referee information
   - Check that `domaruppdraglista` field is populated

## Performance Considerations

### API Usage

The `--fresh-sync` flag will:
- Process ALL matches regardless of changes
- Make additional Google People API calls for contact processing
- Take longer to complete than normal sync

**Recommendation:** Use `--fresh-sync` only when needed, not for every sync operation.

### Resource Usage

- **Memory**: No significant increase
- **CPU**: Slightly higher due to additional processing
- **Network**: More API calls to Google services
- **Time**: Approximately 2-3x longer than normal sync

## Rollback Plan

If issues occur after deployment:

1. **Immediate Rollback:**
   ```bash
   # Revert to previous behavior (no fresh-sync flag)
   python fogis_calendar_sync.py
   ```

2. **Container Rollback:**
   ```bash
   # Use previous container version
   docker pull ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:previous-tag
   ```

3. **No Data Loss:** The `--fresh-sync` flag only adds functionality; it doesn't modify existing data structures.

## Testing Checklist

Before production deployment:

- [ ] Test `--fresh-sync` flag in staging environment
- [ ] Verify referee contacts are created in test Google account
- [ ] Confirm calendar events are processed correctly
- [ ] Check that existing functionality remains unchanged
- [ ] Validate performance impact is acceptable
- [ ] Test rollback procedure

## Support

For issues related to the `--fresh-sync` implementation:

1. Check logs for contact processing emoji indicators
2. Verify Google People API permissions
3. Test with a small number of matches first
4. Refer to Issue #81 for Phase 2 architectural improvements

---

**Deployment Date:** [To be filled during deployment]
**Version:** Phase 1 - Fresh Sync Implementation
**Breaking Changes:** None
**Backward Compatibility:** Yes
