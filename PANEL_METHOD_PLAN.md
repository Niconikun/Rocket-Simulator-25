# Panel Method Aerodynamics — Feasibility Research & Implementation Plan

Branch: `pyqt-gui` · Status: **feasible** · Scope: `src/models` + PyQt6 GUI + thermodynamics extensions

---

## 1. Current state on `pyqt-gui`

The aerodynamics pipeline today is:

- `src/models/aerodynamics.py` — a single `Aerodynamics(IAerodynamics)` class with two modes:
  - **geometry mode**: Barrowman method for normal force / center of pressure
    (`_calculate_normal_force_coefficients`, `_calculate_pressure_center`) plus
    component-based drag (skin friction via Prandtl–Schlichting, pressure, base,
    interference, wave) and transonic drag-divergence corrections;
  - **constant mode**: fixed `cd`/`cl` for tests.
- `src/models/interfaces.py:154` — `IAerodynamics` contract:
  `update(mach, angle_attack, height, density)`, `get_coefficients() -> (cd, cl)`,
  `get_center_of_pressure()`, `get_stability_margin()`,
  `get_aerodynamic_forces(dynamic_pressure, reference_area)`.
- `src/models/rocket/dynamics.py` (`calculate_aerodynamics`) — the **only** consumer:
  it reads `cd, cl, cp` and applies drag along −X body, lift along +Z body, torque
  = `(cm − cp) × F`. No pitch damping, roll moments, or fin effectiveness are modeled.
- `src/models/rocket/factory.py` — `create_aerodynamics()` (line 673) builds the
  geometry dict from the rocket JSON; `create_rocket_from_config()` (line 838) wires it
  via `rocket.set_aerodynamics()` (`rocket.py:413`); `RocketBuilder.with_aerodynamics()`
  already supports injecting any `IAerodynamics`.
- GUI: `ui/widgets/rocket_settings_widget.py` has tabs (Properties, Inertia & CoM, Engine,
  Geometry, Nosecone, Fins, Stability, Thrust Curves); Stability tab uses the Barrowman
  helper `src/utils/stability_calculator.py`. `ui/widgets/simulation_widget.py` stores sim
  parameters in `AppState` via `Constants.StateKeys` (`src/config/constants.py:195`);
  `workers/simulation_worker.py:271` calls `create_rocket_from_config(...)`.
- Rocket configs (`data/rockets/configs/*.json`) already contain everything needed to
  mesh the vehicle: `nosecone` (shape/length/diameter — conical, parabolic, Von Kármán
  ogive), `fuselage`, `rear_section`, `fins` (span, root/tip/mid chord, N_fins, sweep),
  `geometry.length_nosecone_fins`. The JSON schema (`data/schemas/rocket.schema.json`)
  has no `additionalProperties: false`, so a new optional `aerodynamics` section is safe.

**Key architectural fact:** the system already depends on the `IAerodynamics` interface,
not the concrete class. A panel method is therefore a *substitution*, not a refactor —
Liskov substitution is already the design intent.

---

## 2. Feasibility research (theory)

### 2.1 What a panel method gives us for a rocket

A rocket is a slender axisymmetric body-of-revolution with thin fins — exactly the
class of configurations for which panel methods were matured for missiles and
sounding rockets (Hess–Smith subsonic; Woodward supersonic, NASA CR-73106 / CR-2228).

- **Subsonic (M < 0.8):** Hess–Smith source/doublet panel method. The body surface is
  discretized into `n_axial × n_theta` panels with constant source strength (and
  doublets for the crossflow), the no-penetration boundary condition is enforced at
  panel centroids, and the resulting linear system is solved for singularity
  strengths. Because the flow is linear and the geometry is a body of revolution,
  the problem decomposes into **two unit solves done once at init** (axial flow and
  crossflow in the pitch plane); any angle of attack is a superposition
  `Φ = Φ_axial·cos α + Φ_cross·sin α`. Pressure coefficient per panel comes from
  Bernoulli; numerical integration of `Cp·n dA` yields `C_N`, `C_A`, `C_m`, and the
  center of pressure directly. Subsonic compressibility via the Prandtl–Glauert /
  Göthert scaling `β = √(1−M²)`.
- **Supersonic (M > 1.2):** linearized supersonic panel method (Woodward): constant
  source/doublet panels with closed-form Mach-cone influence coefficients. Gives the
  **wave drag and Cp distribution from actual geometry**, where Barrowman needs
  shock-expansion approximations.
- **Transonic (0.8 < M < 1.2):** no panel method is valid (mixed sub/supersonic
  flow). Keep the existing empirical transonic drag-divergence correction and blend.
- **Viscous effects:** potential panels do **not** capture skin friction or flow
  separation. Skin friction (Prandtl–Schlichting), base drag, and an Allen-type
  viscous crossflow term (`C_d,cf · sin²α`) stay as empirical add-ons — the standard
  hybrid used by production tools. Fins can be meshed as flat panels (thin-wing
  extension of the same solver) or kept on the Barrowman fin model with an
  interference factor.

### 2.2 Performance feasibility in this codebase

- Mesh of e.g. 48 × 16 = 768 panels → a dense `768 × 768` influence matrix,
  **LU-factorized once at construction** with numpy (`numpy.linalg` — already a
  dependency; scipy is available if needed). Per flight state the cost is two
  precomputed matrix–vector products — microseconds, negligible inside the RK4 loop
  at `dt = 0.001 s`.
- `update(mach, alpha, height, density)` is called every substep; results are
  cached keyed on quantized `(mach, alpha)` since the solution is linear in `α` and
  the Mach correction is a scalar scaling — hits dominate in practice.
- Monte Carlo (`workers/monte_carlo_runner.py`) reuses the same geometry per rocket,
  so the factorization is amortized over thousands of runs.

### 2.3 Accuracy expectations

- Slender body of revolution at low α: panel C_Nα and x_cp agree with wind-tunnel
  data within a few percent; analytic benchmarks exist (cone `C_Nα = 2/rad`, cone
  `x_cp = 2L/3`), so unit tests have ground truth.
- Known limitation: potential-flow body lift at high α is underpredicted without
  the Allen viscous-crossflow correction — add `C_N,visc = C_d,crossflow · sin²α`
  with `C_d,crossflow ≈ 1.2–2.0` for cylinders.
- CP from panels matches Barrowman at low Mach for the shipped configs; differences
  grow with fin size (fin-body interference), so fin treatment is a config toggle.

### 2.4 Verdict

**Feasible, with zero new dependencies** (numpy only), as a new `IAerodynamics`
implementation that plugs into the existing factory/DI seams. The panel method
replaces the Barrowman lift/CP block and adds geometry-based pressure/wave drag;
skin-friction and base drag remain empirical. It additionally unlocks the surface
pressure distribution `Cp(x, θ)`, which is the entry point for thermodynamics.

---

## 3. Implementation plan

### Phase 1 — Core solver in `src/models` (no GUI)

1. **New module `src/models/panel_method.py`:**
   - `BodyOfRevolutionMesh(rocket_data, n_axial, n_theta)` — axisymmetric mesh from
     `nosecone` (profile equations for conical / parabolic / ogive (Von Kármán) /
     ellipsoidal / power), `fuselage` cylinder, `rear_section` boat-tail; strip
     centroids, meridian normals, areas, azimuth quadrature.
   - **Phase 1 solver (implemented):** axial flow via a source line on the body
     axis (no-penetration solved once at construction, `numpy.linalg.lstsq`);
     crossflow via the per-station 2D doublet (cylinder) field plus the
     slender-body (Munk) normal force `C_N = 2 sin α cos α S_base/S_ref` with
     `x_cp` from the `dS/dx` distribution — exact for slender bodies (cone
     `C_Nα = 2`, `x_cp = 2L/3`; verified in tests). A full Hess–Smith surface
     doublet solve (better for blunt bodies) is the accuracy follow-up; flat fin
     panels likewise follow (Phase 1 uses the Barrowman fin add-on).
   - `class PanelMethodAerodynamics(IAerodynamics)` — same constructor signature as
     `Aerodynamics` (mach, angle_attack, height, atmosphere, rocket_data,
     mass_props) plus `n_axial`, `n_theta`, `include_fins`, `viscous_crossflow`.
     Implements the full interface: `update`, `get_coefficients` (CD = pressure/wave
     + skin friction + base; CL = normal force projected), `get_center_of_pressure`,
     `get_stability_margin`, `get_aerodynamic_forces`. Mach handling: Prandtl–
     Glauert (M<0.8), transonic blend (0.8–1.2), Ackeret linearized supersonic
     panels (M>1.2, geometry-based wave drag). Per-`(mach, u)` result caching.
   - Extended duck-typed API (not on the ABC, to avoid breaking other impls):
     `accepts_v_rel_body` + `update(..., v_rel_body=...)` (full body-frame relative
     velocity, sideslip preserved), `get_force_moment_body(q, S, cm_b) -> (F, M)`,
     and `get_surface_pressure() -> (x, theta, Cp)`.
2. **Factory seam** in `src/models/rocket/factory.py`:
   - `create_aerodynamics(..., method: str = "barrowman", panel_options: dict | None)` —
     reads `rocket_config["aerodynamics"]["method"]` by default, returns
     `PanelMethodAerodynamics` when `"panel"`.
   - `create_rocket_from_config(..., aero_method: Optional[str] = None)` — override
     from app state (GUI selection wins over file default).
3. **Dynamics upgrade** in `src/models/rocket/dynamics.py::calculate_aerodynamics`:
   if `getattr(aero, "get_force_moment_coefficients", None)` exists, use the full
   6-DOF body-frame force/moment vector (adds pitch damping `C_mq`, roll `C_lp`,
   fin rolling moment); otherwise keep the current scalar cd/cl/cp path. Fully
   backward compatible.
   - **Caveat (must be handled here):** dynamics currently reduces the air-relative
     velocity to a single scalar angle of attack, `alpha = arctan2(v_z, v_x)`
     (`dynamics.py:434-437`), discarding sideslip `beta`. Wind itself is upstream
     (`v_rel = v_enu - wind`, `dynamics.py:411`), so the panel model stays
     wind-agnostic — but the aero handoff must pass the **full relative-velocity
     vector in the body frame** (or both `alpha` and `beta`) so the panel solver
     can decompose the freestream into axial + crossflow in *both* planes.
     Concretely: extend the `update` call with an optional `v_rel_body` argument
     (duck-typed; defaults to the current scalar-alpha behavior) and have
     `PanelMethodAerodynamics` superpose the unit axial solution plus two unit
     crossflow solutions (`+y` and `+z`) instead of one.
4. **Tests** `tests/models/test_panel_method.py`: analytic benchmarks (cone
   `C_Nα=2`, `x_cp=2L/3`; cylinder crossflow), panel-vs-Barrowman agreement on
   `campanil_1a.json` within tolerance, interface conformance, factory switching,
   and a run of the existing suite (`tests/models/test_aerodynamics.py`,
   `test_factory.py`, `test_rocket_dynamics.py`) to prove no regression.

### Phase 2 — Config, state keys, worker plumbing ✅ implemented

- Rocket JSONs gain an optional section (schema update in
  `data/schemas/rocket.schema.json`, example in `campanil_1a.json`):
  ```json
  "aerodynamics": {
    "method": "barrowman | panel",
    "n_axial": 48, "n_theta": 16,
    "include_fins": true,
    "viscous_crossflow": true,
    "thermo_enabled": true
  }
  ```
- `src/config/constants.py` `StateKeyConstants`: `AERO_METHOD`, `AERO_PANEL_N_AXIAL`,
  `AERO_PANEL_N_THETA`, `AERO_INCLUDE_FINS`, `AERO_VISCOUS_CROSSFLOW`, `THERMO_ENABLED`.
- `src/models/rocket/factory.py`: `validate_aerodynamics_section()` (config errors)
  and `aero_selection_from_state()` (state → `(method, options)`; `'default'` =
  use the rocket file). `create_aerodynamics` merges the file section with overrides.
- `workers/simulation_worker.py`: reads the keys via `aero_selection_from_state`,
  passes `aero_method`/`aero_options` into `create_rocket_from_config`, validates the
  `aerodynamics` section in `_validate_rocket_config`, and records
  `metrics['aero_method']` / `metrics['thermo_enabled']`. Monte Carlo inherits this
  automatically (MC workers delegate to `SimulationWorker` with the shared state).
- Per-step thermo fields (`max_heat_flux`, ...) are appended in Phase 4.
- Tests: `tests/models/test_aero_plumbing.py` (section validation, state plumbing,
  schema subschema, state-overrides-file precedence).

### Phase 3 — GUI (PyQt6)

- **`ui/widgets/rocket_settings_widget.py`** — new **"Aerodynamics"** tab between
  Fins and Stability: method combo (Barrowman / Panel method), panel resolution
  spin boxes, `include_fins` and thermo checkboxes, and an **"Analyze"** button that
  runs the panel solver at sea level and plots, inline (matplotlib canvas already
  used by the Stability tab): `Cp(x)` distribution, `C_Nα` and `x_cp` vs Mach, and
  `CD(M)` — side-by-side with the Barrowman values from `stability_calculator` for
  comparison. Saved into the rocket JSON `aerodynamics` section by
  `save_rocket_config` (line 1462).
- **`ui/widgets/simulation_widget.py`** — new "Aerodynamics" group in the parameters
  panel: method combo (Rocket file default / Barrowman / Panel) + thermo toggle,
  bound to the new `StateKeys`.
- **`ui/widgets/dashboard_widget.py`** — new "Aero & Thermal" section: heat-flux and
  stagnation-temperature vs time, max-q marker, integrated heat load, and an
  unwrapped `Cp(x, θ)` surface map when the panel method is active.
- **Translations**: new label keys in `src/config/translations.py` (en/es),
  compiled via `scripts/compile_translations.py`.

#### GUI display rundown

- **Dashboard** (`ui/widgets/dashboard_widget.py`): results arrive via the
  `simulation_completed` event and are stored in `StateKeys.SIMULATION_RESULTS`
  (lines 100-108). Two display surfaces:
  - *Flight Metrics grid* (lines 219-243): six `QGroupBox` labels fed from the
    `metrics` dict — add **Max Heat Flux [W/m²]**, **Max Stagnation Temp [K]**, and
    **Total Heat Load [kJ]** as new label boxes, populated from the new metric keys.
  - *Charts tab bar* (`generate_performance_charts`, line 611): pyqtgraph
    `PlotWidget`s in a `QTabWidget` — Altitude & Velocity (dual axis), Flight Path,
    Mach vs time — plus placeholder tabs from `_generate_advanced_charts`
    (Forces, Attitude, Atmosphere, lines 668-781). Add an **"Aero & Thermal"** tab:
    heat flux vs time and stagnation temperature vs time with an `InfiniteLine`
    marking max-q, `Cp(x)` along the body at the max-q instant, and an unwrapped
    `Cp(x, θ)` heatmap (`pyqtgraph.ImageItem`). Data comes from per-step fields the
    worker appends to each trajectory point (`heat_flux`, `stagnation_temp`,
    `cp_profile`) and from `history`.
- **Monte Carlo** (`ui/widgets/monte_carlo_widget.py`): three tabs — Config,
  Landing Zone, Flight Performance (line 157). Per-run metrics arrive via
  `run_completed(idx, metrics)` (line 525) and the batch via `finished(summary)`
  (line 539).
  - *Flight Performance tab* (`_populate_stats_table`, line 586): a `QTableWidget`
    with columns Metric / Mean / Std / Min / P05 / Median / P95 / Max, driven by
    `MonteCarloAggregator.from_runs(runs).all_scalar_stats()` — new thermo metrics
    (`max_heat_flux`, `max_stagnation_temperature`, `heat_load`) appear
    automatically as rows once the worker emits them; just add pretty names to the
    `LABELS` dict. CEP row stays appended at the bottom.
  - *Landing Zone tab* (lines 630-785): matplotlib figures from the aggregator
    (`plot_apogee_histogram`, `plot_impact_scatter` — cartopy map or local km
    scatter with dispersion ellipse). Add a **thermal dispersion figure**:
    histogram of per-run max heat flux and a scatter of max-q altitude vs Mach,
    so the spread of the heating environment across the ensemble is visible;
    optionally color the impact scatter by per-run heat load.
- **README**: new "Panel method aerodynamics" section documenting the method, its
  validity envelope (transonic gap), and the thermodynamics outputs.

### Phase 4 — Thermodynamics enabled by the panel method

New module `src/utils/thermodynamics.py`, fed by `get_surface_pressure()`:

- Local edge Mach/pressure from isentropic relations on panel `Cp`; recovery
  temperature `T_r = T∞ (1 + r (γ−1)/2 M_e²)` with `r ≈ 0.85` laminar / `0.89`
  turbulent.
- **Eckert reference-temperature method**: `T* = 0.5(T_w + T_e) + 0.22(T_r − T_e)`;
  evaluate `ρ*, μ*, cp*` at `T*` (Sutherland law, already in `aerodynamics.py`).
- **Reynolds analogy**: `St = Cf/2 · Pr^(−2/3)`, `h = St ρ* V cp*`, heat flux
  `q̇ = h (T_r − T_w)` per panel, with local `Cf` from flat-plate correlations
  (laminar Blasius / turbulent Prandtl–Schlichting, consistent with the drag model).
- Stagnation point: modified-Newtonian `Cp,max → 2` limit / Fay–Riddell engineering
  correlation for the nose tip.
- Integration over the mesh → **total heat load Q(t), max q̇ and its location,
  stagnation temperature history** — the outputs the dashboard plots and the
  worker records. These size thermal protection and feed temperature-dependent
  material limits.

### 5. What else the panel method unlocks (beyond thermo)

- Full 6-DOF aero derivatives: `C_mα`, `C_mq` (pitch damping), `C_lp` (roll
  damping), `C_lδ` (fin roll forcing) — currently absent from `dynamics.py`; needed
  for spin-stabilized and fin-corrected vehicles (`spin_stabilized_rocket.json`).
- Mach- and α-dependent CP (dynamic stability analysis), nonlinear high-α loads via
  the Allen viscous-crossflow term.
- Wave drag from actual geometry in supersonic flight (replacing the empirical
  `0.4/M^1.5` term), boat-tail/base-pressure effects.
- Airframe load distribution (shear/bending from `Cp(x,θ)`) for structural sizing.
- A clean path to CFD validation: same mesh can be exported for external solvers.

---

## 4. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Transonic gap (0.8–1.2) | Blend with existing empirical transonic correction; flag regime in GUI |
| Fin–body interference accuracy | `include_fins` toggle: panel fins vs Barrowman fins; validate on shipped configs |
| High-α body lift underprediction | Allen viscous crossflow term (`C_d,cf sin²α`), toggleable |
| Per-step cost in RK4 at dt=0.001 | LU once + two matvecs + `(mach, α)` caching; profile in tests |
| Regression risk | Default stays `barrowman`; interface unchanged; full existing test suite must pass |

## 5. Verification plan

1. `pytest tests/models/test_panel_method.py` — analytic cone/cylinder benchmarks,
   panel-vs-Barrowman on `campanil_1a.json`, factory switching.
2. `pytest tests/` — full suite green (no regression in `test_aerodynamics.py`,
   `test_factory.py`, `test_simulation_integration.py`).
3. Headless GUI smoke: `QT_QPA_PLATFORM=offscreen python main.py`, select Panel
   method in the new tab, run a short sim, confirm dashboard thermo plots populate.
4. Physics sanity: apogee within a few % of the Barrowman run for the same rocket.

## 6. Suggested order of work

Phase 1 (solver + factory + tests) → Phase 2 (config/state/worker) → Phase 3 (GUI
tab + simulation settings + dashboard) → Phase 4 (thermodynamics module + metrics) →
docs/README + translations. Each phase is independently mergeable.
