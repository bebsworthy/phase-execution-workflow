---
type: framework
name: tailwind-css-v4
keywords:
  [css, tailwind, tailwindcss, utility-first, styling, design-system, v4, vite]
priority: 8
matches:
  technologies: [tailwindcss, tailwind, '@tailwindcss/vite', 'tailwindcss/vite']
---

# Tailwind CSS v4 Best Practices

Our primary goal is to write code that is **readable, consistent, and maintainable**. These guidelines exist to help us achieve that together. When a rule seems unclear, we should default to what best serves clarity for a future developer.

---

## 1. Installation and Setup

### **Use the Official Vite Plugin**

**Rule:** **Use** the official `@tailwindcss/vite` plugin for Vite-based React projects.

**Why:** It provides the most streamlined setup process and the best performance. The plugin handles the configuration automatically and leverages Tailwind's new high-performance engine.

**Example:**

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [tailwindcss(), react()],
});
```

**Rule:** **Import** Tailwind directly into your global CSS file.

**Why:** The v4 setup is simplified. You no longer need to import different parts of Tailwind; a single import is all that's required.

**Example:**

```css
/* src/index.css */
@import 'tailwindcss';
```

---

## 2. Theming

### **Use CSS Variables for Theming**

**Rule:** **Define** theme colors and other design tokens using CSS variables.

**Why:** Tailwind v4 is designed to work with native CSS variables. This approach is more performant, easier to debug, and aligns with modern web standards. It also makes dynamic theming (e.g., dark mode) trivial to implement.

**Example:**

```css
/* src/index.css */
@import 'tailwindcss';

@layer base {
  :root {
    --color-primary: #3f3cbb;
    --color-background: #ffffff;
    --color-foreground: #111827;
  }

  .dark {
    --color-primary: #aab9ff;
    --color-background: #121063;
    --color-foreground: #e5e7eb;
  }
}
```

---

## 3. Core Principles

### **Embrace Component Abstraction**

**Rule:** **Abstract** repeating utility classes into reusable React components.

**Why:** Raw utility class strings in JSX can become cluttered and hard to read. Encapsulating styles within components creates a clean, semantic API for developers to use.

**Example:**

```javascript
// ❌ Bad: Repeating utility classes across the application.
<button className="bg-primary hover:bg-primary-alt text-primary-contrast py-2 px-4 rounded">
  Save Changes
</button>

<button className="bg-primary hover:bg-primary-alt text-primary-contrast py-2 px-4 rounded">
  Cancel
</button>

// ✅ Good: Abstracting styles into a reusable Button component.
const Button = ({ children,...props }) => {
  return (
    <button
      className="bg-primary hover:bg-primary-alt text-primary-contrast py-2 px-4 rounded"
      {...props}
    >
      {children}
    </button>
  );
};

// Usage
<Button>Save Changes</Button>
<Button>Cancel</Button>
```

---

## 4. Conditional Styling

### **Use a Standardized Approach for Variants**

**Rule:** **Use** `cva`, `clsx`, and `tailwind-merge` for managing component variants.

**Why:** This "trifecta" of libraries provides a structured, declarative, and conflict-free way to manage complex conditional styling based on props. It makes components more maintainable and easier to extend.

**Example:**

```typescript
// lib/utils.ts
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue) {
  return twMerge(clsx(inputs));
}
```

```javascript
// components/Button.jsx
import { cva } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive:
          'bg-destructive text-destructive-foreground hover:bg-destructive/90',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

const Button = React.forwardRef(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
```

---

## 5. Antipatterns to Avoid

### **Avoid Dynamic Class Name Concatenation**

**Rule:** **Do not** construct class names dynamically using string interpolation.

**Why:** The Tailwind JIT compiler works by scanning your source files for complete, literal class names. Dynamic class names will not be detected, resulting in missing styles in the production build.

**Example:**

```javascript
// ❌ Bad: The JIT compiler cannot see the full class name.
const MyComponent = ({ color }) => {
  return <div className={`bg-${color}-500`}>...</div>;
};

// ✅ Good: Map props to full class names.
const MyComponent = ({ color }) => {
  const colorClasses = {
    red: 'bg-red-500',
    blue: 'bg-blue-500',
  };
  return <div className={colorClasses[color]}>...</div>;
};
```
