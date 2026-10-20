# CHANGELOG


## Unreleased

### Documentation

- Record Python compatibility release delivery
  ([`30eeb55`](https://github.com/BuckanovNikita/ed-killer/commit/30eeb55f4c2b71cbd427c249fc823600fe33a2ce))


## v0.5.0 (2026-10-15)

### Documentation

- Align development with shared Python workflow
  ([`4eee49b`](https://github.com/BuckanovNikita/ed-killer/commit/4eee49b3fd70312ac1fcc700d374c1f390bff7ef))

- Record clearml cleanup release verification
  ([`50dca21`](https://github.com/BuckanovNikita/ed-killer/commit/50dca21aac416b165367102c5b8c84796429cefd))

- Record Python workflow alignment delivery
  ([`f9904d8`](https://github.com/BuckanovNikita/ed-killer/commit/f9904d8eb99d286c64fedeb3e72d6f27ab9d370f))

### Features

- Require Python 3.12 or 3.13
  ([`849dadb`](https://github.com/BuckanovNikita/ed-killer/commit/849dadbe33bc6ae58c9ef3fe4f9e92e65567fa90))

### Breaking Changes

- Supported Python is now >=3.12,<3.14; Python 3.10 and 3.11 are no longer supported.


## v0.4.0 (2026-10-14)

### Features

- **clearml-yolo**: Validate training fields and repair box overflows
  ([`c6d16c9`](https://github.com/BuckanovNikita/ed-killer/commit/c6d16c950a04d0b3ca87b8f83b5c43b93ecb0abd))

### Breaking Changes

- **clearml-yolo**: Clearml-yolo applies stricter minimum geometry and class-conflict rules, ignores
  task/shape metadata, and may return repaired clean coordinates.


## v0.3.0 (2026-10-13)

### Features

- Rename package and repository to ed-killer
  ([`e48290b`](https://github.com/BuckanovNikita/ed-killer/commit/e48290b6307de2214ed9f684ee6a2ffcf31e20f7))

### Breaking Changes

- Use the ed-killer distribution and command, and import ed_killer instead of csv_dataset_validator.


## v0.2.0 (2026-10-13)

### Features

- Automate local semantic releases
  ([`6e55631`](https://github.com/BuckanovNikita/ed-killer/commit/6e55631651fbe5d9c7ef22f727d7b05a7f706006))


## v0.1.0 (2026-10-13)

### Features

- Add Pandera dataset validator and CLI
  ([`6dc52fa`](https://github.com/BuckanovNikita/ed-killer/commit/6dc52fab59c7cb4c3bf1a6e5bb37c658dbb44cf8))
