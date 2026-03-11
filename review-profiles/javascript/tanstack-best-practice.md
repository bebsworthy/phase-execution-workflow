---
type: framework
name: tanstack-query
keywords:
  [
    javascript,
    typescript,
    tanstack,
    react-query,
    data-fetching,
    cache,
    server-state,
    async,
  ]
priority: 9
matches:
  technologies: [tanstack-query, react-query, '@tanstack/react-query']
---

## **TanStack Query: A Guideline for Server State Synchronization**

Our primary goal is to manage server state in a way that is **declarative, resilient, and performant**. TanStack Query is not just a data-fetching library; it is a server-state synchronization manager. These guidelines exist to help us use it effectively, ensuring our application is robust and our data layer is maintainable. When a rule seems unclear, we should default to what best serves data consistency and a declarative implementation.

---

### **1. Foundational Setup: Configure for Consistency**

A well-configured `QueryClient` is the bedrock of a scalable application. It reduces boilerplate and enforces architectural standards.

#### **Rule: Centralize `QueryClient` configuration with sensible defaults.**

**Why:** Defaulting `staleTime` to a non-zero value prevents excessive, jarring refetches. A global `mutationCache` handler centralizes error logging and user notifications, making the system more robust.

**Example:**

```javascript
// ❌ Bad: Using default options leads to aggressive refetching and scattered error handling.
const queryClient = new QueryClient();

// Component.js
useMutation(updatePost, {
  onError: (error) => {
    // Error handling logic is repeated in every component
    showToast('An error occurred.');
    logError(error);
  },
});

// ✅ Good: Configure a client with sane defaults for the entire application.
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Set a default staleTime to avoid excessive refetching
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: (failureCount, error) => {
        // Do not retry on 4xx client errors
        if (error.response?.status >= 400 && error.response?.status < 500) {
          return false;
        }
        // Otherwise, retry up to 2 times
        return failureCount < 2;
      },
    },
  },
  mutationCache: {
    onError: (error) => {
      // Centralized error logging or toast notification logic
      console.error('A mutation failed:', error);
      // showToast('An error occurred. Please try again.');
    },
  },
});
```

---

### **2. The Art of the Query Key**

Query keys are the most critical concept in TanStack Query. They are the address for cached data and the primary tool for interacting with the cache.

#### **Rule: Structure query keys as hierarchical arrays and use key factories.**

**Why:** A consistent, hierarchical structure enables powerful, granular cache interactions (e.g., invalidating all queries related to a feature). A key factory eliminates typos and ensures that key structures are consistent across the entire application.

**Example:**

```javascript
// ❌ Bad: Using unstructured strings or inconsistent array structures.
// Hard to invalidate, prone to typos.
useQuery({ queryKey: 'todos', ... });
useQuery({ queryKey: ['todo', 123], ... });
queryClient.invalidateQueries('todos'); // Will this invalidate the detail query? Maybe not.

// ✅ Good: Use a centralized key factory for consistency and power.
export const todoKeys = {
  all: ['todos'],
  lists: () => [...todoKeys.all, 'list'],
  list: (filters) => [...todoKeys.lists(), filters],
  details: () => [...todoKeys.all, 'detail'],
  detail: (id) => [...todoKeys.details(), id],
};

// Now it's easy and safe to use and invalidate keys.
useQuery({ queryKey: todoKeys.list({ status: 'done' }), ... });
queryClient.invalidateQueries({ queryKey: todoKeys.lists() }); // Invalidate all todo lists.
```

---

### **3. Encapsulate Logic and Promote Reusability**

Data-fetching logic should be abstracted away from presentational components to maintain a clean separation of concerns.

#### **Rule: Encapsulate `useQuery` and `useMutation` calls in domain-specific custom hooks.**

**Why:** This creates a clean, reusable, and domain-specific API for components. It enforces a sound architecture where all logic for a feature (keys, API functions, hooks) can be co-located, improving maintainability.

**Example:**

```javascript
// ❌ Bad: Components are cluttered with data-fetching logic.
function PostsList() {
  const { data } = useQuery({
    queryKey: ['posts', { status: 'published' }],
    queryFn: () => fetchPosts({ status: 'published' }),
  });
  // ...
}

// ✅ Good: The component consumes a simple, declarative hook.
// src/features/posts/usePostsQuery.ts
export const usePostsQuery = (filters) => {
  return useQuery({
    queryKey: postKeys.list(filters),
    queryFn: () => fetchPosts(filters),
  });
};
```

#### **Rule: Use the `queryOptions` helper (v5+) for sharable query definitions.**

**Why:** The `queryOptions` helper encapsulates `queryKey`, `queryFn`, and other configurations into a single, reusable object. This improves type safety and is perfect for sharing logic between `useQuery`, `useSuspenseQuery`, and `prefetchQuery`.

**Example:**

```javascript
// ✅ Good: Define a reusable query configuration that can be used anywhere.
// src/features/groups/groupQueries.ts
export const groupQueries = {
  detail: (groupId) =>
    queryOptions({
      queryKey: groupKeys.detail(groupId),
      queryFn: () => fetchGroup(groupId),
    }),
};

// Usage in a component hook:
const { data } = useQuery(groupQueries.detail(123));

// Usage for prefetching:
await queryClient.prefetchQuery(groupQueries.detail(123));
```

---

### **4. Advanced Patterns for a Responsive UI**

For a seamless user experience, master TanStack Query's advanced features.

#### **Rule: Use optimistic updates to make the UI feel instantaneous.**

**Why:** Optimistic updates update the UI _before_ the server responds, making the application feel exceptionally fast. TanStack Query provides a safe, cache-based mechanism to implement this, with automatic rollback on failure.

**Example:**

```javascript
// ✅ Good: Optimistically add a new todo to the list.
const useAddTodoMutation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: addTodo,
    onMutate: async (newTodo) => {
      // 1. Cancel ongoing refetches
      await queryClient.cancelQueries({ queryKey: todoKeys.lists() });
      // 2. Snapshot the previous value
      const previousTodos = queryClient.getQueryData(todoKeys.lists());
      // 3. Optimistically update to the new value
      queryClient.setQueryData(todoKeys.lists(), (old) => [
        ...(old || []),
        newTodo,
      ]);
      // 4. Return a context object with the snapshotted value
      return { previousTodos };
    },
    // If the mutation fails, use the context returned from onMutate to roll back
    onError: (err, newTodo, context) => {
      queryClient.setQueryData(todoKeys.lists(), context.previousTodos);
    },
    // Always refetch after error or success to ensure server state alignment
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: todoKeys.lists() });
    },
  });
};
```

#### **Rule: Update the cache directly from mutation responses to eliminate refetches.**

**Why:** If your API returns the updated entity after a mutation, using that data to update the cache with `setQueryData` is far more performant than invalidating the query and forcing a new network request.

**Example:**

```javascript
// ❌ Bad: A needless network request to refetch data the client already has.
const useUpdatePostMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updatePost,
    onSuccess: () => {
      // This forces a new API call for data we just received.
      queryClient.invalidateQueries({ queryKey: postKeys.lists() });
      queryClient.invalidateQueries({ queryKey: postKeys.details() });
    },
  });
};

// ✅ Good: Use the response from the API to update the cache directly.
const useUpdatePostMutation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updatePost, // Assumes this API returns the updated post
    onSuccess: (updatedPost) => {
      // Update the specific post's detail query
      queryClient.setQueryData(postKeys.detail(updatedPost.id), updatedPost);

      // Also update the post within the list query to keep it in sync
      queryClient.setQueryData(postKeys.lists(), (oldData) => {
        return oldData?.map((post) =>
          post.id === updatedPost.id ? updatedPost : post,
        );
      });
    },
  });
};
```

---

### **5. Handling Complex Data Flows**

#### **Rule: Use the `enabled` option for dependent queries.**

**Why:** To fetch data that depends on the result of a previous query, use the `enabled` flag. This is the correct, declarative way to create a sequential data-fetching chain, preventing a query from running until it has the data it needs.

**Example:**

```javascript
// ❌ Bad: Using useEffect to trigger a second fetch imperatively.
useEffect(() => {
  if (user) {
    fetchProjects(user.id); // Not managed by React Query
  }
}, [user]);

// ✅ Good: The projects query is declaratively disabled until `userId` is available.
function UserProjects({ email }) {
  const { data: user } = useQuery({
    queryKey: ['user', email],
    queryFn: () => fetchUserByEmail(email),
  });

  const userId = user?.id;

  const { data: projects } = useQuery({
    queryKey: ['projects', userId],
    queryFn: () => fetchProjectsByUserId(userId),
    // The query will not run until userId is truthy.
    enabled: !!userId,
  });
}
```

---

### **6. Critical Anti-Patterns (The "Don'ts")**

Avoiding common mistakes is as important as applying correct patterns.

#### **Anti-pattern: Duplicating Server State in `useState`**

**Harm:** This is the most critical anti-pattern. It creates a "forked" copy of the server state, which breaks the single source of truth principle. This local copy will not receive background updates from TanStack Query, leading to a stale, buggy UI.

**The Fix: Treat the query cache as the single source of truth. For forms, use the data to provide an initial value or leverage the `key` prop.**

```javascript
// ❌ Bad: Creating a rogue, unmanaged copy of server state.
function EditProfile({ userId }) {
  const { data: user } = useQuery({
    queryKey: ['users', userId],
    queryFn: fetchUser,
  });
  const [name, setName] = useState('');

  useEffect(() => {
    if (user) {
      setName(user.name);
    }
  }, [user]);
}

// ✅ Good: Use the `key` prop to reset form state declaratively when the ID changes.
function UserEditor({ userId }) {
  const { data: user } = useQuery({
    queryKey: ['users', userId],
    queryFn: fetchUser,
  });
  if (!user) return <p>Loading...</p>;

  // The key prop ensures the form component re-mounts with new initial state.
  return <EditProfileForm key={user.id} user={user} />;
}
```

#### **Anti-pattern: Placing Side Effects in Component `onSubmit` Handlers**

**Harm:** Attaching navigation or toast notifications to the `mutateAsync` promise in a component's submit handler makes the logic brittle. If the component unmounts while the mutation is in flight, the logic may never run or may try to update an unmounted component.

**The Fix: Place all side-effect logic within the `onSuccess` and `onError` callbacks provided by `useMutation`.**

```javascript
// ❌ Bad: Logic is detached from the mutation lifecycle.
const { mutateAsync } = useCreatePostMutation();
const handleSubmit = async (data) => {
  try {
    await mutateAsync(data);
    toast.success('Post created!');
    navigate('/posts');
  } catch (error) {
    toast.error('Failed to create post');
  }
};

// ✅ Good: Side effects are tied directly to the mutation's lifecycle.
const { mutate } = useCreatePostMutation({
  onSuccess: () => {
    toast.success('Post created!');
    navigate('/posts');
  },
  onError: (error) => {
    toast.error('Failed to create post');
  },
});
```

#### **Anti-pattern: Using TanStack Query for Client State**

**Harm:** TanStack Query is architected to solve the complex problems of _asynchronous server state_ (caching, refetching, invalidation). Using it for simple, synchronous client state (like a modal's visibility) adds unnecessary overhead and conceptual confusion.

**The Fix: Use dedicated client state management tools like `useState` or Zustand for synchronous, client-only state.**

```javascript
// ❌ Bad: Storing modal visibility in the query cache.
useQuery({
  queryKey: ['isSettingsModalOpen'],
  enabled: false, // Query is never fetched, used only as a cache entry
  initialData: false,
});

// ✅ Good: Use the right tool for the job.
const [isSettingsModalOpen, setSettingsModalOpen] = useState(false);
```
