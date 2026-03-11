---
type: pattern
name: spa
keywords: [spa, frontend, ui, component, react, vue, angular]
priority: 5
matches:
  area_type: [frontend, ui, component, view]
  name_contains: [component, page, view, ui, frontend]
---

# Single Page Application Documentation Pattern

## Documentation Requirements

### Application Overview

- **Purpose**: What the application does for users
- **Architecture**: Component hierarchy and data flow
- **Routing**: Client-side routing structure
- **State Management**: How application state is managed
- **API Integration**: Backend services consumed

### Component Documentation

Each component should document:

- **Purpose**: What the component does
- **Props/Inputs**: Required and optional properties with types
- **Events/Outputs**: Events emitted or callbacks
- **State**: Internal state management
- **Dependencies**: Other components or services used
- **Examples**: Usage examples with different prop combinations

### User Interface

- **Design System**: UI library or design tokens used
- **Accessibility**: ARIA labels, keyboard navigation
- **Responsive Design**: Breakpoints and mobile behavior
- **Browser Support**: Supported browsers and versions
- **Performance**: Loading strategies, code splitting

## Review Checklist

- [ ] Component purpose and responsibilities clear
- [ ] Props/inputs documented with types
- [ ] State management patterns documented
- [ ] Routing structure documented
- [ ] API integration patterns documented
- [ ] Error handling and loading states documented
- [ ] Accessibility features documented
- [ ] Responsive design documented
- [ ] Performance optimizations noted
- [ ] Testing approach documented

## Best Practices

### Component Design

- Follow single responsibility principle
- Document component composition patterns
- Use consistent naming conventions
- Implement proper error boundaries

### State Management

- Document state shape and flow
- Explain side effects handling
- Document data fetching patterns
- Clarify local vs global state

### Documentation Format

- Use JSDoc or TypeScript for inline docs
- Provide Storybook or similar for component gallery
- Include visual examples and screenshots
- Document keyboard shortcuts and gestures

## Common Issues

### Issue: Missing Prop Documentation

Component props not documented or typed.
**Solution**: Use PropTypes or TypeScript interfaces with descriptions.

### Issue: Unclear State Management

Complex state changes without documentation.
**Solution**: Document state flow with diagrams and explain update patterns.

### Issue: No Accessibility Documentation

Missing ARIA labels and keyboard navigation docs.
**Solution**: Document all accessibility features and testing procedures.
