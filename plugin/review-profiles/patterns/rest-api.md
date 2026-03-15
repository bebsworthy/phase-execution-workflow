---
type: pattern
name: rest-api
keywords: [rest, api, http, crud, endpoint, restful]
priority: 5
matches:
  area_type: [api, endpoint, service]
  name_contains: [api, endpoint, route, controller]
---

# REST API Documentation Pattern

## Documentation Requirements

### API Overview

- **Service Purpose**: Clear description of what the API does and its boundaries
- **Base URL**: Production and staging endpoints
- **Versioning Strategy**: How API versions are managed (URL path, headers, etc.)
- **Authentication**: Methods supported (Bearer token, API key, OAuth, etc.)
- **Rate Limiting**: Limits per endpoint and time window

### Resource Documentation

Each resource should document:

- **Resource Model**: Structure and relationships
- **Endpoints**: All available operations (GET, POST, PUT, DELETE, PATCH)
- **Business Rules**: Constraints and validation rules
- **Access Control**: Who can access what operations

### Endpoint Documentation

For each endpoint, document:

- **HTTP Method and Path**: e.g., `GET /api/v1/users/{id}`
- **Purpose**: What the endpoint does
- **Parameters**:
  - Path parameters with types and constraints
  - Query parameters with defaults and validation
  - Request body schema with examples
- **Responses**:
  - Success responses with status codes and schemas
  - Error responses with codes and meanings
  - Response headers
- **Examples**: curl commands or code snippets

## Review Checklist

- [ ] RESTful resource naming conventions followed
- [ ] HTTP methods used semantically (GET for read, POST for create, etc.)
- [ ] Status codes are appropriate and consistent
- [ ] Pagination documented for collection endpoints
- [ ] Filtering and sorting parameters documented
- [ ] Error response format is consistent
- [ ] API versioning strategy is clear
- [ ] Authentication requirements specified
- [ ] Rate limiting documented
- [ ] Request/response examples provided

## Best Practices

### Resource Naming

- Use nouns, not verbs: `/users` not `/getUsers`
- Use plural forms: `/products` not `/product`
- Use hierarchical structure: `/users/{id}/orders`

### HTTP Status Codes

- `200 OK` - Successful GET, PUT
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Client error
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Authorization failed
- `404 Not Found` - Resource doesn't exist
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

### Documentation Format

- Use OpenAPI/Swagger when possible
- Provide interactive documentation (Swagger UI, Postman collections)
- Include code examples in multiple languages
- Document breaking changes clearly

## Common Issues

### Issue: Inconsistent Error Responses

Different endpoints return errors in different formats.
**Solution**: Define a standard error response schema and use it everywhere.

### Issue: Missing Pagination

Large collections returned without pagination.
**Solution**: Implement standard pagination with `page`, `limit`, and total count.

### Issue: Unclear Versioning

API changes break existing clients.
**Solution**: Clear versioning strategy with deprecation notices.
