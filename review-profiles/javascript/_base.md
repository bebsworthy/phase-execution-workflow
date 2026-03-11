---
type: language
name: javascript
keywords: [javascript, js, typescript, ts, node, nodejs]
priority: 2
---

# JavaScript/TypeScript Documentation Standards

## Documentation Requirements

### Module Documentation

- **File Header**: Purpose and main exports
- **Imports**: Organized by type (libraries, components, utilities)
- **Exports**: Clear public API with named exports preferred
- **Module-level Comments**: Explain complex logic or architecture

### Function Documentation

Use JSDoc format for all exported functions:

```javascript
/**
 * Calculate the total price including tax.
 *
 * @param {number} price - Base price before tax
 * @param {number} taxRate - Tax rate as decimal (e.g., 0.08 for 8%)
 * @returns {number} Total price including tax
 * @throws {Error} If price or taxRate is negative
 * @example
 * const total = calculateTotal(100, 0.08); // Returns 108
 */
function calculateTotal(price, taxRate) {
  // Implementation
}
```

### TypeScript Interfaces

```typescript
/**
 * Represents a user in the system.
 */
interface User {
  /** Unique identifier */
  id: string;

  /** User's display name */
  name: string;

  /** Email address (must be unique) */
  email: string;

  /** Account creation timestamp */
  createdAt: Date;

  /** Optional user preferences */
  preferences?: UserPreferences;
}
```

### Class Documentation

```javascript
/**
 * Manages user authentication and session handling.
 *
 * @class
 * @example
 * const auth = new AuthManager(config);
 * await auth.login(credentials);
 */
class AuthManager {
  /**
   * Create an auth manager.
   * @param {AuthConfig} config - Configuration options
   */
  constructor(config) {
    // ...
  }

  /**
   * Authenticate a user.
   * @param {Credentials} credentials - User credentials
   * @returns {Promise<User>} Authenticated user
   */
  async login(credentials) {
    // ...
  }
}
```

## Review Checklist

- [ ] All exported functions have JSDoc comments
- [ ] JSDoc includes @param, @returns, @throws
- [ ] Complex functions include @example
- [ ] TypeScript interfaces are documented
- [ ] Type definitions are clear and specific
- [ ] Async functions document Promise resolution
- [ ] Error handling is documented
- [ ] Side effects are noted
- [ ] Dependencies are documented
- [ ] Module purpose is clear

## TypeScript Specific

### Type Documentation

```typescript
/**
 * Result of an API call, either success with data or error.
 */
type ApiResult<T> =
  | { success: true; data: T }
  | { success: false; error: string };

/**
 * Configuration for retry behavior.
 */
type RetryConfig = {
  /** Maximum number of retry attempts */
  maxAttempts: number;
  /** Delay between retries in milliseconds */
  delay: number;
  /** Exponential backoff multiplier */
  backoff?: number;
};
```

### Generic Types

```typescript
/**
 * A generic repository for CRUD operations.
 * @template T - The entity type
 * @template ID - The identifier type (default: string)
 */
interface Repository<T, ID = string> {
  findById(id: ID): Promise<T | null>;
  save(entity: T): Promise<T>;
  delete(id: ID): Promise<void>;
}
```

## Best Practices

### Documentation Tools

- Use `typedoc` for TypeScript projects
- Use `jsdoc` for JavaScript projects
- Configure `eslint-plugin-jsdoc` for validation
- Generate API documentation automatically

### Async/Promise Documentation

```javascript
/**
 * Fetch user data from the API.
 *
 * @async
 * @param {string} userId - User identifier
 * @returns {Promise<User>} User data
 * @rejects {NotFoundError} If user doesn't exist
 * @rejects {NetworkError} If API is unreachable
 */
async function fetchUser(userId) {
  // ...
}
```

### React Component Documentation

```typescript
interface ButtonProps {
  /** Button label text */
  label: string;
  /** Click handler */
  onClick: () => void;
  /** Visual style variant */
  variant?: 'primary' | 'secondary';
  /** Disable interactions */
  disabled?: boolean;
}

/**
 * Reusable button component with multiple style variants.
 *
 * @example
 * <Button label="Submit" onClick={handleSubmit} variant="primary" />
 */
const Button: React.FC<ButtonProps> = ({
  label,
  onClick,
  variant = 'primary',
  disabled = false,
}) => {
  // ...
};
```

## Common Issues

### Issue: Missing Type Information

Functions without parameter or return types.
**Solution**: Add JSDoc @param and @returns or use TypeScript.

### Issue: Undocumented Promises

Async functions without Promise documentation.
**Solution**: Document what the Promise resolves to and possible rejections.

### Issue: No Interface Documentation

TypeScript interfaces without descriptions.
**Solution**: Add JSDoc comments above interfaces and their properties.
