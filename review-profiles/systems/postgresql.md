---
type: system
name: postgresql
keywords: [postgresql, postgres, sql, database, rdbms, psql]
priority: 8
---

# PostgreSQL Documentation Standards

## Database Documentation Requirements

### Schema Documentation

- **Database Purpose**: What data the database stores
- **Schema Design**: Logical organization of schemas
- **Naming Conventions**: Table, column, and constraint naming rules
- **Data Types**: Custom types and domains used
- **Versioning**: How schema changes are managed

### Table Documentation

Each table should document:

```sql
-- Users table stores registered user accounts
-- Primary entity for authentication and authorization
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE, -- User's email (login identifier)
    username VARCHAR(50) NOT NULL UNIQUE, -- Display name
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- Registration timestamp
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- Last modification
    is_active BOOLEAN NOT NULL DEFAULT true -- Soft delete flag
);

COMMENT ON TABLE users IS 'Registered user accounts';
COMMENT ON COLUMN users.email IS 'Unique email address used for login';
COMMENT ON COLUMN users.username IS 'Public display name (unique)';
```

### Relationships

```sql
-- Foreign key relationships should be documented
ALTER TABLE orders
  ADD CONSTRAINT fk_orders_user
  FOREIGN KEY (user_id)
  REFERENCES users(id)
  ON DELETE CASCADE; -- Cascading delete when user is removed

COMMENT ON CONSTRAINT fk_orders_user ON orders
  IS 'Links order to the user who placed it';
```

### Indexes

```sql
-- Document index purpose and strategy
CREATE INDEX idx_users_email_lower ON users(LOWER(email));
COMMENT ON INDEX idx_users_email_lower
  IS 'Case-insensitive email lookup for authentication';

CREATE INDEX idx_orders_created_at ON orders(created_at DESC);
COMMENT ON INDEX idx_orders_created_at
  IS 'Optimize queries for recent orders';
```

## Review Checklist

- [ ] All tables have COMMENT descriptions
- [ ] All columns have meaningful names and comments
- [ ] Foreign key relationships documented
- [ ] Indexes have documented purposes
- [ ] Constraints are named and documented
- [ ] Triggers and functions documented
- [ ] Views and materialized views explained
- [ ] Partitioning strategy documented
- [ ] Performance considerations noted
- [ ] Backup and recovery procedures documented

## Migration Documentation

### Migration Files

```sql
-- Migration: 001_create_users_table.sql
-- Date: 2024-01-15
-- Author: John Doe
-- Purpose: Initial users table for authentication system

-- Rollback: DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    -- Table definition
);
```

### Version Control

- Document migration naming convention
- Explain rollback procedures
- Note dependencies between migrations
- Document data migrations separately from schema

## Query Documentation

### Complex Queries

```sql
-- Get user activity summary for the last 30 days
-- Includes: login count, orders placed, total spent
-- Used by: Admin dashboard, user profile page
WITH user_activity AS (
    SELECT
        u.id,
        COUNT(DISTINCT l.id) as login_count,
        COUNT(DISTINCT o.id) as order_count,
        COALESCE(SUM(o.total), 0) as total_spent
    FROM users u
    LEFT JOIN login_logs l ON l.user_id = u.id
        AND l.created_at > NOW() - INTERVAL '30 days'
    LEFT JOIN orders o ON o.user_id = u.id
        AND o.created_at > NOW() - INTERVAL '30 days'
    GROUP BY u.id
)
SELECT * FROM user_activity;
```

### Stored Procedures

```sql
CREATE OR REPLACE FUNCTION calculate_user_score(p_user_id UUID)
RETURNS INTEGER AS $$
DECLARE
    v_score INTEGER := 0;
BEGIN
    -- Calculate user score based on activity
    -- Score factors: orders (10 points), reviews (5 points), referrals (20 points)

    -- Implementation here

    RETURN v_score;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_user_score IS
  'Calculates user loyalty score based on activity metrics';
```

## Performance Documentation

### Query Optimization

- Document EXPLAIN ANALYZE results for critical queries
- Note query performance expectations
- Document index usage strategies
- Explain partitioning decisions

### Connection Pooling

- Document connection pool settings
- Explain connection limits
- Note transaction timeout settings
- Document lock timeout configurations

## Security Documentation

### Access Control

```sql
-- Document role-based access
GRANT SELECT ON users TO readonly_role;
GRANT SELECT, INSERT, UPDATE ON orders TO app_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO admin_role;

-- Row-level security policies
CREATE POLICY user_isolation ON orders
    FOR ALL
    TO app_role
    USING (user_id = current_setting('app.current_user_id')::UUID);
```

## Common Issues

### Issue: Missing Column Comments

Tables without column-level documentation.
**Solution**: Add COMMENT ON COLUMN for all columns.

### Issue: Unnamed Constraints

System-generated constraint names like `users_email_key`.
**Solution**: Use explicit CONSTRAINT names that describe purpose.

### Issue: No Migration Documentation

Schema changes without explanation.
**Solution**: Document each migration's purpose and rollback procedure.
