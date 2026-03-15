---
type: language
name: typescript
keywords: [typescript, ts, javascript, types, typing, static-types, type-safety]
priority: 3
matches:
  technologies: [typescript, ts]
---

# TypeScript Best Practices: A Guideline

## **1. The Guiding Philosophy**

Our primary goal is to write code that is **readable, consistent, and robust**. These guidelines exist to help us leverage TypeScript's power to achieve that together. When a rule seems unclear, we should default to what best serves clarity and long-term maintainability for a future developer. This document turns the type-checker from a hurdle into a collaborative tool for success. 🏆

---

## **2. Project Configuration: The Foundation of Safety**

A project's `tsconfig.json` is its constitutional document for type safety. Getting it right is the first step.

### **Rule: Enable `strict` Mode**

**Always** enable all strictness flags by setting `strict: true` in your `tsconfig.json`.

- **Why:** This is the single most important setting in a TypeScript project. It activates all strict type-checking options (`noImplicitAny`, `strictNullChecks`, `useUnknownInCatchVariables`, etc.), providing the highest level of type safety and catching entire classes of bugs at compile time.

- **Example:**

  ```json
  // ❌ Bad: A permissive configuration that allows for unsafe code.
  {
    "compilerOptions": {
      "strict": false
    }
  }

  // ✅ Good: Enforce the highest level of type safety from the start.
  {
    "compilerOptions": {
      "target": "ES2022",
      "module": "ESNext",
      "lib": ["ES2022", "DOM"],
      "strict": true,
      "esModuleInterop": true,
      "forceConsistentCasingInFileNames": true
    }
  }
  ```

- **Tooling:** This is enforced by the TypeScript compiler via `tsconfig.json`.

---

## **3. The Art of Precise Typing**

Effective typing involves choosing the right constructs to model data accurately and safely.

### **Rule: Use `interface` for Object Shapes, `type` for Compositions**

**Use** `interface` to define the shape of objects and classes. **Use** `type` for creating union types, intersection types, or aliasing primitives and tuples.

- **Why:** This convention provides consistency. `interface` is ideal for object-oriented patterns because it can be extended and implemented. `type` is more readable and flexible for combining existing types.

- **Example:**

  ```typescript
  // ✅ Good: Use `interface` for object shapes.
  interface User {
    id: number;
    name: string;
  }

  // ✅ Good: Use `type` for a union of string literals.
  type UserStatus = 'active' | 'inactive' | 'pending';
  ```

### **Antipattern: The `any` Dilemma**

**Avoid** using the `any` type. It is a dangerous escape hatch that disables type-checking.

- **Why it's harmful:** Using `any` introduces a "type virus." Any value derived from an `any` type also becomes `any`, silently dismantling the type safety net across your application. This defers type errors to runtime, which is precisely what TypeScript aims to prevent.

- **The Preferred Alternative:** **Use** the `unknown` type for values from external sources (like API responses). `unknown` forces you to perform a safe runtime check (like a type guard) before you can operate on the value.

- **Example:**

  ```typescript
  // ❌ Bad: `any` allows unsafe property access, leading to runtime errors.
  async function fetchUserUnsafe(id: number) {
    const user: any = await (await fetch(`/api/users/${id}`)).json();
    console.log(user.profile.name); // Compiles, but will crash if `profile` doesn't exist.
  }

  // ✅ Good: `unknown` forces a check, preventing runtime errors.
  async function fetchUserSafe(id: number) {
    const user: unknown = await (await fetch(`/api/users/${id}`)).json();
    if (isUser(user)) {
      // isUser is a custom type guard
      console.log(user.profile.name);
    }
  }
  ```

### **Antipattern: Overusing Type Assertions**

**Avoid** using type assertions (e.g., `value as string`) to silence compiler errors.

- **Why it's harmful:** An assertion is not a safe type conversion; it is a compile-time instruction that removes the compiler's safety checks. If the assertion is incorrect, it will lead to a runtime error. It is often a sign that your types are modeled incorrectly.

- **The Preferred Alternative:** **Use** user-defined type guards or type narrowing to safely validate the shape of data at runtime.

- **Example:**

  ```typescript
  // ❌ Bad: Unsafe assertion that can easily lead to a crash.
  const response: unknown = { name: 'Alice', age: 30 };
  const user = response as { name: string; email: string };
  console.log(user.email.toLowerCase()); // CRASHES: user.email is undefined

  // ✅ Good: A type guard performs a runtime check.
  function isUserWithEmail(
    value: unknown,
  ): value is { name: string; email: string } {
    return typeof value === 'object' && value !== null && 'email' in value;
  }

  const response: unknown = { name: 'Alice', age: 30 };
  if (isUserWithEmail(response)) {
    console.log(response.email.toLowerCase()); // Safe
  }
  ```

---

## **4. Designing with Immutability**

Design with immutability to reduce side effects and create more predictable code.

### **Rule: Prefer Immutability**

**Use** TypeScript's `readonly` modifier and `as const` assertions to enforce immutability at compile time.

- **Why:** Preventing data from being changed after it's created is a powerful strategy for reducing bugs, especially in complex applications with shared state. It makes code easier to reason about.

- **Example:**

  ```typescript
  // ✅ Good: Use `readonly` for properties that should not change.
  interface Config {
    readonly apiKey: string;
    readonly endpoint: string;
  }
  const config: Config = { apiKey: 'abc', endpoint: '/api' };
  // config.apiKey = "def"; // Compile-time error

  // ✅ Good: Use `as const` for deeply immutable constants.
  const COLORS = ['red', 'green', 'blue'] as const;
  // COLORS.push("yellow"); // Compile-time error
  ```

---

## **5. Structuring Code for Clarity**

A well-organized project is easier to navigate, understand, and scale.

### **Rule: Follow Naming Conventions**

**Use** standard naming conventions to improve readability.

- **Why:** A consistent naming scheme makes the code's structure and intent clear at a glance, reducing cognitive load for everyone on the team.

- **The Conventions:**
  - **`PascalCase`** for types, interfaces, enums, and classes (e.g., `interface UserProfile`).
  - **`camelCase`** for variables, functions, and properties (e.g., `const userId`).
  - **`CONSTANT_CASE`** for top-level or static constants (e.g., `const MAX_RETRIES`).
  - **`kebab-case`** for filenames (e.g., `user-profile.component.ts`).

### **Rule: Prefer Named Exports**

**Always** use named exports. **Avoid** default exports.

- **Why:** Named exports are explicit, which prevents naming inconsistencies. They also make it significantly easier to search for all usages of a component and enable more reliable automated refactoring.

- **Example:**

  ```typescript
  // ❌ Bad: The name can be different in every file that imports it.
  export default class UserProfile {
    /* ... */
  }
  import MyProfile from './user-profile'; // Inconsistent naming

  // ✅ Good: The name is consistent and discoverable.
  export class UserProfile {
    /* ... */
  }
  import { UserProfile } from './user-profile'; // Clear and consistent.
  ```

### **Antipattern: Copy-Pasting Type Definitions**

**Avoid** manually creating variations of existing types by copying and pasting fields.

- **Why it's harmful:** This violates the "Don't Repeat Yourself" (DRY) principle and creates a maintenance nightmare. If the original type changes, all copied versions must be found and updated manually.

- **The Preferred Alternative:** **Use** TypeScript's built-in utility types (`Pick`, `Omit`, `Partial`, etc.) to derive new types from a single source of truth.

- **Example:**

  ```typescript
  interface User {
    id: number;
    name: string;
    email: string;
  }

  // ❌ Bad: Manually creating a partial type.
  interface UserUpdatePayload {
    name?: string;
    email?: string;
  }

  // ✅ Good: Deriving the type ensures it stays in sync with `User`.
  type UserUpdatePayload = Pick<User, 'name' | 'email'>;
  ```

---

## **6. Asynchronous Code**

Handle asynchronous operations in a way that is both safe and performant.

### **Rule: Handle Errors Safely**

**Always** treat errors in `catch` blocks as `unknown`.

- **Why:** You can `throw` anything in JavaScript (an `Error` object, a string, `null`). The `useUnknownInCatchVariables` strict flag enforces this. Assuming the caught error has a `.message` property is unsafe and can lead to a second, unhandled error.

- **Example:**

  ```typescript
  try {
    // ...
  } catch (error) {
    // `error` is of type `unknown`
    // ❌ Bad: Unsafe access, will crash if `error` is not an object with a message.
    console.error(error.message);

    // ✅ Good: Safely inspect the error before using it.
    if (error instanceof Error) {
      console.error(`Failed to fetch user: ${error.message}`);
    } else {
      console.error('An unknown error occurred:', error);
    }
  }
  ```

### **Antipattern: Sequential `await`**

**Avoid** `await`ing independent promises sequentially.

- **Why it's harmful:** This turns parallelizable work into a serial process, dramatically slowing down execution.

- **The Preferred Alternative:** **Use** `Promise.all()` to execute independent asynchronous operations concurrently.

- **Example:**

  ```typescript
  // ❌ Bad: Each request waits for the previous one to complete.
  async function fetchUsersSequentially(ids: number[]): Promise<User[]> {
    const users: User[] = [];
    for (const id of ids) {
      users.push(await fetchUser(id)); // Unnecessary waiting
    }
    return users;
  }

  // ✅ Good: All requests are sent in parallel.
  async function fetchUsersConcurrently(ids: number[]): Promise<User[]> {
    const userPromises = ids.map((id) => fetchUser(id));
    return await Promise.all(userPromises);
  }
  ```

---

## **7. Automating Quality**

A guideline is only effective if it's followed. The best way to ensure this is through automation.

### **Rule: Enforce Standards with Tooling**

**Set up** ESLint and Prettier to automate code quality and formatting enforcement.

- **Why:** This offloads the cognitive burden of style and quality checks from the developer to the machine. It eliminates style debates in code reviews and guarantees a consistent, readable codebase.

- **How to make it actionable:**
  1.  **Configure Prettier** (`.prettierrc`) to handle all code formatting.
  2.  **Configure ESLint** (`.eslintrc.js`) with `@typescript-eslint/recommended` to catch potential bugs and enforce best practices. Use `eslint-config-prettier` to disable any ESLint rules that conflict with Prettier.
  3.  **Use pre-commit hooks** with tools like `husky` and `lint-staged` to automatically format and lint staged files before every commit, preventing non-compliant code from ever entering the repository.
