# E8 Post-Hoc Actuation Validation

## Purpose

Controller-level outcomes are preserved exactly as produced by the validated
B0-B3 implementations.

Because SWIM state-changing actions may become observable after the controller's
immediate post-execution monitor, E8 additionally performs an independent
post-hoc actuation-effect assessment from the continuous runtime time series.

The E8 post-hoc result does not replace or rewrite the controller outcome.

## Observation Window

For every executed state-changing action, inspect runtime samples from the
controller cycle end through:

    cycle_end + 10 seconds

The E8 runtime sampler records state approximately every 2 seconds.

## Action-Specific Effect Rules

### add_server

Actuation effect is observed when:

    active_servers > servers_before

### remove_server

Actuation effect is observed when:

    active_servers < servers_before

### set_dimmer

Actuation effect is observed when the runtime dimmer reaches the executed
target value, allowing only normal numeric tolerance.

### none

No runtime state mutation is expected.

Classification:

    NOT_APPLICABLE

## E8 Actuation Classifications

IMMEDIATE_SUCCESS
    The controller's immediate post-execution state already contains the
    expected state change.

DELAYED_SUCCESS
    The immediate controller observation does not contain the expected state
    change, but the expected change is observed within 10 seconds after the
    controller cycle ends.

NO_EFFECT_WITHIN_10S
    The expected state change is not observed within the 10-second
    post-cycle window.

NOT_APPLICABLE
    No state-changing actuation was expected.

## Scientific Reporting Rule

The following must remain separate:

1. controller_outcome
2. e8_actuation_status
3. longitudinal QoS outcome

Controller outcomes are never overwritten retrospectively.

Longitudinal comparison across B0-B3 uses the continuous E8 runtime time
series for QoS violation rate, recovery behavior, resource usage, and other
time-dependent metrics.

## First Observed Example

E8_B0_rep00, cycle 6:

    action: remove_server
    controller cycle end: 360.030619625 s
    immediate active servers: 5
    controller outcome: FAIL
    first continuous-sampler observation with 4 active servers: 362.014 s
    delay after controller cycle end: 1.983380375 s
    E8 actuation classification: DELAYED_SUCCESS

