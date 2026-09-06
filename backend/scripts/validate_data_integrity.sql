-- Data Integrity Check and Validation SQL Script
-- Purpose: Detect orphaned records, constraint violations, and data quality issues
-- Run this script to identify problems in the database

-- =====================================================================
-- 1. ORPHANED RECORDS CHECKS
-- =====================================================================

-- Check 1.1: Orphaned message_favorites (message_id references deleted messages)
SELECT 'ORPHANED: message_favorites with missing message' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT mf.id ORDER BY mf.id LIMIT 10) as sample_ids
FROM message_favorites mf
WHERE mf.message_id NOT IN (SELECT id FROM messages);

-- Check 1.2: Orphaned message_favorites (user_id references deleted users)
SELECT 'ORPHANED: message_favorites with missing user' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT mf.id ORDER BY mf.id LIMIT 10) as sample_ids
FROM message_favorites mf
WHERE mf.user_id NOT IN (SELECT id FROM users);

-- Check 1.3: Orphaned appeals (user_id references deleted users)
SELECT 'ORPHANED: appeals with missing user' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT a.id ORDER BY a.id LIMIT 10) as sample_ids
FROM appeals a
WHERE a.user_id NOT IN (SELECT id FROM users);

-- Check 1.4: Orphaned appeals (report_id references deleted reports)
SELECT 'ORPHANED: appeals with missing report' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT a.id ORDER BY a.id LIMIT 10) as sample_ids
FROM appeals a
WHERE a.report_id IS NOT NULL AND a.report_id NOT IN (SELECT id FROM reports);

-- Check 1.5: Orphaned likes (message/moment already deleted)
SELECT 'ORPHANED: likes with missing moment' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT l.id ORDER BY l.id LIMIT 10) as sample_ids
FROM likes l
WHERE l.moment_id NOT IN (SELECT id FROM moments);

-- Check 1.6: Orphaned likes (user already deleted)
SELECT 'ORPHANED: likes with missing user' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT l.id ORDER BY l.id LIMIT 10) as sample_ids
FROM likes l
WHERE l.user_id NOT IN (SELECT id FROM users);

-- Check 1.7: Orphaned comments (moment already deleted)
SELECT 'ORPHANED: comments with missing moment' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT c.id ORDER BY c.id LIMIT 10) as sample_ids
FROM comments c
WHERE c.moment_id NOT IN (SELECT id FROM moments);

-- Check 1.8: Orphaned comments (parent_comment already deleted)
SELECT 'ORPHANED: comments with missing parent comment' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT c.id ORDER BY c.id LIMIT 10) as sample_ids
FROM comments c
WHERE c.parent_comment_id IS NOT NULL AND c.parent_comment_id NOT IN (SELECT id FROM comments);

-- Check 1.9: Orphaned sticker_favorites (sticker already deleted)
SELECT 'ORPHANED: sticker_favorites with missing sticker' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT sf.id ORDER BY sf.id LIMIT 10) as sample_ids
FROM sticker_favorites sf
WHERE sf.sticker_id NOT IN (SELECT id FROM stickers);

-- Check 1.10: Orphaned sticker_favorites (user already deleted)
SELECT 'ORPHANED: sticker_favorites with missing user' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT sf.id ORDER BY sf.id LIMIT 10) as sample_ids
FROM sticker_favorites sf
WHERE sf.user_id NOT IN (SELECT id FROM users);

-- Check 1.11: Orphaned group_members (group already deleted)
SELECT 'ORPHANED: group_members with missing group' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT gm.id ORDER BY gm.id LIMIT 10) as sample_ids
FROM group_members gm
WHERE gm.group_id NOT IN (SELECT id FROM group_chats);

-- Check 1.12: Orphaned group_members (user already deleted)
SELECT 'ORPHANED: group_members with missing user' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT gm.id ORDER BY gm.id LIMIT 10) as sample_ids
FROM group_members gm
WHERE gm.member_type = 'human' AND gm.member_id IS NOT NULL
  AND gm.member_id NOT IN (SELECT id FROM users);

-- Check 1.13: Orphaned group_messages (group already deleted)
SELECT 'ORPHANED: group_messages with missing group' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT gm.id ORDER BY gm.id LIMIT 10) as sample_ids
FROM group_messages gm
WHERE gm.group_id NOT IN (SELECT id FROM group_chats);

-- Check 1.14: Orphaned group_memories (group already deleted)
SELECT 'ORPHANED: group_memories with missing group' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT gm.id ORDER BY gm.id LIMIT 10) as sample_ids
FROM group_memories gm
WHERE gm.group_id NOT IN (SELECT id FROM group_chats);

-- =====================================================================
-- 2. CONSTRAINT VIOLATION CHECKS
-- =====================================================================

-- Check 2.1: Messages with no content (NULL or empty)
SELECT 'CONSTRAINT: messages with missing content' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT m.id ORDER BY m.id LIMIT 10) as sample_ids
FROM messages m
WHERE m.content IS NULL OR m.content = '';

-- Check 2.2: Messages without sender (neither user nor soul)
SELECT 'CONSTRAINT: messages without sender' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT m.id ORDER BY m.id LIMIT 10) as sample_ids
FROM messages m
WHERE (m.user_id IS NULL OR m.user_id = '00000000-0000-0000-0000-000000000000'::uuid)
  AND (m.soul_id IS NULL OR m.soul_id <= 0);

-- Check 2.3: Moments with no content
SELECT 'CONSTRAINT: moments with missing content' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT m.id ORDER BY m.id LIMIT 10) as sample_ids
FROM moments m
WHERE m.content IS NULL OR m.content = '';

-- Check 2.4: Moments without author (neither user nor soul)
SELECT 'CONSTRAINT: moments without author' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT m.id ORDER BY m.id LIMIT 10) as sample_ids
FROM moments m
WHERE (m.user_id IS NULL OR m.user_id = '00000000-0000-0000-0000-000000000000'::uuid)
  AND (m.soul_id IS NULL OR m.soul_id <= 0);

-- Check 2.5: Comments with no content
SELECT 'CONSTRAINT: comments with missing content' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT c.id ORDER BY c.id LIMIT 10) as sample_ids
FROM comments c
WHERE c.content IS NULL OR c.content = '';

-- Check 2.6: Comments without author
SELECT 'CONSTRAINT: comments without author' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT c.id ORDER BY c.id LIMIT 10) as sample_ids
FROM comments c
WHERE (c.user_id IS NULL OR c.user_id = '00000000-0000-0000-0000-000000000000'::uuid)
  AND (c.soul_id IS NULL OR c.soul_id <= 0);

-- Check 2.7: Users with missing username
SELECT 'CONSTRAINT: users with missing username' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT u.id ORDER BY u.id LIMIT 10) as sample_ids
FROM users u
WHERE u.username IS NULL OR u.username = '';

-- Check 2.8: Users with missing password_hash
SELECT 'CONSTRAINT: users with missing password' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT u.id ORDER BY u.id LIMIT 10) as sample_ids
FROM users u
WHERE u.password_hash IS NULL OR u.password_hash = '';

-- =====================================================================
-- 3. TIMESTAMP LOGIC CHECKS
-- =====================================================================

-- Check 3.1: Messages with updated_at before created_at
SELECT 'TIMESTAMP: message edited_at < created_at' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT m.id ORDER BY m.id LIMIT 10) as sample_ids
FROM messages m
WHERE m.edited_at IS NOT NULL AND m.edited_at < m.created_at;

-- Check 3.2: Moments with inconsistent timestamps
SELECT 'TIMESTAMP: moment updated_at < created_at' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT m.id ORDER BY m.id LIMIT 10) as sample_ids
FROM moments m
WHERE m.created_at IS NOT NULL AND EXISTS (
  SELECT 1 FROM moments WHERE id = m.id AND created_at > NOW()
);

-- Check 3.3: Appeals with future created_at
SELECT 'TIMESTAMP: appeal created in future' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT a.id ORDER BY a.id LIMIT 10) as sample_ids
FROM appeals a
WHERE a.created_at > NOW();

-- Check 3.4: Appeals with inconsistent review timing
SELECT 'TIMESTAMP: appeal reviewed before created' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT a.id ORDER BY a.id LIMIT 10) as sample_ids
FROM appeals a
WHERE a.reviewed_at IS NOT NULL AND a.reviewed_at < a.created_at;

-- Check 3.5: Group messages with inconsistent timestamps
SELECT 'TIMESTAMP: group_message expires before created' as issue_type,
       COUNT(*) as count,
       array_agg(DISTINCT gm.id ORDER BY gm.id LIMIT 10) as sample_ids
FROM group_messages gm
WHERE gm.expires_at IS NOT NULL AND gm.expires_at < gm.created_at;

-- =====================================================================
-- 4. DATA QUALITY SUMMARY
-- =====================================================================

-- Summary of record counts
SELECT 'SUMMARY: Total Messages' as metric, COUNT(*) as value FROM messages
UNION ALL
SELECT 'SUMMARY: Total Moments', COUNT(*) FROM moments
UNION ALL
SELECT 'SUMMARY: Total Comments', COUNT(*) FROM comments
UNION ALL
SELECT 'SUMMARY: Total Users', COUNT(*) FROM users
UNION ALL
SELECT 'SUMMARY: Total Likes', COUNT(*) FROM likes
UNION ALL
SELECT 'SUMMARY: Total Message Favorites', COUNT(*) FROM message_favorites
UNION ALL
SELECT 'SUMMARY: Total Sticker Favorites', COUNT(*) FROM sticker_favorites
UNION ALL
SELECT 'SUMMARY: Total Group Chats', COUNT(*) FROM group_chats
UNION ALL
SELECT 'SUMMARY: Total Group Members', COUNT(*) FROM group_members
UNION ALL
SELECT 'SUMMARY: Total Group Messages', COUNT(*) FROM group_messages
UNION ALL
SELECT 'SUMMARY: Total Appeals', COUNT(*) FROM appeals
UNION ALL
SELECT 'SUMMARY: Total Conversations', COUNT(*) FROM conversations;

-- Index usage summary
SELECT schemaname, tablename, indexname, idx_scan as scans, idx_tup_read as tuples_read, idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC
LIMIT 20;
