---
type: framework
name: react
keywords: [javascript, typescript, react, jsx, tsx, component, hooks]
extends:
  - patterns/spa.md
priority: 10
---

## **React Project Guideline: Building for Clarity and Maintainability**

Our primary goal is to write code that is **readable, consistent, and maintainable**. These guidelines exist to help us achieve that together. When a rule seems unclear, we should default to what best serves clarity for a future developer. This document is a living standard for all our React projects.

---

### **1. Project Setup & Foundational Tooling**

A strong foundation prevents future issues and improves developer experience.

#### **Rule: Initialize projects with Vite and TypeScript.**

- **Why:** Vite provides superior development speed and a modern toolchain. TypeScript enforces type safety, catching countless potential bugs at compile time.
- **Enforcement:** New projects must be created using `npm create vite@latest -- --template react-ts`. Enable `strict` mode in `tsconfig.json` immediately.

#### **Rule: Enforce code style with ESLint and Prettier.**

- **Why:** This eliminates style debates, catches common errors early, and ensures a universally consistent codebase.
- **Enforcement:** Our standard ESLint configuration (including `eslint-plugin-react-hooks` and `eslint-plugin-jsx-a11y`) and Prettier rules will be applied to all projects. Code should be formatted automatically on save and before commits.

---

### **2. Architecture & Code Organization**

A well-organized architecture is crucial for long-term scalability.

#### **Rule: Organize files by feature (colocation).**

- **Why:** Grouping all files by feature (components, hooks, styles, tests) makes the codebase modular, easier to navigate, and simplifies refactoring.
- **Example:** See the "Common Antipatterns" section for a folder structure example.

#### **Rule: Create explicit public APIs for features.**

- **Why:** Using an `index.ts` file within each feature directory to export only the necessary components creates a clear and enforceable boundary. It prevents other parts of the application from depending on internal implementation details.

#### **Rule: Use absolute imports.**

- **Why:** Absolute imports (e.g., `@/features/Auth`) make moving files and refactoring significantly easier than long relative imports (`../../../features/Auth`).
- **Enforcement:** Configure path aliases in `tsconfig.json` or `vite.config.js`.

#### **Rule: Isolate API logic in a dedicated service layer.**

- **Why:** Components and hooks should not contain raw `fetch` or `axios` calls. A service layer (`/services`) abstracts away API implementation details, making the code cleaner and easier to mock for tests.
- **Example:**

  ```typescript
  // ❌ Bad: API logic is mixed into the component hook.
  const useUser = (userId) => {
    const { data } = useQuery(['user', userId], () =>
      fetch(`https://api.example.com/users/${userId}`).then((res) =>
        res.json(),
      ),
    );
    return data;
  };

  // ✅ Good: The component hook calls the clean service layer.
  // in /services/userService.ts
  export const fetchUser = (userId) => {
    return api.get(`/users/${userId}`); // api is a pre-configured axios instance
  };

  // in /features/User/useUserData.js
  const useUserData = (userId) => {
    const { data } = useQuery(['user', userId], () =>
      userService.fetchUser(userId),
    );
    return data;
  };
  ```

---

### **3. Component Design & State**

Well-designed components are readable, performant, and easy to maintain.

#### **Rule: Follow a clear state management hierarchy.**

- **Why:** Using the right tool for the job prevents over-complication and performance issues.
- **Guidance:**
  - **`useState`**: For all simple, local component state.
  - **`useReducer`**: For complex state logic within a single component.
  - **`useContext`**: For low-frequency global state (e.g., theme, authentication status).
  - **Zustand**: For complex, high-frequency global client state.

#### **Rule: Compute derived data during rendering.**

- **Why:** Storing derived data in state creates redundancy and can lead to synchronization bugs.
- **Enforcement:** Calculate derived values directly in the component body. The React 19 compiler is designed to automatically memoize expensive calculations.

#### **Rule: Understand the new role of `useMemo` with the React Compiler.**

- **Why:** With the React 19 compiler, the primary purpose of `useMemo` shifts from a performance optimization tool to a tool for ensuring referential stability. The compiler handles most performance-related memoization automatically and more effectively.
- **Guidance: When NOT to use `useMemo`**
  - Avoid using `useMemo` purely to prevent re-renders or re-calculations. Trust the compiler.
  - **Before (Old Way):**
    ```typescript
    function ProductPage({ price, tax }) {
      const finalPrice = useMemo(() => price + (price * tax), [price, tax]);
      return <PriceDisplay value={finalPrice} />;
    }
    ```
  - **After (React 19 Way):**
    ```typescript
    function ProductPage({ price, tax }) {
      // The compiler automatically memoizes this calculation
      const finalPrice = price + (price * tax);
      return <PriceDisplay value={finalPrice} />;
    }
    ```
- **Guidance: When it's STILL OK to use `useMemo`**
  - **Referential Stability:** Use `useMemo` when you need a stable object or array reference for a hook's dependency array (e.g., `useEffect`). This is a semantic requirement, not a performance one.

    ```typescript
    function UserProfile({ user }) {
      const options = useMemo(() => ({ id: user.id, role: user.role }), [user.id, user.role]);

      useEffect(() => {
        // This effect only re-runs if the 'options' object's contents change,
        // not every time the parent component re-renders.
        trackUser(options);
      }, [options]);

      return <div>...</div>;
    }
    ```

  - **Expensive Synchronous Calculations:** In rare cases, for a truly expensive, blocking calculation that you must avoid re-running, `useMemo` can be a valid tool. However, this should be an exception, not the rule.

#### **Rule: Display intelligent loading states.**

- **Why:** Avoid showing blank screens or simple spinners. Skeleton screens that mimic the layout of the loading content improve perceived performance and user experience.

---

### **4. Data Flow & API Interactions**

API interactions must be robust, abstracted, and performant.

#### **Rule: Abstract server state with TanStack Query.**

- **Why:** It standardizes data fetching and provides essential features like caching, background re-fetching, and mutation management out-of-the-box.
- **Enforcement:** All server-side data fetching (`useQuery`) and mutation (`useMutation`) must be handled through TanStack Query.

#### **Rule: Use `useEffect` for synchronization only.**

- **Why:** The purpose of `useEffect` is to synchronize your component with an external system (e.g., a browser API, a third-party SDK). Using it for data fetching is an antipattern that TanStack Query solves more effectively.

---

### **5. Common Antipatterns to Avoid**

#### **Antipattern: Prop Drilling**

- **What it is:** Passing props through many layers of intermediate components.
- **Why it's bad:** It creates tight coupling and causes unnecessary re-renders.
- **Solution:** Use React Context or a state management library (see the state hierarchy rule).

#### **Antipattern: Defining components inside the render function.**

- **Why it's bad:** This is a major performance killer, as the inner component is re-created on every render, losing its state.
- **Solution:** Always define components at the top level of your module.

---

### **6. Quality, Security & Performance**

#### **Rule: Write user-centric tests.**

- **Why:** Tests should verify functionality from a user's perspective, not implementation details.
- **Enforcement:** Use Vitest and React Testing Library. Find elements by their accessible role or text. Mock the API layer with Mock Service Worker (MSW).

#### **Rule: Implement a global error boundary and reporting.**

- **Why:** A combination of a local boundary and a reporting service provides a robust safety net. The boundary displays a fallback UI, and the service allows us to proactively find and fix bugs in production.
- **Enforcement:** Wrap the application in a top-level Error Boundary. Integrate a service like Sentry or LogRocket.

#### **Rule: Perform regular dependency audits.**

- **Why:** Your app's security depends on its dependencies.
- **Enforcement:** Regularly run `npm audit` and use automated tools like Dependabot or Snyk to patch known vulnerabilities.

#### **Rule: Prevent XSS attacks.**

- **Why:** Rendering HTML directly from an external source can expose your application to Cross-Site Scripting (XSS) attacks.
- **Solution:** Trust React's automatic content sanitization. **Never use `dangerouslySetInnerHTML`**. If you must, sanitize the content first with a library like DOMPurify.

#### **Rule: Optimize performance strategically, not prematurely.**

- **Why:** A fast application is critical for user retention, but premature optimization can lead to complex, unmaintainable code. We should focus on well-known patterns for common problems and use profiling to guide other optimization efforts.
- **Guidance:**
  - **Code Splitting:** Use `React.lazy()` with `<Suspense>` to split code at the route level. This is a foundational optimization for almost any application.
  - **List Virtualization:** For features that will render long lists, use a library like TanStack Virtual to only render items currently in the viewport. This is a necessary optimization for data-heavy interfaces.
  - **General Optimization:** Before applying more specific memoization techniques like `useMemo` or `useCallback`, always profile your application to identify true performance bottlenecks.
