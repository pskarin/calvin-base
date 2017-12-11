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
    actor_fire_exit,     // Tracepoint name
    TP_ARGS(              // Input arguments
        const char *, actor_id
    )
)

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

TRACEPOINT_EVENT(
    com_ericsson_calvin,  // Tracepoint provider
    actor_queue,     // Tracepoint name
    TP_ARGS(              // Input arguments
        const char *, actor_id,
        const char *, method_id,
        int, hasvalue,
        double, value
    ),
    TP_FIELDS(            // Output event fields
        ctf_string(actor, actor_id)
        ctf_string(method, method_id)
        ctf_integer(unsigned long, hasvalue, hasvalue)
        ctf_float(double, value, value)
    )
)
