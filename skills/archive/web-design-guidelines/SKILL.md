---
name: web-design-guidelines
description: 网页设计规范和最佳实践指南
version: 1.0.0
when_to_use: 设计网页UI时
status: peripheral
tags:
- design
- frontend
- UI
domain: code
category: code.design
---

# Web Design Guidelines

Guidelines for creating professional, accessible, and beautiful web interfaces.

## Core Principles

### 1. Visual Hierarchy
- Primary content: largest, most prominent
- Secondary content: smaller, supporting
- Tertiary: minimal visual weight

### 2. Consistency
- Consistent spacing (8px grid system)
- Consistent typography scale
- Consistent color usage

### 3. Accessibility
- WCAG 2.1 AA compliance minimum
- Color contrast ratio ≥ 4.5:1
- Keyboard navigable
- Screen reader friendly

## Typography

```css
/* 字体层级 */
--font-display: 'xxx', sans-serif;  /* 标题 */
--font-body: 'xxx', sans-serif;     /* 正文 */
--font-mono: 'xxx', monospace;      /* 代码 */

/* 字号比例 */
--text-xs: 0.75rem;   /* 12px */
--text-sm: 0.875rem;  /* 14px */
--text-base: 1rem;    /* 16px */
--text-lg: 1.125rem;  /* 18px */
--text-xl: 1.25rem;   /* 20px */
--text-2xl: 1.5rem;   /* 24px */
```

## Color System

```css
/* 主色 */
--color-primary: #xxx;
--color-primary-light: #xxx;
--color-primary-dark: #xxx;

/* 中性色 */
--color-gray-50: #f9fafb;
--color-gray-100: #f3f4f6;
--color-gray-200: #e5e7eb;
--color-gray-300: #d1d5db;
--color-gray-400: #9ca3af;
--color-gray-500: #6b7280;
--color-gray-600: #4b5563;
--color-gray-700: #374151;
--color-gray-800: #1f2937;
--color-gray-900: #111827;
```

## Spacing

8px grid system:
```css
--space-1: 0.25rem;  /* 4px */
--space-2: 0.5rem;   /* 8px */
--space-3: 0.75rem;  /* 12px */
--space-4: 1rem;     /* 16px */
--space-6: 1.5rem;   /* 24px */
--space-8: 2rem;     /* 32px */
--space-12: 3rem;    /* 48px */
```

## Components

### Buttons
- Minimum touch target: 44x44px
- Clear visual states (hover, active, disabled)
- Consistent border-radius

### Forms
- Label above input
- Error states clearly visible
- Sufficient spacing between fields

### Cards
- Consistent padding (16px or 24px)
- Subtle shadows or borders
- Clear hierarchy within card

## Responsive Breakpoints

```css
/* Mobile first */
--breakpoint-sm: 640px;   /* Tablet portrait */
--breakpoint-md: 768px;   /* Tablet landscape */
--breakpoint-lg: 1024px;  /* Desktop */
--breakpoint-xl: 1280px;  /* Large desktop */
```
