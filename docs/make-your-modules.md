Koi Modules — "How to Create a New Module"
Overview
--------
This document describes the conventions, required exports, lifecycle, and best practices
for authoring modules that integrate with the Koi application. Place new module files
in the project's modules directory (e.g. src/koi/modules) and implement the required
interface so Koi's module loader can discover, validate, and register your module.
High-level goals for a module:
 - Be self-contained: encapsulate behavior, configuration, and dependencies.
 - Declare metadata: name, version, description, compat/engine version.
 - Expose lifecycle hooks: load/init, start/activate, stop/deactivate, unload.
 - Support configuration schema and validation.
 - Integrate with Koi's logging, event bus, and permission systems.
File placement & discovery
--------------------------
- Place your module source file (or directory) under src/koi/modules.
- Module files may be:
    - Single-file modules (e.g. myModule.js / my_module.py)
    - Directory modules (e.g. my_module/index.js or my_module/__init__.py) with assets.
- The module loader typically discovers modules by scanning the modules directory
  and loading files that match configured patterns (e.g. *.js, *.ts, *.py).
Module metadata (required)
--------------------------
Every module must expose metadata describing itself. Typical fields:
 - name (string, unique)               : short machine-friendly identifier
 - title (string)                      : human-friendly name
 - description (string)                : what the module does
 - version (semver string)             : module release version
 - engineCompatibility (semver range)  : supported Koi engine versions
 - author (string/object)              : author name and contact
 - license (string)                    : SPDX license identifier (recommended)
Example metadata (JS-like):
 const meta = {
   name: 'example-module',
   title: 'Example Module',
   description: 'Adds example functionality to Koi.',
   version: '1.0.0',
   engineCompatibility: '^1.2.0',
   author: 'Your Name <you@example.com>',
   license: 'MIT'
 };
Required exports / interface
----------------------------
A module should export a predictable set of properties and functions. The loader
uses these to initialize and manage the module.
Typical required exports:
 - metadata/meta (object)           : as above
 - register(container)              : register services, commands, event handlers
 - init(context, config)            : optional, called once after registration
 - start(context)                   : optional, activate resources (start timers, listeners)
 - stop(context)                    : optional, gracefully shut down
 - shutdown(context)                : optional, final cleanup before unload
If a language uses classes, a single exported class implementing these methods is fine.
"container" and "context" objects
---------------------------------
The module loader calls register/init/start/stop with helper objects:
 - container:
     - registerService(name, factory)
     - provideCommand(name, handler, options)
     - provideEventListener(eventName, handler, options)
     - addRoute(path, handler)            // if applicable (HTTP modules)
     - config (reference to resolved configuration)
 - context:
     - logger (scoped logger for module)
     - emit(eventName, payload)
     - on(eventName, handler)
     - off(eventName, handler)
     - getService(name)
     - config (resolved module config)
Configuration
-------------
- Expose a configuration schema (JSON Schema or similar) to validate user configuration.
- Provide default config values.
- Prefer explicit, documented config keys; keep them namespaced under the module name.
Example config shape:
 const configSchema = {
   type: 'object',
   properties: {
     enabled: { type: 'boolean', default: true },
     apiKey: { type: 'string' },
     pollingInterval: { type: 'integer', minimum: 1000, default: 60000 }
   },
   required: ['apiKey']
 };
Commands, Events & APIs
-----------------------
- If your module exposes commands (CLI or runtime), register them in the register() step
  with clear help text, parameter validation, and permission requirements.
- For events: subscribe during start(), unsubscribe during stop() to avoid leaks.
- For HTTP/REST modules: register routes in register() and add middleware as needed.
Permissions & Security
----------------------
- Declare required permissions/scopes for commands and actions.
- Validate and sanitize all external inputs.
- Use the context/logger for audit logging of privileged operations.
- Avoid storing secrets in plaintext; integrate with the application's secrets manager.
Dependency declaration
----------------------
- If your module depends on services provided by other modules, declare them explicitly.
- During register(), request/get dependencies from the container via service names.
- Handle optional dependencies gracefully (e.g., degrade features if dependency is absent).
Lifecycle best practices
------------------------
- register(): declare services, commands, and static wiring. Avoid starting async loops.
- init(): perform synchronous initialization that depends on resolved configuration.
- start(): launch background tasks, open connections, subscribe to events.
- stop(): stop background tasks, close connections, unsubscribe from events.
- shutdown/unload(): final cleanup, free resources; idempotent and fast.
Error handling and logging
--------------------------
- Use the provided logger for module-scoped logs.
- Throw descriptive errors during registration/init to fail fast if misconfigured.
- Catch and handle runtime errors; avoid letting unhandled exceptions crash the host.
Testing
-------
- Provide unit tests for core logic; keep side effects abstracted behind interfaces.
- Provide integration tests that run with a test instance of Koi or with mocks of
  the container/context.
- Example test targets:
    - metadata validation
    - config schema validation
    - register()/init()/start()/stop() happy paths and failure modes
Packaging & distribution
------------------------
- Keep module folder self-contained: source, README, package manifest (if applicable),
  changelog, license, and tests.
- Use semantic versioning; bump major version for breaking changes.
- If publishing to a registry, ensure package manifest declares engineCompatibility.
Documentation & README
----------------------
- Each module must include a README that documents:
    - Purpose and features
    - Installation (where to place files)
    - Configuration keys and defaults
    - Available commands/APIs/events
    - Permissions required
    - Example usage
Example pseudocode (JavaScript-style)
-------------------------------------
const metadata = { name: 'example-module', version: '1.0.0', description: '...' };
function register(container) {
  container.registerService('example', () => new ExampleService(container.config));
  container.provideCommand('example:do', async (args) => { ... }, { description: 'Do example' });
}
async function init(context, config) {
  // validate config, prepare resources
}
async function start(context) {
  context.logger.info('Starting example module');
  // open connections, subscribe to events
}
async function stop(context) {
  context.logger.info('Stopping example module');
  // stop timers, close connections
}
module.exports = { metadata, register, init, start, stop };
Versioning & Compatibility
-------------------------
- Always test with the target Koi engine version(s).
- Use engineCompatibility metadata to prevent loading on incompatible hosts.
- Provide migration scripts or instructions for breaking upgrades.
Troubleshooting
---------------
- On module load failure: check metadata, exports, and config schema.
- On runtime errors: enable debug logging for the module, inspect stack traces,
  and ensure proper cleanup on stop/start cycles.
Checklist before submitting a module
------------------------------------
- [ ] Unique module name and semver version
- [ ] metadata field populated (name, version, description, engineCompatibility)
- [ ] Exports: register() at minimum; init/start/stop as applicable
- [ ] Configuration schema with sensible defaults and validation
- [ ] Properly scoped logging and error handling
- [ ] Unit/integration tests
- [ ] README documenting installation and usage
- [ ] License and author information
Notes
-----
- This document is intentionally implementation-agnostic. Adjust names of exported
  functions and lifecycle hooks to match the concrete loader API used by your Koi
  codebase. If the loader expects different hook names or a class-based module,
  follow the exact patterns recognized by the loader.
If you paste specific module source files from src/koi/modules, I can produce a
tailored template and a concrete example module matching the exact loader API.
