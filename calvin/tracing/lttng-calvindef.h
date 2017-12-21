/**
  Available events
    com_ericsson_calvin:
      actor_fire_enter      Entering the actor fire method. This may happen several times without action.
      actor_fire_exit       Exiting the actor fire method.
      actor_method_fire     Activated an Actor action. Specifies actor, method.
      actor_method_fire_d   Activated an Actor action. Specifies actor, method and one double form the action code.
      actor_method_fire_dd  Activated an Actor action. Specifies actor, method and two doubles form the action code.
      migrate               An actor is about to migrate. Specifies the actor.
      migrated              An actor has migrated. Specifies the actor.
      queue_minmax          Gives the min and max queue values after an action method. Specifies actor,method,min,max.
      queue_precond         Specifies information on queues in a precondition clause. Several of these are listed in sequence.
      
*/
#undef TRACEPOINT_PROVIDER
#define TRACEPOINT_PROVIDER com_ericsson_calvin

#undef TRACEPOINT_INCLUDE
#define TRACEPOINT_INCLUDE "lttng-calvindef.h"

#if !defined(_TP_H) || defined(TRACEPOINT_HEADER_MULTI_READ)
#define _TP_H

#include <lttng/tracepoint.h>

/*
 * Use TRACEPOINT_EVENT(), TRACEPOINT_EVENT_CLASS(),
 * TRACEPOINT_EVENT_INSTANCE(), and TRACEPOINT_LOGLEVEL() here.
 */

#endif /* _TP_H */

#include <lttng/tracepoint-event.h>

// *** A class for simple named actor events
TRACEPOINT_EVENT_CLASS(
    com_ericsson_calvin,  // Tracepoint provider name
    actor_fire_class,     // Tracepoint class name
    TP_ARGS(              // Input arguments
        const char *, actor_id
    ),
    TP_FIELDS(            // Output event fields
        ctf_string(actor, actor_id)
    )
)

TRACEPOINT_EVENT_INSTANCE(
    com_ericsson_calvin,  // Tracepoint provider
    actor_fire_class,     // Tracepoint class
    actor_fire_enter,     // Tracepoint name
    TP_ARGS(              // Input arguments
        const char *, actor_id
    )
)

TRACEPOINT_EVENT_INSTANCE(
    com_ericsson_calvin,  // Tracepoint provider
    actor_fire_class,     // Tracepoint class
    actor_migrate,     // Tracepoint name
    TP_ARGS(              // Input arguments
        const char *, actor_id
    )
)

TRACEPOINT_EVENT_INSTANCE(
    com_ericsson_calvin,  // Tracepoint provider
    actor_fire_class,     // Tracepoint class
    actor_migrated,       // Tracepoint name
    TP_ARGS(              // Input arguments
        const char *, actor_id
    )
)

TRACEPOINT_EVENT_INSTANCE(
    com_ericsson_calvin,  // Tracepoint provider
    actor_fire_class,     // Tracepoint class
    actor_fire_exit,     // Tracepoint name
    TP_ARGS(              // Input arguments
        const char *, actor_id
    )
)

// Method fire with no data
TRACEPOINT_EVENT(
    com_ericsson_calvin,  // Tracepoint provider
    actor_method_fire,     // Tracepoint name
    TP_ARGS(              // Input arguments
        const char *, actor_id,
        const char *, method_id
    ),
    TP_FIELDS(            // Output event fields
        ctf_string(actor, actor_id)
        ctf_string(method, method_id)
    )
)

// Method fire with single double data
TRACEPOINT_EVENT(
    com_ericsson_calvin,  // Tracepoint provider
    actor_method_fire_d,     // Tracepoint name
    TP_ARGS(              // Input arguments
        const char *, actor_id,
        const char *, method_id,
        double, value
    ),
    TP_FIELDS(            // Output event fields
        ctf_string(actor, actor_id)
        ctf_string(method, method_id)
        ctf_float(double, value, value)
    )
)

// Method fire two double valued data
TRACEPOINT_EVENT(
    com_ericsson_calvin,  // Tracepoint provider
    actor_method_fire_dd, // Tracepoint name
    TP_ARGS(              // Input arguments
        const char *, actor_id,
        const char *, method_id,
        double, value1,
        double, value2
    ),
    TP_FIELDS(            // Output event fields
        ctf_string(actor, actor_id)
        ctf_string(method, method_id)
        ctf_float(double, value1, value1)
        ctf_float(double, value2, value2)
    )
)

TRACEPOINT_EVENT(
    com_ericsson_calvin,  // Tracepoint provider name
    queue_minmax,     		// Tracepoint name
    TP_ARGS(              // Input arguments
        const char *, name,
        const char *, method,
				int, min,
				int, max
    ),
    TP_FIELDS(            // Output event fields
        ctf_string(name, name)
        ctf_string(method, method)
        ctf_integer(int, min, min)
        ctf_integer(int, max, max)
    )
)

TRACEPOINT_EVENT(
    com_ericsson_calvin,  // Tracepoint provider name
    queue_precond,     		// Tracepoint name
    TP_ARGS(              // Input arguments
        const char *, actor_name,
        const char *, queue_name,
				int, num_discarded,
				double, delta
    ),
    TP_FIELDS(            // Output event fields
        ctf_string(actor, actor_name)
        ctf_string(queue, queue_name)
        ctf_integer(int, discarded, num_discarded)
        ctf_float(double, offset_from_first_ms, delta)
    )
)
