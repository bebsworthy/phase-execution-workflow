---
type: framework
name: nestjs
keywords:
  [
    nestjs,
    nest,
    controller,
    service,
    module,
    dto,
    guard,
    pipe,
    interceptor,
    middleware,
  ]
extends:
  - patterns/rest-api.md
priority: 10
matches:
  file_patterns:
    [
      '*.module.ts',
      '*.controller.ts',
      '*.service.ts',
      '*.dto.ts',
      '*.guard.ts',
      '*.pipe.ts',
    ]
---

# NestJS Best Practices

## **The Guiding Philosophy**

NestJS applications should be **modular, testable, and maintainable**. The framework provides strong conventions — follow them rather than fighting the architecture. Controllers stay thin, services own domain logic, and modules define clear boundaries.

---

## **1. Module Architecture**

### **Rule: One domain, one module.**

Each business domain gets its own module with a controller, service, and DTOs. Modules are the unit of encapsulation.

```typescript
// ✅ Good: Clear module boundary
@Module({
  imports: [DatabaseModule],
  controllers: [UsersController],
  providers: [UsersService],
  exports: [UsersService], // Only export what other modules need
})
export class UsersModule {}
```

### **Rule: Keep controllers thin.**

Controllers handle HTTP concerns only: routing, request binding, guards, and response formatting. All domain logic lives in services.

```typescript
// ❌ Bad: Domain logic in controller
@Post()
async create(@Body() dto: CreateUserDto) {
  const exists = await this.db.query('SELECT ...');
  if (exists) throw new ConflictException();
  const hashed = await bcrypt.hash(dto.password, 10);
  return this.db.query('INSERT ...');
}

// ✅ Good: Controller delegates to service
@Post()
async create(@Body() dto: CreateUserDto) {
  return this.usersService.create(dto);
}
```

---

## **2. Dependency Injection**

### **Rule: Inject interfaces, not implementations.**

Use custom providers and injection tokens when you need to swap implementations (testing, multi-tenancy, etc.).

### **Rule: Avoid circular dependencies.**

If two services depend on each other, extract the shared logic into a third service or use `forwardRef()` as a last resort. Circular deps are usually a sign of incorrect module boundaries.

---

## **3. Validation and DTOs**

### **Rule: Validate at the boundary with `class-validator`.**

DTOs with validation decorators are the first line of defense. Enable the global `ValidationPipe` with `whitelist: true` to strip unknown properties and `transform: true` for auto-transformation.

```typescript
export class CreateUserDto {
  @IsString()
  @MinLength(2)
  name: string;

  @IsEmail()
  email: string;
}
```

### **Rule: Don't re-validate inside services.**

If the DTO passed validation at the controller boundary, trust it in the service layer. Redundant validation adds noise without safety.

---

## **4. Error Handling**

### **Rule: Use domain-specific exceptions.**

Create custom exception classes that extend `HttpException` for domain errors. This keeps error semantics explicit and consistent.

```typescript
// ✅ Good: Domain-specific error
export class UserConflictException extends ConflictException {
  constructor(email: string) {
    super({
      code: 'USER_CONFLICT',
      message: `User with email ${email} already exists`,
    });
  }
}
```

### **Rule: Let the exception filter handle unknown errors.**

Don't wrap every service call in try/catch. Use a global exception filter to catch unexpected errors and format them consistently.

---

## **5. Guards, Pipes, and Interceptors**

### **Rule: Use guards for authorization, pipes for transformation, interceptors for cross-cutting concerns.**

Don't mix these responsibilities. Guards decide access (return boolean). Pipes transform/validate input. Interceptors wrap execution (logging, caching, response mapping).

### **Rule: Prefer decorator composition over middleware.**

NestJS decorators (`@UseGuards`, `@UsePipes`, `@UseInterceptors`) are more explicit and testable than Express-style middleware.

---

## **6. Database and Transactions**

### **Rule: Keep database logic in the service layer, not controllers.**

Services own all data access. If queries get complex, extract a repository or data-access helper — but keep it injected through DI, not imported directly.

### **Rule: Scope transactions explicitly.**

Wrap multi-step mutations in explicit transactions. Don't rely on auto-commit for operations that must be atomic.

---

## **7. Testing**

### **Rule: Test services with real DI, not manual instantiation.**

Use `Test.createTestingModule()` to build a real NestJS container for integration tests. This catches wiring bugs that unit tests with manual mocks miss.

```typescript
const module = await Test.createTestingModule({
  providers: [UsersService, { provide: DatabaseService, useValue: mockDb }],
}).compile();

const service = module.get(UsersService);
```

### **Rule: E2E tests hit the real HTTP layer.**

Use `supertest` with a real NestJS app instance. Test the full request path: routing, guards, pipes, controller, service, error handling.

---

## **Common Antipatterns**

### **Antipattern: God services.**

A service that handles authentication, user CRUD, email sending, and report generation. Split by domain responsibility.

### **Antipattern: Barrel exports that expose internals.**

Only export what other modules actually need. A module's `exports` array is its public API.

### **Antipattern: Hardcoded configuration.**

Use `@nestjs/config` with environment-specific `.env` files. Never hardcode URLs, secrets, or feature flags in source code.
