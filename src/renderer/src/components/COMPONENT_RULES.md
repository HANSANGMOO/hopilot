# Component Architecture Rules

## Levels

### Atoms
- The smallest indivisible unit of UI.
- Cannot be broken down further without losing meaning.
- **Domain-agnostic**: can be copied to any app and still work.
- Examples: `Button`, `IconButton`, `TextArea`, `DropdownItem`, `DropdownList`, `Spinner`, `Badge`

### Molecules
- A combination of two or more atoms.
- Serves a single, focused purpose.
- **Domain-agnostic**: no dependency on hopilot-specific stores, types, or signals.
- Examples: `DropdownMenu`, `CopyBlock`, `ExpandableBlock`, `SessionItem`

### Organisms
- A self-contained, independent UI section.
- **Domain-specific**: depends on hopilot stores, domain types, or business logic.
- Occupies a meaningful slot in a template (e.g. sidebar, footer, main body).
- No restriction on what it combines (atoms, molecules, other organisms).
- Examples: `NavPanel`, `Toolbar`, `ToolPanel`, `MsgInputFooter`, `CopilotBody`

---

## The Key Distinction

| | Reusability | Can use stores? |
|--|-------------|-----------------|
| **Atom** | Any app | No |
| **Molecule** | Any app | No |
| **Organism** | hopilot only | Yes |

**Ask this one question:** "If I copy this component to a different app, does it still compile and make sense?"
- Yes → Atom or Molecule
- No → Organism

---

## Combination Rules

| Combination | Result |
|-------------|--------|
| atom + atom | molecule or organism |
| atom + molecule | organism |
| molecule + molecule | organism |
| any + store/signal | organism |

---

## Placement

```
components/
  atoms/       → domain-agnostic UI primitives
  molecules/   → domain-agnostic combinations of atoms
  organisms/   → hopilot-specific self-contained sections
  templates/   → layout shells with named slots
```

---

## Decision Guide

When unsure which level a component belongs to, ask:

1. **Can it be broken down further without losing meaning?** → If no, it is an atom.
2. **Is it a combination of atoms with no hopilot dependency?** → It is a molecule.
3. **Does it depend on hopilot stores, signals, or domain types?** → It is an organism.
4. **Does it occupy a meaningful slot in a template layout?** → It is an organism.
