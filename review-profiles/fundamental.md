---
type: system
name: fundamental
keywords:
  [
    architecture,
    design,
    patterns,
    solid,
    clean-code,
    best-practices,
    fundamentals,
  ]
priority: 1
---

# Fundamental Architecture Best Practices

## **The Guiding Philosophy**

Our primary goal is to build software that is **resilient, scalable, and maintainable**. These guidelines are the architectural bedrock for achieving that goal. When a design choice seems unclear, we should default to the principle that best serves the long-term health of the system and the clarity for future developers who will inherit it.

---

## **Core Principles: The "Do's"**

These are the foundational rules for designing robust components and systems.

### **1. Isolate Responsibilities (Single Responsibility Principle)**

**Rule:** **Assign** a single, well-defined responsibility to each class or module. A component should have only one reason to change.

**Why:** This makes the code easier to understand, test, and refactor. When a change is needed, it's localized to one place, reducing the risk of unintended side effects.

**Example:**

```javascript
// ❌ Bad: This class handles user data AND presentation.
// A change to the data logic or the display logic would both require changing this class.
class UserProfile {
  fetchUserData(userId) {
    /* ... */
  }
  displayUserOnPage(userData) {
    /* ... */
  }
}

// ✅ Good: Responsibilities are separated.
class UserDataService {
  fetchUserData(userId) {
    /* ... */
  }
}

class UserInterface {
  displayUserOnPage(userData) {
    /* ... */
  }
}
```

### **2. Design for Extension, Not Modification (Open/Closed Principle)**

**Rule:** **Write** entities (classes, modules) that can be extended with new functionality without modifying their existing source code.

**Why:** This prevents introducing bugs into existing, working code. New features are added in new code, making the system more stable and easier to update.

**Example:**

```javascript
// ❌ Bad: To add a new shape, you must modify the `calculateAreas` function.
function calculateAreas(shapes) {
  shapes.forEach((shape) => {
    if (shape.type === 'circle') {
      /* ... */
    }
    if (shape.type === 'square') {
      /* ... */
    }
  });
}

// ✅ Good: The function accepts any shape that conforms to the interface.
// You can add a new `Triangle` class without changing `calculateAreas`.
function calculateAreas(shapes) {
  shapes.forEach((shape) => {
    shape.calculateArea();
  });
}
```

### **3. Eliminate Repetition (Don't Repeat Yourself - DRY)**

**Rule:** **Abstract** every piece of knowledge or logic into a single, unambiguous representation within the system.

**Why:** Repetition leads to maintenance nightmares. If logic is copied in multiple places, a single change requires hunting down and updating every instance, which is error-prone.

**Example:**

```javascript
// ❌ Bad: The validation logic is repeated.
function registerUser(email, password) {
  if (!email.includes('@')) {
    throw new Error('Invalid email.');
  }
  // ...
}

function updateUser(email) {
  if (!email.includes('@')) {
    throw new Error('Invalid email.');
  }
  // ...
}

// ✅ Good: The logic is centralized in one function.
function validateEmail(email) {
  if (!email.includes('@')) {
    throw new Error('Invalid email.');
  }
}

function registerUser(email, password) {
  validateEmail(email);
  // ...
}
```

### **4. Keep It Simple (KISS)**

**Rule:** **Favor** the simplest possible solution. Avoid unnecessary complexity.

**Why:** Simple code is easier to write, read, and debug. Complexity is the primary source of bugs and maintenance costs.

**Example:**

```javascript
// ❌ Bad: Using a complex loop and index for a simple sum.
const numbers = [1, 2, 3];
let sum = 0;
for (let i = 0; i < numbers.length; i++) {
  sum += numbers[i];
}

// ✅ Good: Using a clear, declarative, and simpler method.
const numbers = [1, 2, 3];
const sum = numbers.reduce((acc, num) => acc + num, 0);
```

### **5. Depend on Abstractions, Not Concretions (Dependency Inversion)**

**Rule:** **Make** high-level modules depend on abstractions (like interfaces or abstract classes), not on concrete low-level implementations.

**Why:** This decouples your code. It allows you to easily swap out implementations (e.g., changing from a SQL database to a NoSQL database, or from one payment provider to another) without changing the high-level business logic.

**Example:**

```javascript
// ❌ Bad: The high-level `ReportGenerator` depends directly on the low-level `MySqlDatabase`.
class MySqlDatabase {
  getData() {
    /* ... */
  }
}

class ReportGenerator {
  constructor() {
    this.db = new MySqlDatabase(); // Direct dependency
  }
  generate() {
    const data = this.db.getData();
    // ...
  }
}

// ✅ Good: The generator depends on an abstraction (`Database`).
// We can pass in *any* class that implements the `Database` interface.
class ReportGenerator {
  constructor(database) {
    // Depends on the abstraction
    this.db = database;
  }
  generate() {
    const data = this.db.getData();
    // ...
  }
}
```

---

## **Common Antipatterns: The "Don'ts"**

Avoiding common pitfalls is as important as following good principles.

### **Antipattern: Over-Engineering (YAGNI - You Ain't Gonna Need It)**

**Harm:** Building features or complex architectural layers "just in case" adds complexity and development time for functionality that may never be used. It's a direct violation of the KISS principle.

**Better Alternative:** **Implement** only what is necessary for the current requirements. Trust that you can adapt and extend the design later when new requirements actually emerge.

### **Antipattern: God Objects**

**Harm:** A "God Object" is a class that knows and does everything. It violates the Single Responsibility Principle, making it impossible to test, debug, or refactor without breaking the entire system.

**Better Alternative:** **Decompose** large classes into smaller, more focused modules that each have a single responsibility. This aligns with the Single Responsibility Principle.

### **Antipattern: Premature Optimization**

**Harm:** Optimizing code before identifying performance bottlenecks often leads to more complex, unreadable code with negligible performance gains.

**Better Alternative:** **Write** clean, simple, and maintainable code first. Use profiling tools to identify actual bottlenecks, and then optimize only those specific areas.
